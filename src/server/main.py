import zmq
import json
import time
import os

# Arquivos para persistência
USERS_FILE = 'data/users.json'
CHANNELS_FILE = 'data/channels.json'

# --- Funções de Persistência ---

def load_data(filepath):
    """Carrega dados de um arquivo JSON."""
    # Garante que o diretório 'data' exista
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_data(filepath, data):
    """Salva dados em um arquivo JSON, garantindo unicidade."""
    # Garante que o diretório 'data' exista
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    unique_data = sorted(list(set(data)))
    with open(filepath, 'w') as f:
        json.dump(unique_data, f, indent=4)

# --- Carregar dados na inicialização ---
users = load_data(USERS_FILE)
channels = load_data(CHANNELS_FILE)
print(f"Servidor iniciado. {len(users)} usuários, {len(channels)} canais carregados.")

# --- Configuração ZMQ ---
context = zmq.Context()

# Socket REP para responder aos clientes (via broker)
rep_socket = context.socket(zmq.REP)
rep_socket.connect("tcp://broker:5556")

# Socket PUB para publicar (será usado na Etapa 2)
pub_socket = context.socket(zmq.PUB)
pub_socket.connect("tcp://proxy:5557")

print("Servidor pronto para receber requisições...")

# --- Loop Principal de Requisições ---
while True:
    try:
        # 1. Recebe a requisição (espera-se JSON)
        message = rep_socket.recv_json()
        print(f"Recebido: {message}")

        service = message.get('service')
        data = message.get('data', {})
        response = {}

        # 2. Roteia a requisição para o serviço correto
        
        if service == 'login':
            user = data.get('user')
            if user:
                if user not in users:
                    users.append(user)
                    save_data(USERS_FILE, users) # Persiste
                
                response = {
                    "service": "login",
                    "data": {
                        "status": "sucesso",
                        "timestamp": int(time.time())
                    }
                }
            else:
                response = {
                    "service": "login",
                    "data": {
                        "status": "erro",
                        "description": "Nome de usuário não fornecido",
                        "timestamp": int(time.time())
                    }
                }

        elif service == 'users':
            response = {
                "service": "users",
                "data": {
                    "users": users,
                    "timestamp": int(time.time())
                }
            }

        elif service == 'channel':
            channel = data.get('channel')
            if channel:
                if channel not in channels:
                    channels.append(channel)
                    save_data(CHANNELS_FILE, channels) # Persiste
                    status = "sucesso"
                    desc = ""
                else:
                    status = "erro"
                    desc = "Canal já existe"
                
                response = {
                    "service": "channel",
                    "data": {
                        "status": status,
                        "description": desc,
                        "timestamp": int(time.time())
                    }
                }
            else:
                 response = {
                    "service": "channel",
                    "data": {
                        "status": "erro",
                        "description": "Nome de canal não fornecido",
                        "timestamp": int(time.time())
                    }
                }

        elif service == 'channels':
            response = {
                "service": "channels",
                "data": {
                    # Seguindo a especificação (usando a chave "users" para a lista de canais)
                    "users": channels, 
                    "timestamp": int(time.time())
                }
            }

        else:
            response = {
                "service": "unknown",
                "data": {
                    "status": "erro",
                    "description": "Serviço desconhecido",
                    "timestamp": int(time.time())
                }
            }

        # 3. Envia a resposta JSON
        rep_socket.send_json(response)
        print(f"Enviado: {response}")

    except Exception as e:
        print(f"Erro ao processar: {e}")
        # Tenta enviar uma resposta de erro se possível
        try:
            rep_socket.send_json({
                "service": "internal_error",
                "data": {
                    "status": "erro",
                    "description": str(e),
                    "timestamp": int(time.time())
                }
            })
        except zmq.ZMQError as ze:
            print(f"Erro ZMQ ao enviar erro: {ze}")