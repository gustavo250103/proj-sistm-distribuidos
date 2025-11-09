import zmq

ctx = zmq.Context()
router = ctx.socket(zmq.ROUTER); router.bind("tcp://*:5555")
dealer = ctx.socket(zmq.DEALER); dealer.bind("tcp://*:5556")

zmq.proxy(router, dealer)

router.close(); dealer.close(); ctx.term()
