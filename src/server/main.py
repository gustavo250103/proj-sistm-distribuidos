import zmq
import json
import time
import os

# Arquivos para persistência
DATA_DIR = 'data'
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
CHANNELS_FILE = os.path.join(DATA_DIR, 'channels.json')
MESSAGES_FILE = os.path.join(DATA_DIR, 'messages.log') # Novo arquivo de log

# --- Funções de Persistência ---

def ensure_data_dir():
    """Garante que o diretório 'data' exista."""
    os.makedirs(DATA_DIR, exist_ok=True)

def load_data(filepath):
    """Carrega dados de um arquivo JSON."""
    ensure_data_dir()
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_data(filepath, data):
    """Salva dados em um arquivo JSON."""
    ensure_data_dir()
    unique_data = sorted(list(set(data)))
    with open(filepath, 'w') as f:
        json.dump(unique_data, f, indent=4)

def log_message(message_data):
    """Adiciona uma mensagem ao log de persistência."""
    ensure_data_dir()
    with open(MESSAGES_FILE, 'a') as f:
        f.write(json.dumps(message_data) + '\n')

# --- Carregar dados na inicialização ---
users = load_data(USERS_FILE)
channels = load_data(CHANNELS_FILE)
print(f"Servidor iniciado. {len(users)} usuários, {len(channels)} canais carregados.")

# --- Configuração ZMQ ---
context = zmq.Context()

# Socket REP para responder aos clientes (via broker)
rep_socket = context.socket(zmq.REP)
rep_socket.connect("tcp://broker:5556")

# Socket PUB para publicar (agora será usado)
pub_socket = context.socket(zmq.PUB)
pub_socket.connect("tcp://proxy:5557")

print("Servidor pronto para receber requisições...")

# --- Loop Principal de Requisições ---
while True:
    try:
        # 1. Recebe a requisição (espera-se JSON)
        message_str = rep_socket.recv_string()
        message = json.loads(message_str)
        print(f"Recebido: {message}")

        service = message.get('service')
        data = message.get('data', {})
        response = {}
        
        current_time = int(time.time())

        # 2. Roteia a requisição para o serviço correto
        
        if service == 'login':
            user = data.get('user')
            if user:
                if user not in users:
                    users.append(user)
                    save_data(USERS_FILE, users)
                response = {"status": "sucesso"}
            else:
                response = {"status": "erro", "description": "Nome de usuário não fornecido"}

        elif service == 'users':
            response = {"users": users}

        elif service == 'channel':
            channel = data.get('channel')
            if channel:
                if channel not in channels:
                    channels.append(channel)
                    save_data(CHANNELS_FILE, channels)
                    response = {"status": "sucesso"}
                else:
                    response = {"status": "erro", "description": "Canal já existe"}
            else:
                 response = {"status": "erro", "description": "Nome de canal não fornecido"}

        elif service == 'channels':
            response = {"users": channels} # Mantendo a chave "users" conforme Etapa 1

        # --- NOVOS SERVIÇOS (ETAPA 2) ---
        
        elif service == 'publish':
            user = data.get('user')
            channel = data.get('channel')
            message_content = data.get('message')
            
            if channel in channels:
                # 1. Preparar a mensagem pública
                pub_message = {
                    "type": "channel",
                    "channel": channel,
                    "user": user,
                    "message": message_content,
                    "timestamp": current_time
                }
                # 2. Publicar no TÓPICO (o nome do canal)
                pub_socket.send_multipart([
                    channel.encode('utf-8'), 
                    json.dumps(pub_message).encode('utf-8')
                ])
                # 3. Persistir
                log_message(pub_message)
                response = {"status": "OK"}
            else:
                response = {"status": "erro", "message": "Canal não existe"}

        elif service == 'message':
            src_user = data.get('src')
            dst_user = data.get('dst')
            message_content = data.get('message')
            
            if dst_user in users:
                # 1. Preparar a mensagem privada
                pub_message = {
                    "type": "private",
                    "from": src_user,
                    "to": dst_user,
                    "message": message_content,
                    "timestamp": current_time
                }
                # 2. Publicar no TÓPICO (o nome do usuário de destino)
                pub_socket.send_multipart([
                    dst_user.encode('utf-8'),
                    json.dumps(pub_message).encode('utf-8')
                ])
                # 3. Persistir
                log_message(pub_message)
                response = {"status": "OK"}
            else:
                response = {"status": "erro", "message": "Usuário não existe"}

        else:
            response = {"status": "erro", "description": "Serviço desconhecido"}

        # 3. Envia a resposta JSON
        final_response = {
            "service": service,
            "data": {**response, "timestamp": current_time}
        }
        rep_socket.send_json(final_response)
        print(f"Enviado: {final_response}")

    except Exception as e:
        print(f"Erro ao processar: {e}")
        try:
            rep_socket.send_json({
                "service": "internal_error",
                "data": {"status": "erro", "description": str(e), "timestamp": int(time.time())}
            })
        except zmq.ZMQError as ze:
            print(f"Erro ZMQ ao enviar erro: {ze}")