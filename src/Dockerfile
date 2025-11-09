# imagem oficial do Python com Alpine (leve)
FROM python:3.13.7-alpine3.21

# pasta onde o código vai rodar dentro do container
WORKDIR /app

# instala as libs usadas pelo projeto (ZeroMQ e MessagePack)
RUN pip install pyzmq msgpack

# comando padrão (o docker-compose troca isso para cada serviço)
CMD ["python", "main.py"]
