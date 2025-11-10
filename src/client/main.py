import os
import random
import time
from datetime import datetime

import zmq
import msgpack

# Endereços (podem ser sobrescritos por variáveis de ambiente)
BROKER = os.getenv("BROKER_REQ", "tcp://localhost:5555")   # broker (ROUTER)
XPUB   = os.getenv("PROXY_XPUB", "tcp://localhost:5558")   # proxy (XPUB)

USERNAME = os.getenv("USERNAME", f"user{random.randint(1000,9999)}")  # nome do usuário
AUTO = os.getenv("AUTO_CLIENT", "0") == "1"                           # cliente automático?

logical_clock = 0  # relógio lógico local (Lamport)


def ts() -> str:
    """Timestamp físico simples."""
    return datetime.utcnow().isoformat() + "Z"


def update_clock(remote_clock: int) -> None:
    """Atualiza relógio lógico com base em outro clock."""
    global logical_clock
    logical_clock = max(logical_clock, int(remote_clock or 0)) + 1


def next_clock() -> int:
    """Incrementa o relógio lógico e devolve valor atual."""
    global logical_clock
    logical_clock += 1
    return logical_clock


def send_req(sock, service: str, data: dict) -> dict:
    """
    Envia requisição em MessagePack para o servidor,
    já incluindo timestamp e clock.
    """
    # incrementa clock antes de enviar
    data = dict(data or {})
    data.setdefault("timestamp", ts())
    data.setdefault("clock", next_clock())

    payload = {"service": service, "data": data}
    sock.send(msgpack.packb(payload, use_bin_type=True))

    # recebe resposta e atualiza clock com o clock recebido
    rep_raw = sock.recv()
    reply = msgpack.unpackb(rep_raw, raw=False)
    rdata = reply.get("data", {}) or {}
    update_clock(rdata.get("clock", 0))
    return reply


def main():
    ctx = zmq.Context()

    # REQ para falar com o servidor via broker
    req = ctx.socket(zmq.REQ)
    req.connect(BROKER)

    # SUB para receber mensagens do proxy
    sub = ctx.socket(zmq.SUB)
    sub.connect(XPUB)

    # registra usuário no servidor
    send_req(req, "register_user", {"user": USERNAME})

    # obtém lista de canais
    ch_resp = send_req(req, "list_channels", {})
    channels = (ch_resp.get("data", {}) or {}).get("channels", []) or ["general"]

    # assina o próprio nome (mensagens diretas) e todos os canais
    sub.setsockopt_string(zmq.SUBSCRIBE, USERNAME)
    for ch in channels:
        sub.setsockopt_string(zmq.SUBSCRIBE, ch)

    print(f"[{USERNAME}] assinando {USERNAME} + {channels}")

    poller = zmq.Poller()
    poller.register(sub, zmq.POLLIN)

    if AUTO:
        # modo automático: manda 10 mensagens por vez em canais aleatórios
        while True:
            canal = random.choice(channels)
            for i in range(10):
                send_req(
                    req,
                    "publish",
                    {
                        "user": USERNAME,
                        "channel": canal,
                        "message": f"auto-msg {i} de {USERNAME} em #{canal}",
                    },
                )
                time.sleep(0.05)

            # vê se chegaram publicações enquanto isso
            socks = dict(poller.poll(50))
            if socks.get(sub) == zmq.POLLIN:
                topic, raw = sub.recv_multipart()
                try:
                    payload = msgpack.unpackb(raw, raw=False)
                    # atualiza relógio com clock da msg recebida
                    update_clock(payload.get("clock", 0))
                    print(f"[{USERNAME}] <- ({topic.decode()}) {payload}")
                except Exception:
                    pass
    else:
        # modo "somente ouvindo"
        while True:
            topic, raw = sub.recv_multipart()
            try:
                payload = msgpack.unpackb(raw, raw=False)
                update_clock(payload.get("clock", 0))
                print(f"[{USERNAME}] <- ({topic.decode()}) {payload}")
            except Exception:
                pass


if __name__ == "__main__":
    main()
