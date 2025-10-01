import zmq

context = zmq.Context()

# Socket XPUB recebe mensagens de publishers
pub = context.socket(zmq.XPUB)
pub.bind("tcp://*:5558")

# Socket XSUB recebe inscrições de subscribers
sub = context.socket(zmq.XSUB)
sub.bind("tcp://*:5557")

# Conecta XPUB <-> XSUB
zmq.proxy(pub, sub)

pub.close()
sub.close()
context.close()
