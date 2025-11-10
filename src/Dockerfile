# Imagem oficial do Python (leve)
FROM python:3.13.7-alpine3.21

# Diretório de trabalho dentro do container
WORKDIR /app

# Copia todo o projeto
COPY . .

# Instala libs usadas pelo código Python
RUN pip install --no-cache-dir pyzmq msgpack

# Comando padrão só de placeholder.
# Cada serviço (server, client, ref) define o seu próprio "command" no docker-compose.
CMD ["python", "-c", "print('Imagem base para serviços Python (server/client/ref)')"]

