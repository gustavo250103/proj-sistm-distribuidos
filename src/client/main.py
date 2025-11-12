import zmq
import json
import time

# Endereços (como no docker-compose.yml)
req_address = "broker"
req_port = 5555

sub_address = "proxy"
sub_port = 5558

# --- Configuração ZMQ ---
context = zmq.Context()

print("Conectando ao broker...")
req_socket = context.socket(zmq.REQ)
req_socket.connect(f"tcp://{req_address}:{req_port}")

# O socket SUB será configurado e usado na Etapa 2
# sub_socket = context.socket(zmq.SUB)
# sub_socket.connect(f"tcp://{sub_address}:{sub_port}")
# sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")

# --- Funções Auxiliares ---

def send_request(service, data):
    """Função genérica para enviar uma requisição e receber uma resposta."""
    request_data = {
        "service": service,
        "data": data
    }
    print(f"\n[Enviando REQ]: {request_data}")
    req_socket.send_json(request_data)
    
    response = req_socket.recv_json()
    print(f"[Recebido REP]: {response}")
    return response.get('data', {})

def main_menu(username):
    """Loop principal do menu do cliente."""
    while True:
        print("\n--- Menu Principal ---")
        print("1. Listar usuários")
        print("2. Criar canal")
        print("3. Listar canais")
        print("q. Sair")
        choice = input("Escolha uma opção: ").strip()

        if choice == '1':
            data = {"timestamp": int(time.time())}
            send_request("users", data)
        
        elif choice == '2':
            channel_name = input("Nome do novo canal: ").strip()
            if channel_name:
                data = {
                    "channel": channel_name,
                    "timestamp": int(time.time())
                }
                send_request("channel", data)
        
        elif choice == '3':
            data = {"timestamp": int(time.time())}
            send_request("channels", data)

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
        # 2. Entrar no menu principal
        main_menu(username)
    else:
        print(f"Falha no login: {login_response.get('description')}")
        
    print("Encerrando cliente.")
    req_socket.close()
    context.term()