import zmq, os, random, time        # zmq para rede, os/env, random/time para client automático
from datetime import datetime
import msgpack                      # MessagePack para falar com o servidor

BROKER = os.getenv("BROKER_REQ", "tcp://localhost:5555")  # endereço do broker (ROUTER)
XPUB   = os.getenv("PROXY_XPUB", "tcp://localhost:5558")  # endereço do proxy (XPUB)
USERNAME = os.getenv("USERNAME", f"user{random.randint(1000,9999)}")  # nome do usuário
AUTO = os.getenv("AUTO_CLIENT", "0") == "1"                           # modo automático?

def ts():
    return datetime.utcnow().isoformat() + "Z"             # timestamp padrão

def send_req(sock, obj: dict):
    # envia uma requisição em msgpack e recebe a resposta em msgpack
    sock.send(msgpack.packb(obj, use_bin_type=True))
    rep = sock.recv()
    return msgpack.unpackb(rep, raw=False)

def main():
    ctx = zmq.Context()
    req = ctx.socket(zmq.REQ); req.connect(BROKER)         # socket para fazer requisições
    sub = ctx.socket(zmq.SUB); sub.connect(XPUB)           # socket para receber publicações

    # registra usuário no servidor
    send_req(req, {"service": "register_user", "data": {"user": USERNAME}})

    # pega lista de canais disponíveis
    ch_resp = send_req(req, {"service": "list_channels", "data": {}})
    channels = (ch_resp.get("data", {}) or {}).get("channels", []) or ["general"]

    # assina o próprio nome e todos os canais
    sub.setsockopt_string(zmq.SUBSCRIBE, USERNAME)
    for ch in channels:
        sub.setsockopt_string(zmq.SUBSCRIBE, ch)

    print(f"[{USERNAME}] assinando {USERNAME} + {channels}")

    poller = zmq.Poller(); poller.register(sub, zmq.POLLIN)  # facilita ver se chegou algo

    if AUTO:
        # modo automático: manda 10 mensagens por canal escolhido aleatoriamente
        while True:
            canal = random.choice(channels)
            for i in range(10):
                send_req(
                    req,
                    {
                        "service": "publish",
                        "data": {
                            "user": USERNAME,
                            "channel": canal,
                            "message": f"auto-msg {i} de {USERNAME} em #{canal}",
                            "timestamp": ts(),
                        },
                    },
                )
                time.sleep(0.05)                             # pequeno delay entre as msgs

            # lê rapidamente o que chegou enquanto isso
            socks = dict(poller.poll(50))
            if socks.get(sub) == zmq.POLLIN:
                topic, raw = sub.recv_multipart()
                try:
                    payload = msgpack.unpackb(raw, raw=False)
                    print(f"[{USERNAME}] <- ({topic.decode()}) {payload}")
                except Exception:
                    pass
    else:
        # modo "somente ouvindo" (útil para testes manuais)
        while True:
            topic, raw = sub.recv_multipart()
            try:
                payload = msgpack.unpackb(raw, raw=False)
                print(f"[{USERNAME}] <- ({topic.decode()}) {payload}")
            except Exception:
                pass

if __name__ == "__main__":
    main()
