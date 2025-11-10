import os
import json
from datetime import datetime

import zmq

DATA = os.getenv("PERSIST_DIR", "./data")
os.makedirs(DATA, exist_ok=True)

SERVERS_FILE = os.path.join(DATA, "ref_servers.json")

logical_clock = 0


def ts() -> str:
    return datetime.utcnow().isoformat() + "Z"


def load_servers():
    if os.path.exists(SERVERS_FILE):
        return json.load(open(SERVERS_FILE, "r", encoding="utf-8"))
    return {}


def save_servers(servers):
    json.dump(servers, open(SERVERS_FILE, "w", encoding="utf-8"))


def update_clock(remote_clock: int):
    global logical_clock
    logical_clock = max(logical_clock, int(remote_clock or 0)) + 1


def next_clock() -> int:
    global logical_clock
    logical_clock += 1
    return logical_clock


def main():
    ctx = zmq.Context.instance()
    rep = ctx.socket(zmq.REP)
    rep.bind("tcp://*:6000")

    servers = load_servers()

    print("[ref] servidor de referência iniciado em tcp://*:6000")

    while True:
        msg = rep.recv_json()
        service = msg.get("service")
        data = msg.get("data", {}) or {}

        update_clock(data.get("clock", 0))

        if service == "rank":
            # registra servidor se ainda não existir, com próximo rank
            name = data.get("user")
            if name and name not in servers:
                rank = len(servers) + 1
                servers[name] = {
                    "rank": rank,
                    "last_beat": ts(),
                }
                save_servers(servers)

            reply = {
                "service": "rank",
                "data": {
                    "rank": servers.get(name, {}).get("rank"),
                    "timestamp": ts(),
                    "clock": next_clock(),
                },
            }
            rep.send_json(reply)

        elif service == "list":
            # devolve lista de servidores e ranks
            reply = {
                "service": "list",
                "data": {
                    "list": servers,
                    "timestamp": ts(),
                    "clock": next_clock(),
                },
            }
            rep.send_json(reply)

        elif service == "heartbeat":
            # atualiza last_beat do servidor
            name = data.get("user")
            if name in servers:
                servers[name]["last_beat"] = ts()
                save_servers(servers)

            reply = {
                "service": "heartbeat",
                "data": {
                    "timestamp": ts(),
                    "clock": next_clock(),
                },
            }
            rep.send_json(reply)

        elif service == "clock":
            # usado para sincronização de relógio (Berkeley simpli.)
            reply = {
                "service": "clock",
                "data": {
                    "time": ts(),
                    "timestamp": ts(),
                    "clock": next_clock(),
                },
            }
            rep.send_json(reply)

        else:
            reply = {
                "service": service,
                "data": {
                    "status": "erro",
                    "message": "serviço desconhecido",
                    "timestamp": ts(),
                    "clock": next_clock(),
                },
            }
            rep.send_json(reply)


if __name__ == "__main__":
    main()
