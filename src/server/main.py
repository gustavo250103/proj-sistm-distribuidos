import os
import json
import time
from datetime import datetime

import zmq
import msgpack
import threading

# Endereços principais (podem ser sobrescritos via docker-compose/env)
BROKER = os.getenv("BROKER_ENDPOINT", "tcp://localhost:5556")     # REP <-> DEALER (broker)
XSUB   = os.getenv("PROXY_XSUB", "tcp://localhost:5557")          # PUB -> XSUB (proxy)
XPUB   = os.getenv("PROXY_XPUB", "tcp://localhost:5558")          # SUB <- XPUB (proxy)  # <- usado p/ replicação e election

DATA   = os.getenv("PERSIST_DIR", "./data")

SERVER_NAME = os.getenv("SERVER_NAME", f"server-{int(time.time()) % 1000}")
REF_HOST    = os.getenv("REF_HOST", "localhost")
REF_PORT    = os.getenv("REF_PORT", "6000")
REF_ADDR    = f"tcp://{REF_HOST}:{REF_PORT}"

LOG_PUB = os.path.join(DATA, "publications.jsonl")
LOG_MSG = os.path.join(DATA, "messages.jsonl")
REG     = os.path.join(DATA, "registry.json")

os.makedirs(DATA, exist_ok=True)

# ---------------------------
# Relógio lógico e controle
# ---------------------------

logical_clock = 0            # relógio lógico Lamport
msg_count = 0
SYNC_EVERY = 10              # a cada N mensagens tentamos sincronizar clock e atualizar coordenador
last_heartbeat = 0.0
HEARTBEAT_INTERVAL = 5.0

rank = None
servers_info = {}            # info retornada pelo ref
coordinator = None           # nome do servidor coordenador


def ts() -> str:
    """Timestamp físico em ISO."""
    return datetime.utcnow().isoformat() + "Z"


def append(path: str, obj: dict) -> None:
    """Persistência simples em JSONL."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def load_registry() -> dict:
    """Carrega canais/usuários ou cria default."""
    if os.path.exists(REG):
        return json.load(open(REG, "r", encoding="utf-8"))
    reg = {"channels": ["general", "random", "dev"], "users": []}
    json.dump(reg, open(REG, "w", encoding="utf-8"))
    return reg


def save_registry(reg: dict) -> None:
    json.dump(reg, open(REG, "w", encoding="utf-8"))


# ---------------------------
# Relógio lógico (Lamport)
# ---------------------------

def update_clock(remote_clock: int) -> None:
    """Atualiza o relógio lógico local."""
    global logical_clock
    logical_clock = max(logical_clock, int(remote_clock or 0)) + 1


def next_clock() -> int:
    """Incrementa o relógio lógico e retorna o valor."""
    global logical_clock
    logical_clock += 1
    return logical_clock


# ---------------------------
# Helpers de MessagePack
# ---------------------------

def recv_msgpack(sock) -> dict:
    raw = sock.recv()
    return msgpack.unpackb(raw, raw=False)


def send_msgpack(sock, obj: dict) -> None:
    sock.send(msgpack.packb(obj, use_bin_type=True))


def pub_msgpack(pub, topic: str, obj: dict) -> None:
    pub.send_multipart([
        topic.encode("utf-8"),
        msgpack.packb(obj, use_bin_type=True),
    ])


# ---------------------------
# Comunicação com servidor de referência (ref)
# ---------------------------

def ref_request(sock, service: str, data: dict) -> dict:
    """
    Envia requisição JSON para o servidor de referência
    e atualiza o clock lógico com a resposta.
    """
    data = dict(data or {})
    data.setdefault("timestamp", ts())
    data.setdefault("clock", next_clock())

    sock.send_json({"service": service, "data": data})
    reply = sock.recv_json()
    rdata = reply.get("data", {}) or {}
    update_clock(rdata.get("clock", 0))
    return reply


def register_with_ref(ref_sock) -> None:
    """Pede rank e lista de servidores para o ref."""
    global rank, servers_info, coordinator

    reply_rank = ref_request(ref_sock, "rank", {"user": SERVER_NAME})
    rank = reply_rank.get("data", {}).get("rank")
    print(f"[{SERVER_NAME}] rank obtido: {rank}")

    reply_list = ref_request(ref_sock, "list", {})
    servers_info = reply_list.get("data", {}).get("list", {}) or {}

    if servers_info:
        coordinator_name = min(servers_info.items(), key=lambda kv: kv[1]["rank"])[0]
        coordinator = coordinator_name
        print(f"[{SERVER_NAME}] coordenador inicial: {coordinator}")


def maybe_send_heartbeat(ref_sock) -> None:
    """Envia heartbeat periódico ao servidor de referência."""
    global last_heartbeat
    now = time.time()
    if now - last_heartbeat >= HEARTBEAT_INTERVAL:
        ref_request(ref_sock, "heartbeat", {"user": SERVER_NAME})
        last_heartbeat = now


def sync_clock_with_ref(ref_sock) -> None:
    """
    Sincroniza o relógio lógico com o servidor de referência.
    Usa o serviço 'clock' do ref (algoritmo de Berkeley simplificado),
    que devolve o horário base. O update do clock lógico já é feito
    em ref_request, aqui apenas exibimos o ajuste.
    """
    reply = ref_request(ref_sock, "clock", {})
    data = reply.get("data", {}) or {}
    remote_time = data.get("time")
    print(f"[{SERVER_NAME}] sincronizou clock com ref (time={remote_time}, clock={logical_clock})")


def refresh_servers_and_maybe_elect(ref_sock, pub_sock) -> None:
    """
    Atualiza lista de servidores a partir do ref e, se houver mudança,
    elege novo coordenador (menor rank) e publica no tópico 'servers'.
    """
    global servers_info, coordinator

    reply_list = ref_request(ref_sock, "list", {})
    new_info = reply_list.get("data", {}).get("list", {}) or {}
    if not new_info:
        return

    servers_info = new_info
    new_coord = min(servers_info.items(), key=lambda kv: kv[1]["rank"])[0]

    if new_coord != coordinator:
        coordinator = new_coord
        print(f"[{SERVER_NAME}] novo coordenador eleito: {coordinator}")

        # avisa os demais via publicação no tópico 'servers'
        payload = {
            "service": "election",
            "data": {
                "coordinator": coordinator,
                "timestamp": ts(),
                "clock": next_clock(),
            },
        }
        pub_msgpack(pub_sock, "servers", payload)


# ---------------------------
# THREAD de replicação 
# ---------------------------

def replica_listener():
    """
    Escuta o tópico interno 'replica' e grava localmente
    logs que vieram de outros servidores.
    """
    ctx = zmq.Context.instance()
    sub = ctx.socket(zmq.SUB)
    sub.connect(XPUB)                       # XPUB do proxy
    sub.setsockopt_string(zmq.SUBSCRIBE, "replica")

    print(f"[{SERVER_NAME}] ouvindo réplicas no tópico 'replica'...")

    while True:
        topic, raw = sub.recv_multipart()
        if topic.decode() != "replica":
            continue

        try:
            payload = msgpack.unpackb(raw, raw=False)
        except Exception:
            continue

        # não replica o que foi originado por esse mesmo servidor
        if payload.get("origin") == SERVER_NAME:
            continue

        # atualiza clock lógico
        update_clock(payload.get("clock", 0))

        kind = payload.get("type")
        if kind == "publish":
            append(LOG_PUB, payload)
        elif kind == "message":
            append(LOG_MSG, payload)

        print(f"[{SERVER_NAME}] replicou registro de {payload.get('origin')} ({kind})")


# ---------------------------
# Loop principal do servidor
# ---------------------------

def main():
    global msg_count

    ctx = zmq.Context.instance()

    # REP: atende clientes via broker
    rep = ctx.socket(zmq.REP)
    rep.connect(BROKER)

    # PUB: publica mensagens para canais/usuários, réplicas e eleição
    pub = ctx.socket(zmq.PUB)
    pub.connect(XSUB)

    # REQ: fala com o servidor de referência
    ref = ctx.socket(zmq.REQ)
    ref.connect(REF_ADDR)

    reg = load_registry()

    # registra servidor na referência e inicia thread de replicação
    register_with_ref(ref)
    threading.Thread(target=replica_listener, daemon=True).start()

    print(f"[{SERVER_NAME}] iniciado. Aguardando requisições...")

    while True:
        req = recv_msgpack(rep)
        service = req.get("service")
        data = req.get("data", {}) or {}

        # clock lógico com base na mensagem recebida
        update_clock(data.get("clock", 0))

        if service == "publish":
            user = data.get("user")
            channel = data.get("channel")
            message = data.get("message")
            t = data.get("timestamp") or ts()

            if channel not in reg["channels"]:
                reply_clock = next_clock()
                send_msgpack(rep, {
                    "service": "publish",
                    "data": {
                        "status": "erro",
                        "message": "canal inexistente",
                        "timestamp": t,
                        "clock": reply_clock,
                    },
                })
                continue

            # payload da publicação
            payload_clock = next_clock()
            payload = {
                "type": "publish",
                "origin": SERVER_NAME,  # quem gerou
                "channel": channel,
                "user": user,
                "message": message,
                "timestamp": t,
                "clock": payload_clock,
            }

            # publica para os clientes do canal
            pub_msgpack(pub, channel, payload)
            # grava localmente
            append(LOG_PUB, payload)
            # 🔁 replica para outros servidores
            pub_msgpack(pub, "replica", payload)

            reply_clock = next_clock()
            send_msgpack(rep, {
                "service": "publish",
                "data": {
                    "status": "OK",
                    "message": "",
                    "timestamp": t,
                    "clock": reply_clock,
                },
            })
            msg_count += 1

        elif service == "message":
            src = data.get("src")
            dst = data.get("dst")
            message = data.get("message")
            t = data.get("timestamp") or ts()

            if reg["users"] and dst not in reg["users"]:
                reply_clock = next_clock()
                send_msgpack(rep, {
                    "service": "message",
                    "data": {
                        "status": "erro",
                        "message": "usuário inexistente",
                        "timestamp": t,
                        "clock": reply_clock,
                    },
                })
                continue

            payload_clock = next_clock()
            payload = {
                "type": "message",
                "origin": SERVER_NAME,
                "src": src,
                "dst": dst,
                "message": message,
                "timestamp": t,
                "clock": payload_clock,
            }

            # publica para o usuário de destino
            pub_msgpack(pub, dst, payload)
            # grava localmente
            append(LOG_MSG, payload)
            # 🔁 replica para outros servidores
            pub_msgpack(pub, "replica", payload)

            reply_clock = next_clock()
            send_msgpack(rep, {
                "service": "message",
                "data": {
                    "status": "OK",
                    "message": "",
                    "timestamp": t,
                    "clock": reply_clock,
                },
            })
            msg_count += 1

        elif service == "register_user":
            u = data.get("user")
            if u and u not in reg["users"]:
                reg["users"].append(u)
                save_registry(reg)

            reply_clock = next_clock()
            send_msgpack(rep, {
                "service": "register_user",
                "data": {
                    "status": "OK",
                    "users": reg["users"],
                    "timestamp": ts(),
                    "clock": reply_clock,
                },
            })

        elif service == "list_channels":
            reply_clock = next_clock()
            send_msgpack(rep, {
                "service": "list_channels",
                "data": {
                    "status": "OK",
                    "channels": reg["channels"],
                    "timestamp": ts(),
                    "clock": reply_clock,
                },
            })

        elif service == "clock":
            # este serviço é chamado por outros processos, mas aqui
            # mantemos para compatibilidade com o enunciado
            reply_clock = next_clock()
            send_msgpack(rep, {
                "service": "clock",
                "data": {
                    "time": ts(),
                    "timestamp": ts(),
                    "clock": reply_clock,
                },
            })

        elif service == "election":
            # responde requisições de eleição conforme enunciado
            reply_clock = next_clock()
            send_msgpack(rep, {
                "service": "election",
                "data": {
                    "election": "OK",
                    "timestamp": ts(),
                    "clock": reply_clock,
                },
            })

        else:
            reply_clock = next_clock()
            send_msgpack(rep, {
                "service": service,
                "data": {
                    "status": "erro",
                    "message": "serviço desconhecido",
                    "timestamp": ts(),
                    "clock": reply_clock,
                },
            })

        # a cada N mensagens: sincroniza relógio com o ref
        # e atualiza coordenador (eleição baseada no rank)
        if msg_count > 0 and msg_count % SYNC_EVERY == 0:
            sync_clock_with_ref(ref)
            refresh_servers_and_maybe_elect(ref, pub)

        # heartbeat pro servidor de referência
        maybe_send_heartbeat(ref)


if __name__ == "__main__":
    main()
