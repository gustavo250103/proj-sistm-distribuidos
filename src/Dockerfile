# imagem oficial do Python com Alpine (leve)
FROM python:3.13.7-alpine3.21

# diretório de trabalho dentro do container
WORKDIR /app

# copia todo o projeto para dentro da imagem
COPY . .

# instala as libs usadas pelo Python (ZeroMQ + MessagePack)
RUN pip install pyzmq msgpack

# comando padrão (o docker-compose sobrescreve conforme o serviço)
CMD ["python", "main.py"]
