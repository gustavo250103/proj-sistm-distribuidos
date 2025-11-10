// ROUTER (5555) <-> DEALER (5556)
import { Router, Dealer, Poller } from "zeromq"; // importa tipos de socket e poller

const ROUTER_ADDR = process.env.ROUTER_ADDR || "tcp://*:5555"; // endereço que recebe REQ dos clientes
const DEALER_ADDR = process.env.DEALER_ADDR || "tcp://*:5556"; // endereço que encaminha para o servidor

async function main() {
  const router = new Router();          // socket que fala com os clientes
  const dealer = new Dealer();          // socket que fala com o servidor

  await router.bind(ROUTER_ADDR);       // abre porta 5555
  await dealer.bind(DEALER_ADDR);       // abre porta 5556
  console.log(`[broker] ROUTER on ${ROUTER_ADDR} | DEALER on ${DEALER_ADDR}`);

  const poller = new Poller();          // objeto para esperar dados em vários sockets
  poller.add(router, "readable");       // avisa quando chegar algo do cliente
  poller.add(dealer, "readable");       // avisa quando chegar algo do servidor

  while (true) {
    const events = await poller.poll(); // espera qualquer lado ficar pronto
    for (const ev of events) {
      if (ev.socket === router && ev.events.readable) { // veio do cliente
        const frames = await router.receive();          // pega todas as partes da msg
        await dealer.send(frames);                      // repassa para o servidor
      }
      if (ev.socket === dealer && ev.events.readable) { // veio do servidor
        const frames = await dealer.receive();          // pega todas as partes
        await router.send(frames);                      // devolve para o cliente certo
      }
    }
  }
}

main().catch((e) => {                  // log de erro caso algo dê ruim
  console.error("[broker] error:", e);
  process.exit(1);                     // encerra o processo em erro
});
