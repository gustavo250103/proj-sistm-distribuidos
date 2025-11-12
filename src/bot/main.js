import zmq from "zeromq";
import { randomBytes } from "crypto";
import { encode, decode } from "@msgpack/msgpack";

const REQ_ADDR = process.env.BROKER_ADDR || "tcp://broker:5555";
const username = process.env.BOT_NAME || `bot-${randomBytes(4).toString("hex")}`;
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function sendRequest(sock, service, data = {}) {
  const payload = {
    service,
    data: {
      ...data,
      timestamp: data.timestamp ?? Math.floor(Date.now() / 1000),
    },
  };
  await sock.send(encode(payload));
  const [replyRaw] = await sock.receive();
  const reply = decode(replyRaw);
  return reply.data || {};
}

async function run() {
  const req = new zmq.Request();
  await req.connect(REQ_ADDR);
  console.log(`[bot] ${username} conectado em ${REQ_ADDR}`);

  try {
    await sendRequest(req, "login", { user: username });
    console.log(`[bot] ${username} autenticado.`);
  } catch (err) {
    console.error("[bot] erro no login:", err);
    process.exit(1);
  }

  while (true) {
    try {
      const channelsData = await sendRequest(req, "channels", {});
      const channels = channelsData.users || channelsData.channels || [];
      let targetChannel = "geral";
      if (channels.length > 0) {
        targetChannel = channels[Math.floor(Math.random() * channels.length)];
      } else {
        await sendRequest(req, "channel", { channel: targetChannel });
        console.log(`[bot] criou canal padrão '${targetChannel}'`);
      }

      console.log(`[bot] ${username} publicando no canal '${targetChannel}'`);

      for (let i = 0; i < 10; i++) {
        await sendRequest(req, "publish", {
          user: username,
          channel: targetChannel,
          message: `Mensagem ${i} de ${username}`,
        });
        await delay(100);
      }

      console.log("[bot] publicações concluídas, aguardando 5s");
      await delay(5000);
    } catch (err) {
      console.error("[bot] erro no loop principal:", err);
      await delay(10000);
    }
  }
}

run().catch((err) => {
  console.error("[bot] erro fatal:", err);
  process.exit(1);
});

process.on("SIGINT", () => {
  console.log("[bot] encerrando...");
  process.exit(0);
});
