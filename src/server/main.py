import zmq

context = zmq.Context()

# Servidor REP -> responde a pedidos recebidos via broker
rep_socket = context.socket(zmq.REP)
rep_socket.connect("tcp://broker:5556")

# Publisher -> envia mensagens para o proxy
pub_socket = context.socket(zmq.PUB)
pub_socket.connect("tcp://proxy:5557")
