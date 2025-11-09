import zmq, json, os, time
from datetime import datetime

PORT = os.getenv("REF_PORT", "6000")             # porta do servidor de referência
ADDR = f"tcp://*:{PORT}"                         # endereço de bind
DATA = os.getenv("REF_DATA", "./data/ref.json")  # onde guarda a lista de servidores

servers = {}  # {nome: {"rank": n, "last_beat": timestamp}}
next_rank = 1
clock = 0     # relógio lógico local

def ts(): return datetime.utcnow().isoformat() + "Z"

def update_clock(remote_clock):
    """atualiza o relógio lógico local"""
    global clock
    clock = max(clock, remote_clock) + 1

def save():
    json.dump(servers, open(DATA, "w"), indent=2)

def main():
    global next_rank, clock
    ctx = zmq.Context()
    rep = ctx.socket(zmq.REP)
    rep.bind(ADDR)
    print(f"[ref] listening on {ADDR}")

    while True:
        msg = rep.recv_json()
        data = msg.get("data", {})
        svc = msg.get("service")
        remote_clock = data.get("clock", 0)
        update_clock(remote_clock)

        if svc == "rank":
            name = data.get("user")
            if name not in servers:
                servers[name] = {"rank": next_rank, "last_beat": time.time()}
                next_rank += 1
                save()
            rep.send_json({"service": "rank", "data": {"rank": servers[name]["rank"], "timestamp": ts(), "clock": clock}})

        elif svc == "list":
            rep.send_json({"service": "list", "data": {"list": servers, "timestamp": ts(), "clock": clock}})

        elif svc == "heartbeat":
            name = data.get("user")
            if name in servers:
                servers[name]["last_beat"] = time.time()
            rep.send_json({"service": "heartbeat", "data": {"timestamp": ts(), "clock": clock}})

        else:
            rep.send_json({"service": svc, "data": {"status": "erro", "msg": "serviço desconhecido", "clock": clock}})

if __name__ == "__main__":
    main()
