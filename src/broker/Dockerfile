# Broker em JavaScript (runtime Node.js)
FROM node:22-alpine

WORKDIR /app

# Copia tudo da pasta src (onde está o broker/main.js e package.json)
COPY . .

# Instala dependências definidas no package.json (zeromq etc.)
RUN npm install

# Roda o broker em JavaScript
CMD ["node", "broker/main.js"]
