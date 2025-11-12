import sys
import time
import threading
import zmq
import msgpack
from datetime import datetime

# Endereços
REQ_ADDR = "tcp://broker:5555"
SUB_ADDR = "tcp://proxy:5558"

context = zmq.Context()

req_socket = context.socket(zmq.REQ)
req_socket.connect(REQ_ADDR)

sub_socket = context.socket(zmq.SUB)
sub_socket.connect(SUB_ADDR)

req_lock = threading.Lock()


def recv_msgpack(sock):
    raw = sock.recv()
    return msgpack.unpackb(raw, raw=False)


def send_msgpack(sock, obj):
    sock.send(msgpack.packb(obj, use_bin_type=True))


def receiver_thread(username):
    print(f"\n[Receptor] Inscrito no tópico: {username}")
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, username)

    while True:
        try:
            topic, payload = sub_socket.recv_multipart()
            topic = topic.decode("utf-8")
            message = msgpack.unpackb(payload, raw=False)
            dt = datetime.fromtimestamp(message["timestamp"]).strftime("%H:%M:%S")

            print("\r" + " " * 80 + "\r", end="")

            if message.get("type") == "channel":
                print(f"[{dt}][Canal: {topic}] {message['user']}: {message['message']}")
            elif message.get("type") == "private":
                print(f"[{dt}][Privado de {message['from']}]: {message['message']}")

            print("Escolha uma opção: ", end="", flush=True)
        except (zmq.ZMQError, Exception) as err:
            print(f"\n[Receptor] Erro: {err}. Encerrando thread.")
            break


def send_request(service, data):
    payload = {"service": service, "data": data}
    with req_lock:
        try:
            send_msgpack(req_socket, payload)
            response = recv_msgpack(req_socket)
        except zmq.ZMQError as err:
            print(f"Erro de comunicação com o broker: {err}")
            return {"status": "erro", "description": "Falha no broker"}
    print(f"\n[Resposta do Servidor]: {response.get('data')}")
    return response.get("data", {})


def main_menu(username):
    print("\n--- Menu Principal ---")
    print("1. Listar usuários")
    print("2. Criar canal")
    print("3. Listar canais")
    print("4. Enviar mensagem (canal)")
    print("5. Enviar mensagem (usuário)")
    print("6. Inscrever-se em canal")
    print("q. Sair")

    while True:
        choice = input("Escolha uma opção: ").strip()

        if choice == "1":
            send_request("users", {"timestamp": int(time.time())})

        elif choice == "2":
            channel_name = input("  Nome do novo canal: ").strip()
            if channel_name:
                send_request("channel", {"channel": channel_name, "timestamp": int(time.time())})

        elif choice == "3":
            send_request("channels", {"timestamp": int(time.time())})

        elif choice == "4":
            channel_name = input("  Nome do canal: ").strip()
            message = input("  Mensagem: ").strip()
            if channel_name and message:
                send_request("publish", {
                    "user": username,
                    "channel": channel_name,
                    "message": message,
                    "timestamp": int(time.time()),
                })

        elif choice == "5":
            dst_user = input("  Usuário destino: ").strip()
            message = input("  Mensagem: ").strip()
            if dst_user and message:
                send_request("message", {
                    "src": username,
                    "dst": dst_user,
                    "message": message,
                    "timestamp": int(time.time()),
                })

        elif choice == "6":
            channel_name = input("  Canal para inscrever-se: ").strip()
            if channel_name:
                sub_socket.setsockopt_string(zmq.SUBSCRIBE, channel_name)
                print(f"[Cliente] Inscrito no canal: {channel_name}")

        elif choice.lower() == "q":
            print("Saindo...")
            break

        else:
            print("Opção inválida.")


if __name__ == "__main__":
    print("Cliente iniciado.")
    username = ""
    while not username:
        username = input("Digite seu nome de usuário para login: ").strip()

    login_resp = send_request("login", {"user": username, "timestamp": int(time.time())})
    if login_resp.get("status") == "sucesso":
        print(f"Login de '{username}' realizado com sucesso.")
        threading.Thread(target=receiver_thread, args=(username,), daemon=True).start()
        main_menu(username)
    else:
        print(f"Falha no login: {login_resp.get('description')}")

    req_socket.close()
    sub_socket.close()
    context.term()
    sys.exit(0)
