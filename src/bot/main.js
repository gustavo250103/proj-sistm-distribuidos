"use strict";

const zmq = require("zeromq");
const { randomUUID } = require("node:crypto");

const config = {
  username: process.env.BOT_USERNAME || `bot-${randomUUID().slice(0, 8)}`,
  brokerHost: process.env.BROKER_HOST || "broker",
  brokerPort: process.env.BROKER_PORT || "5555",
  proxyHost: process.env.PROXY_HOST || "proxy",
  proxyPort: process.env.PROXY_PORT || "5558",
  channel: process.env.BOT_CHANNEL || "general",
  intervalMs: Number(process.env.BOT_INTERVAL_MS || 8000),
  dmTarget: process.env.BOT_DM_TARGET
};

const reqSocket = new zmq.Request();
const subSocket = new zmq.Subscriber();

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const now = () => Math.floor(Date.now() / 1000);

async function connectSockets() {
  const reqEndpoint = `tcp://${config.brokerHost}:${config.brokerPort}`;
  const subEndpoint = `tcp://${config.proxyHost}:${config.proxyPort}`;

  await reqSocket.connect(reqEndpoint);
  await subSocket.connect(subEndpoint);
  subSocket.subscribe(config.channel);
  subSocket.subscribe(config.username);

  console.log(
    `[${config.username}] Conectado ao broker (${reqEndpoint}) e proxy (${subEndpoint}).`
  );
}

async function sendRequest(service, data = {}) {
  const payload = {
    service,
    data: {
      ...data,
      timestamp: data.timestamp ?? now()
    }
  };

  try {
    await reqSocket.send(JSON.stringify(payload));
    const [reply] = await reqSocket.receive();
    const parsed = JSON.parse(reply.toString());
    return parsed.data || {};
  } catch (error) {
    console.error(
      `[${config.username}] Falha ao enviar '${service}': ${error.message}`
    );
    await sleep(1500);
    return { status: "erro", description: error.message };
  }
}

async function loginUntilSuccess() {
  while (true) {
    const response = await sendRequest("login", { user: config.username });
    if (response.status === "sucesso") {
      console.log(`[${config.username}] Login realizado com sucesso.`);
      return;
    }

    console.warn(
      `[${config.username}] Login falhou (${response.description || response.status}). Tentando novamente...`
    );
    await sleep(2000);
  }
}

async function ensureChannel(channelName) {
  const response = await sendRequest("channel", { channel: channelName });
  if (response.status === "sucesso") {
    console.log(`[${config.username}] Canal '${channelName}' criado.`);
  } else {
    console.log(
      `[${config.username}] Canal '${channelName}' indisponível (${response.description || response.status}).`
    );
  }
}

function startReceiver() {
  (async () => {
    for await (const [topicBuf, messageBuf] of subSocket) {
      const topic = topicBuf.toString();
      try {
        const payload = JSON.parse(messageBuf.toString());
        const time = new Date(payload.timestamp * 1000).toISOString();
        const target = payload.type === "private" ? `privado:${payload.from}` : `canal:${topic}`;
        console.log(
          `[${config.username}] <- (${target} @ ${time}) ${payload.message}`
        );
      } catch (error) {
        console.error(
          `[${config.username}] Erro ao processar mensagem do tópico '${topic}': ${error.message}`
        );
      }
    }
  })().catch((error) => {
    console.error(`[${config.username}] Receiver encerrado: ${error.message}`);
    process.exit(1);
  });
}

async function publishLoop() {
  let counter = 1;
  while (true) {
    const channelMessage = `auto-msg ${counter} de ${config.username}`;
    const response = await sendRequest("publish", {
      user: config.username,
      channel: config.channel,
      message: channelMessage
    });

    if (response.status === "OK") {
      console.log(
        `[${config.username}] -> (canal:${config.channel}) ${channelMessage}`
      );
    } else {
      console.warn(
        `[${config.username}] Falha ao publicar: ${response.description || response.status}`
      );
    }

    if (config.dmTarget) {
      const dmResponse = await sendRequest("message", {
        src: config.username,
        dst: config.dmTarget,
        message: `ping de ${config.username}`
      });

      if (dmResponse.status !== "OK") {
        console.warn(
          `[${config.username}] Falha ao enviar DM para ${config.dmTarget}: ${dmResponse.description || dmResponse.status}`
        );
      }
    }

    counter += 1;
    const jitter = Math.floor(Math.random() * 1500);
    await sleep(config.intervalMs + jitter);
  }
}

function setupShutdownHooks() {
  const shutdown = async (signal) => {
    console.log(`[${config.username}] Recebido sinal ${signal}. Encerrando...`);
    try {
      await subSocket.close();
      await reqSocket.close();
    } catch (error) {
      console.error(`[${config.username}] Erro ao encerrar sockets: ${error.message}`);
    } finally {
      process.exit(0);
    }
  };

  ["SIGINT", "SIGTERM"].forEach((signal) => {
    process.on(signal, () => {
      shutdown(signal).catch((error) => {
        console.error(`[${config.username}] Erro no shutdown: ${error.message}`);
        process.exit(1);
      });
    });
  });
}

async function main() {
  setupShutdownHooks();
  await connectSockets();
  startReceiver();
  await loginUntilSuccess();
  await ensureChannel(config.channel);
  await publishLoop();
}

main().catch((error) => {
  console.error(`[${config.username}] Erro fatal: ${error.message}`);
  process.exit(1);
});
