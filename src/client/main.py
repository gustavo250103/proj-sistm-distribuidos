import zmq
import json
import time
import threading
import sys
from datetime import datetime

# Endereços
req_address = "broker"
req_port = 5555
sub_address = "proxy"
sub_port = 5558

# --- Configuração ZMQ ---
context = zmq.Context()

# Socket REQ (para enviar comandos)
req_socket = context.socket(zmq.REQ)
req_socket.connect(f"tcp://{req_address}:{req_port}")

# Socket SUB (para receber mensagens)
sub_socket = context.socket(zmq.SUB)
sub_socket.connect(f"tcp://{sub_address}:{sub_port}")

# Trava para proteger o socket REQ (REQ é síncrono)
req_lock = threading.Lock()

# --- Thread Receptora (PUB/SUB) ---

def receiver_thread(username):
    """Thread que escuta mensagens do sub_socket."""
    print(f"\n[Receptor] Inscrito no tópico: {username}")
    sub_socket.setsockopt_string(zmq.SUBSCRIBE, username)
    
    while True:
        try:
            # Espera por uma mensagem (tópico + dados)
            [topic, data] = sub_socket.recv_multipart()
            
            message = json.loads(data.decode('utf-8'))
            topic = topic.decode('utf-8')
            
            dt = datetime.fromtimestamp(message['timestamp']).strftime('%H:%M:%S')
            
            # Limpa a linha de input atual para imprimir a mensagem
            print("\r" + " " * 80 + "\r", end='')
            
            if message.get('type') == 'channel':
                print(f"[{dt}][Canal: {topic}] {message['user']}: {message['message']}")
            elif message.get('type') == 'private':
                print(f"[{dt}][Privado de: {message['from']}]: {message['message']}")
            
            # Redesenha o prompt de input
            print("Escolha uma opção: ", end='', flush=True)

        except (zmq.ZMQError, Exception) as e:
            print(f"\n[Receptor] Erro: {e}. Encerrando thread.")
            break

# --- Funções Auxiliares ---

def send_request(service, data):
    """Função genérica para enviar uma requisição e receber uma resposta."""
    request_data = {
        "service": service,
        "data": data
    }
    
    # O socket REQ não é thread-safe, usamos uma trava
    with req_lock:
        try:
            req_socket.send_json(request_data)
            response = req_socket.recv_json()
        except zmq.ZMQError as e:
            print(f"Erro de comunicação com o broker: {e}")
            return {"data": {"status": "erro", "description": "Falha no broker"}}
            
    print(f"\n[Resposta do Servidor]: {response.get('data')}")
    return response.get('data', {})

def main_menu(username):
    """Loop principal do menu do cliente."""
    print("\n--- Menu Principal ---")
    print("1. Listar usuários")
    print("2. Criar canal")
    print("3. Listar canais")
    print("4. Enviar Mensagem (Canal)")
    print("5. Enviar Mensagem (Usuário)")
    print("6. Inscrever-se em Canal")
    print("q. Sair")
    
    while True:
        choice = input("Escolha uma opção: ").strip()

        if choice == '1':
            send_request("users", {"timestamp": int(time.time())})
        
        elif choice == '2':
            channel_name = input("  Nome do novo canal: ").strip()
            if channel_name:
                send_request("channel", {"channel": channel_name, "timestamp": int(time.time())})
        
        elif choice == '3':
            send_request("channels", {"timestamp": int(time.time())})

        elif choice == '4': # Publish
            channel_name = input("  Nome do canal: ").strip()
            message = input("  Mensagem: ").strip()
            if channel_name and message:
                send_request("publish", {
                    "user": username,
                    "channel": channel_name,
                    "message": message,
                    "timestamp": int(time.time())
                })
        
        elif choice == '5': # Message
            dst_user = input("  Nome do usuário de destino: ").strip()
            message = input("  Mensagem: ").strip()
            if dst_user and message:
                send_request("message", {
                    "src": username,
                    "dst": dst_user,
                    "message": message,
                    "timestamp": int(time.time())
                })
        
        elif choice == '6': # Subscribe
            channel_name = input("  Nome do canal para inscrever-se: ").strip()
            if channel_name:
                sub_socket.setsockopt_string(zmq.SUBSCRIBE, channel_name)
                print(f"[Cliente] Inscrito no canal: {channel_name}")

        elif choice.lower() == 'q':
            print("Saindo...")
            break
        
        else:
            print("Opção inválida.")

# --- Ponto de Entrada ---
if __name__ == "__main__":
    print("Cliente iniciado.")
    username = ""
    while not username:
        username = input("Digite seu nome de usuário para login: ").strip()

    # 1. Realizar Login (Obrigatório)
    login_data = {
        "user": username,
        "timestamp": int(time.time())
    }
    login_response = send_request("login", login_data)
    
    if login_response.get("status") == "sucesso":
        print(f"Login de '{username}' realizado com sucesso.")
        
        # 2. Iniciar a thread receptora
        r_thread = threading.Thread(target=receiver_thread, args=(username,), daemon=True)
        r_thread.start()
        
        # 3. Entrar no menu principal
        main_menu(username)
    else:
        print(f"Falha no login: {login_response.get('description')}")
        
    print("Encerrando cliente.")
    req_socket.close()
    sub_socket.close()
    context.term()
    sys.exit(0)