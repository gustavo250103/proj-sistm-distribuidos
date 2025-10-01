# 🚀 Sistema de Mensageria com ZeroMQ + Docker

Este projeto demonstra uma arquitetura **distribuída de mensageria** utilizando [ZeroMQ](https://zeromq.org/) e **containers Docker**.  
Ele combina dois padrões clássicos de comunicação:

- **REQ/REP (Request-Reply)** → para chamadas síncronas entre clientes e servidores.  
- **PUB/SUB (Publish-Subscribe)** → para notificações em tempo real (broadcast de eventos).  

---

## 📂 Estrutura do Projeto

.
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── main.py (com diferentes versões para client, server, broker e proxy)


- **Dockerfile** → define a imagem base Python + ZeroMQ.  
- **docker-compose.yml** → orquestra os 4 serviços: `broker`, `proxy`, `server`, `client`.  
- **main.py** → contém o código, que muda conforme o papel do container.  

---

## 🏗️ Arquitetura

A comunicação acontece em **dois fluxos distintos**:

   CLIENTES ------------------> BROKER ------------------> SERVIDORES
      |                           |                          |
      |                           v                          |
      |<---------------------- respostas --------------------|

   SERVIDORES -----------------> PROXY ------------------> CLIENTES
   (publicam eventos)            (replica msgs)           (assinam eventos)


### 1. Request-Reply (REQ/REP)
- O **cliente** envia requisições (`REQ`) para o **broker**.  
- O **broker** roteia essas mensagens para um **servidor** (`REP`).  
- O servidor processa e devolve a resposta via broker → cliente.  

Fluxo:

CLIENT (REQ) ---> BROKER (ROUTER/DEALER) ---> SERVER (REP)
CLIENT (RESPOSTA) <------------------------------ SERVER

### 2. Publish-Subscribe (PUB/SUB)
- O **servidor** publica mensagens (`PUB`) no **proxy**.  
- O **proxy** replica e distribui mensagens para todos os **clientes** que assinam (`SUB`).  

Fluxo:

SERVER (PUB) ---> PROXY (XSUB/XPUB) ---> CLIENT (SUB)


Assim, temos **RPC + Broadcast de eventos** na mesma aplicação.

---

## ⚙️ Serviços do Docker Compose

```yaml
services:
  broker:   # Intermediário REQ/REP
  proxy:    # Intermediário PUB/SUB
  server:   # Responde REQ e publica eventos
  client:   # Faz REQ e assina SUB



## ▶️ Como Rodar

1. **Abra o terminal** na pasta onde estão `docker-compose.yml` e `Dockerfile`.

2. **Construa e suba todos os serviços**:
   ```bash
   docker-compose up --build
