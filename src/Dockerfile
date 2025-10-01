# img oficial do Python
FROM python:3.13.7-alpine3.21

# Define diretório de trabalho dentro do container
WORKDIR /app

RUN pip install pyzmq

# Comando padrão (pode ser sobrescrito pelo docker-compose)
CMD ["python", "main.py"]
