// ROUTER (5555) <-> DEALER (5556)
import { Router, Dealer, Poller } from "zeromq";

const ROUTER_ADDR = process.env.ROUTER_ADDR || "tcp://*:5555"; // clientes REQ conectam
const DEALER_ADDR = process.env.DEALER_ADDR || "tcp://*:5556"; // servidores REP conectam

async function main() {
  const router = new Router();
  const dealer = new Dealer();

  await router.bind(ROUTER_ADDR);
  await dealer.bind(DEALER_ADDR);

  console.log(`[broker] ROUTER on ${ROUTER_ADDR} | DEALER on ${DEALER_ADDR}`);

  const poller = new Poller();
  poller.add(router, "readable");
  poller.add(dealer, "readable");

  while (true) {
    const events = await poller.poll();

    for (const ev of events) {
      if (ev.socket === router && ev.events.readable) {
        const frames = await router.receive(); // vem do cliente
        await dealer.send(frames);             // vai pro servidor
      }

      if (ev.socket === dealer && ev.events.readable) {
        const frames = await dealer.receive(); // vem do servidor
        await router.send(frames);             // vai pro cliente
      }
    }
  }
}

main().catch((err) => {
  console.error("[broker] error:", err);
  process.exit(1);
});
