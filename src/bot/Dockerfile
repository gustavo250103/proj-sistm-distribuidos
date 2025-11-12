# Use uma imagem oficial do Node.js
FROM node:20-alpine

# Defina o diretório de trabalho
WORKDIR /app

# Copie os arquivos de definição de pacotes e instale as dependências
COPY package*.json ./
RUN npm cache clean --force && npm install

# Copie o código-fonte do bot
COPY . .

# Comando para executar o bot
CMD ["node", "main.js"]
