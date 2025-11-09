# 🚀 Sistema Distribuído de Mensageria com ZeroMQ, Docker e Multi-Linguagem

Este projeto implementa um **sistema distribuído de mensageria** completo, utilizando o padrão **ZeroMQ** para comunicação entre processos, com múltiplas linguagens integradas (**Python**, **Node.js**, **Go**) e **containers Docker**.

O objetivo é demonstrar conceitos de **comunicação distribuída**, **consistência**, **replicação de dados** e **sincronização de relógios** em uma arquitetura modular e escalável.

---

## 📦 Visão Geral

O sistema combina dois padrões clássicos de mensageria:

- **REQ/REP (Request-Reply)** → para comunicação síncrona entre clientes e servidores, mediada pelo *broker*.
- **PUB/SUB (Publish-Subscribe)** → para transmissão assíncrona de mensagens e eventos, mediada pelo *proxy*.

Com o avanço das partes, foram adicionadas camadas de:
- **Serialização binária (MessagePack)**,
- **Relógios lógicos e físicos (Lamport e Berkeley)**,
- **Replicação de dados entre servidores**.

---

## 🧩 Estrutura de Diretórios

```
.
├── src/
│   ├── broker/       # Broker (Node.js)
│   ├── proxy_go/     # Proxy (Go)
│   ├── server/       # Servidores (Python)
│   ├── client/       # Clientes automáticos (Python)
│   └── ref/          # Servidor de referência (Python)
├── Dockerfile
├── docker-compose.yml
└── package.json
```

---

## ⚙️ Componentes Principais

| Serviço | Linguagem | Função |
|----------|------------|--------|
| **Broker** | Node.js | Intermedia comunicação REQ/REP (clientes ⇄ servidores) |
| **Proxy** | Go | Intermedia comunicação PUB/SUB (servidores ⇄ clientes) |
| **Server** | Python | Processa requisições, publica mensagens e replica dados |
| **Client/Bot** | Python | Envia mensagens automáticas e assina canais |
| **Ref** | Python | Controla ranks, heartbeats e sincronização de relógios |

---

## 🧩 Funcionalidades por Etapa

### 🧠 Parte 1 – REQ/REP
Implementa a comunicação direta entre **clientes** e **servidores** via *broker* usando ZeroMQ.

- Broker atua como *ROUTER/DEALER*.
- Servidores processam requisições e enviam respostas.

---

### 📡 Parte 2 – PUB/SUB
Adiciona comunicação assíncrona via *proxy* (XSUB/XPUB).

- Clientes publicam mensagens em canais e enviam mensagens diretas a outros usuários.
- Servidor persiste dados em disco (`messages.jsonl` e `publications.jsonl`).
- Cliente automático envia mensagens de teste em loop.

---

### 🧩 Parte 3 – MessagePack
Substitui o formato JSON por **MessagePack**, otimizando o tráfego entre os containers.

- Transmissão binária entre clientes, servidores e broker.
- Redução de tamanho das mensagens e maior compatibilidade entre linguagens.

---

### ⏱️ Parte 4 – Relógios
Implementa **relógios lógicos (Lamport)** e **sincronização física (Berkeley)**.

- Cada processo mantém um contador lógico incrementado a cada envio.
- O servidor de referência (`ref`) fornece **rank**, **lista de servidores** e **heartbeat**.
- Sincronização periódica entre servidores coordenados.

---

### 🔁 Parte 5 – Consistência e Replicação
Garante que todos os servidores possuam os mesmos dados, mesmo em caso de falha.

- Cada servidor publica todas as operações no tópico interno `replica`.
- Todos os servidores escutam o tópico `replica` e atualizam seus arquivos locais.
- Campo `origin` evita replicação duplicada.
- Resultado: **consistência eventual** entre servidores.

---

## 💾 Persistência

Os servidores mantêm logs locais para garantir histórico e recuperação futura:

| Arquivo | Descrição |
|----------|------------|
| `publications.jsonl` | Publicações em canais |
| `messages.jsonl` | Mensagens diretas entre usuários |
| `registry.json` | Lista de canais e usuários registrados |
| `ref_servers.json` | Lista de servidores e ranks no `ref` |

---

## 🐳 Docker Compose

Principais serviços definidos no `docker-compose.yml`:

```yaml
services:
  ref:        # Servidor de referência (rank, heartbeat)
  broker:     # Intermediário REQ/REP em Node.js
  proxy:      # Intermediário PUB/SUB em Go
  server:     # Servidor Python (3 réplicas, com replicação)
  client_auto:# Cliente automático (2 réplicas)
```

---

## ▶️ Como Executar o Projeto

### 1️⃣ Clonar o repositório
```bash
git clone https://github.com/SEU_USUARIO/proj-sistm-distribuidos.git
cd proj-sistm-distribuidos
```

### 2️⃣ Construir e iniciar os containers
```bash
docker compose up --build
```

### 3️⃣ Monitorar a execução
- Cada container exibirá seus logs no terminal.
- Servidores mostrarão:
  - Incrementos de **relógio lógico**.
  - Confirmações de **replicação de mensagens**.
  - Envio periódico de **heartbeat** ao `ref`.

### 4️⃣ Verificar persistência
Após alguns minutos de execução, todos os arquivos `.jsonl` dentro de `src/server/data` terão o mesmo conteúdo — confirmando a replicação entre servidores.

---

## 🔍 Tecnologias e Bibliotecas

| Componente | Linguagem | Bibliotecas principais |
|-------------|------------|------------------------|
| Broker | Node.js | `zeromq` |
| Proxy | Go | `go-zeromq/zmq4` |
| Server / Client / Ref | Python | `pyzmq`, `msgpack` |
| Infraestrutura | Docker | `docker-compose` |

---

## 📘 Conceitos Demonstrados

- Comunicação distribuída (REQ/REP e PUB/SUB)  
- Serialização binária com MessagePack  
- Relógios lógicos de Lamport  
- Sincronização de relógios físicos (Berkeley)  
- Replicação eventual de dados entre servidores  
- Multi-linguagem com interoperabilidade binária  
- Orquestração de containers com Docker  

---


