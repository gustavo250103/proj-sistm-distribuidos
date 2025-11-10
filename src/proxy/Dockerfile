# Proxy em Go
FROM golang:1.23-alpine

WORKDIR /app

# Copia o projeto
COPY . .

# Vai para a pasta do proxy em Go
WORKDIR /app/proxy_go

# Compila o binário
RUN go build -o proxy .

# Roda o binário do proxy
CMD ["./proxy"]
