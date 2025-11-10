# 🚀 Sistema Distribuído de Mensageria com ZeroMQ, Docker e Multi-Linguagem

Este projeto implementa um **sistema distribuído de mensageria** completo, utilizando o padrão **ZeroMQ** para comunicação entre processos, com múltiplas linguagens integradas (**Python**, **Node.js**, **Go**) e **containers Docker**.

O objetivo é demonstrar, de forma prática, conceitos de **comunicação distribuída**, **consistência**, **replicação de dados** e **sincronização de relógios** em uma arquitetura modular, escalável e tolerante a falhas.

---

## 📦 Visão Geral

O sistema combina dois padrões clássicos de mensageria:

- **REQ/REP (Request-Reply)** → para comunicação síncrona entre **clientes** e **servidores**, mediada pelo **broker**.
- **PUB/SUB (Publish-Subscribe)** → para disseminação assíncrona de eventos e mensagens em **canais**, mediada pelo **proxy**.

Com o avanço das etapas, foram adicionadas:
- **Serialização binária (MessagePack)**  
- **Relógios lógicos e físicos (Lamport e Berkeley)**  
- **Replicação e consistência entre servidores**

---

## 🧩 Estrutura de Diretórios

```
.
├── src/
│   ├── broker/       # Broker (Node.js)
│   ├── proxy_go/     # Proxy (Go)
│   ├── server/       # Servidores (Python)
│   ├── client/       # Clientes e bots (Python)
│   └── ref/          # Servidor de referência (Python)
├── Dockerfile
├── docker-compose.yml
└── package.json
```

---

## ⚙️ Componentes do Sistema

| Serviço | Linguagem | Função |
|----------|------------|--------|
| **Broker** | Node.js | Intermedia REQ/REP entre clientes e servidores |
| **Proxy** | Go | Intermedia PUB/SUB entre servidores e clientes |
| **Server** | Python | Processa requisições, publica mensagens, replica dados e sincroniza relógios |
| **Client/Bot** | Python | Envia mensagens automáticas e assina canais |
| **Ref** | Python | Controla ranks, heartbeats e sincronização de relógios físicos |

---

## 🧠 Funcionalidades por Etapa

### 🧩 Parte 1 – REQ/REP
Comunicação direta entre **clientes** e **servidores** via *broker*:
- Broker atua como **ROUTER/DEALER**.
- Servidores recebem requisições e devolvem respostas via ZeroMQ.

---

### 📡 Parte 2 – PUB/SUB
Camada de publicação e assinatura via *proxy*:
- Clientes e bots publicam em canais.
- Servidores armazenam publicações e mensagens em disco.
- Cada cliente automático envia mensagens periódicas de teste.

---

### ⚙️ Parte 3 – MessagePack
Troca de mensagens no formato **binário (MessagePack)**, reduzindo o tráfego e mantendo compatibilidade entre linguagens.

---

### ⏱️ Parte 4 – Relógios
Implementação de **relógios lógicos (Lamport)** e **sincronização física (Berkeley)**:
- Cada processo mantém um contador lógico.
- Servidor de referência (`ref`) fornece **rank**, **lista de servidores** e **heartbeat**.
- Eleição automática de coordenador (menor rank).
- Publicação de eventos no tópico `servers` ao mudar o coordenador.

---

### 🔁 Parte 5 – Consistência e Replicação
Garante que todos os servidores mantenham o mesmo histórico:
- Servidores publicam operações no tópico interno `replica`.
- Todos assinam o tópico e gravam as mensagens recebidas.
- O campo `origin` evita replicação em loop.
- Resultado: **consistência eventual** entre todos os nós.

---

## 💾 Persistência de Dados

Os servidores mantêm registros locais para garantir integridade e recuperação:

| Arquivo | Descrição |
|----------|------------|
| `publications.jsonl` | Mensagens publicadas em canais |
| `messages.jsonl` | Mensagens diretas entre usuários |
| `registry.json` | Usuários e canais cadastrados |
| `ref_servers.json` | Lista de servidores e ranks no processo `ref` |

---

## 🐳 Execução com Docker Compose

O sistema é totalmente containerizado.

### 📜 Serviços definidos no `docker-compose.yml`

```yaml
services:
  ref:          # Servidor de referência (rank, heartbeat, clock)
  broker:       # Intermediário REQ/REP em Node.js
  proxy:        # Intermediário PUB/SUB em Go
  server:       # Servidor Python (3 réplicas com replicação)
  client_auto:  # Clientes automáticos (2 bots)
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

> 💡 **Dica:** para limpar execuções antigas  
> `docker compose down -v --remove-orphans`

---

## 📺 O que Esperar nos Logs

- **Broker**  
  ```
  [broker] ROUTER on tcp://*:5555 | DEALER on tcp://*:5556
  ```
- **Proxy (Go)**  
  ```
  [proxy-go] XSUB on tcp://*:5557 | XPUB on tcp://*:5558
  ```
- **Ref (Servidor de referência)**  
  ```
  [ref] servidor de referência iniciado em tcp://*:6000
  ```
- **Server**  
  ```
  [server-001] rank obtido: 1
  [server-001] coordenador inicial: server-001
  [server-001] sincronizou clock com ref (time=..., clock=24)
  [server-002] novo coordenador eleito: server-001
  [server-003] recebeu aviso de novo coordenador: server-001
  [server-002] replicou registro de server-001 (publish)
  ```
- **Client/Bot**  
  ```
  [BOT] user4821 iniciado e enviando mensagens automáticas...
  [user4821] <- (#general) auto-msg 3 de user4821
  ```

---

## 🧠 Testes e Validações

1. **Replicação:**  
   Após alguns minutos, todos os servidores devem possuir arquivos `publications.jsonl` idênticos.
2. **Sincronização de relógio:**  
   Os clocks são atualizados a cada 10 mensagens.
3. **Eleição:**  
   O menor rank do `ref` se torna coordenador e avisa os demais via tópico `servers`.
4. **Heartbeat:**  
   Cada servidor envia batimentos regulares ao `ref`.

---

## 🧰 Tecnologias e Bibliotecas

| Componente | Linguagem | Bibliotecas |
|-------------|------------|-------------|
| Broker | Node.js | `zeromq` |
| Proxy | Go | `go-zeromq/zmq4` |
| Server / Client / Ref | Python | `pyzmq`, `msgpack` |
| Infraestrutura | Docker | `docker-compose`, `alpine`, `python:3.13` |

---

## 📘 Conceitos Demonstrados

- Comunicação distribuída (REQ/REP + PUB/SUB)
- Serialização binária com MessagePack
- Relógios de Lamport e sincronização de Berkeley
- Replicação eventual e consistência entre nós
- Eleição e coordenação de servidores
- Multi-linguagem integrada (Python, Node.js, Go)
- Orquestração completa com Docker

---

## 🧹 Encerrando

Para encerrar a execução:
```bash
docker compose down
```

Para remover volumes e logs persistentes:
```bash
docker compose down -v --remove-orphans
```

---

## ✅ Resultado Esperado

Ao final, você terá:
- Uma **rede distribuída** de containers interconectados via ZeroMQ.  
- Mensagens sendo publicadas, replicadas e persistidas entre múltiplos servidores.  
- Relógios lógicos e físicos sincronizados.  
- Coordenação e eleição automáticas de servidores.  

Um projeto completo de **Sistemas Distribuídos com Docker**, cobrindo **todas as 5 partes** do enunciado. 🚀
