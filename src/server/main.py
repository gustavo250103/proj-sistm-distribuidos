import os
import json
import time
import zmq
import msgpack

# Arquivos para persistência
DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
CHANNELS_FILE = os.path.join(DATA_DIR, "channels.json")
MESSAGES_FILE = os.path.join(DATA_DIR, "messages.log")


# ---------------------------
# Persistência básica
# ---------------------------

def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_data(filepath):
    ensure_data_dir()
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []


def save_data(filepath, data):
    ensure_data_dir()
    unique_data = sorted(list(set(data)))
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(unique_data, f, indent=2, ensure_ascii=False)


def log_message(message_data):
    ensure_data_dir()
    with open(MESSAGES_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(message_data, ensure_ascii=False) + "\n")


# ---------------------------
# Helpers MessagePack
# ---------------------------

def recv_msgpack(sock):
    raw = sock.recv()
    return msgpack.unpackb(raw, raw=False)


def send_msgpack(sock, obj):
    sock.send(msgpack.packb(obj, use_bin_type=True))


def pub_msgpack(sock, topic, obj):
    sock.send_multipart([
        topic.encode("utf-8"),
        msgpack.packb(obj, use_bin_type=True),
    ])


# ---------------------------
# Estado inicial
# ---------------------------

users = load_data(USERS_FILE)
channels = load_data(CHANNELS_FILE)
print(f"Servidor iniciado. {len(users)} usuários, {len(channels)} canais carregados.")

context = zmq.Context()

rep_socket = context.socket(zmq.REP)
rep_socket.connect("tcp://broker:5556")

pub_socket = context.socket(zmq.PUB)
pub_socket.connect("tcp://proxy:5557")

print("Servidor pronto para receber requisições...")


# ---------------------------
# Loop principal
# ---------------------------

while True:
    try:
        message = recv_msgpack(rep_socket)
        service = message.get("service")
        data = message.get("data", {}) or {}
        response = {}
        current_time = int(time.time())

        if service == "login":
            user = data.get("user")
            if user:
                if user not in users:
                    users.append(user)
                    save_data(USERS_FILE, users)
                response = {"status": "sucesso"}
            else:
                response = {"status": "erro", "description": "Nome de usuário não fornecido"}

        elif service == "users":
            response = {"users": users}

        elif service == "channel":
            channel = data.get("channel")
            if channel:
                if channel not in channels:
                    channels.append(channel)
                    save_data(CHANNELS_FILE, channels)
                    response = {"status": "sucesso"}
                else:
                    response = {"status": "erro", "description": "Canal já existe"}
            else:
                response = {"status": "erro", "description": "Nome de canal não fornecido"}

        elif service == "channels":
            response = {"users": channels}  # mantém compatibilidade da Etapa 1

        elif service == "publish":
            user = data.get("user")
            channel = data.get("channel")
            message_content = data.get("message")
            if channel in channels:
                pub_message = {
                    "type": "channel",
                    "channel": channel,
                    "user": user,
                    "message": message_content,
                    "timestamp": current_time,
                }
                pub_msgpack(pub_socket, channel, pub_message)
                log_message(pub_message)
                response = {"status": "OK"}
            else:
                response = {"status": "erro", "message": "Canal não existe"}

        elif service == "message":
            src_user = data.get("src")
            dst_user = data.get("dst")
            message_content = data.get("message")
            if dst_user in users:
                pub_message = {
                    "type": "private",
                    "from": src_user,
                    "to": dst_user,
                    "message": message_content,
                    "timestamp": current_time,
                }
                pub_msgpack(pub_socket, dst_user, pub_message)
                log_message(pub_message)
                response = {"status": "OK"}
            else:
                response = {"status": "erro", "message": "Usuário não existe"}

        else:
            response = {"status": "erro", "description": "Serviço desconhecido"}

        final_response = {
            "service": service,
            "data": {**response, "timestamp": current_time},
        }
        send_msgpack(rep_socket, final_response)

    except Exception as e:
        print(f"Erro ao processar: {e}")
        try:
            send_msgpack(rep_socket, {
                "service": "internal_error",
                "data": {
                    "status": "erro",
                    "description": str(e),
                    "timestamp": int(time.time()),
                },
            })
        except zmq.ZMQError as ze:
            print(f"Erro ZMQ ao enviar erro: {ze}")
