import zmq

context = zmq.Context()

# Roteador para receber mensagens de clientes REQ
client_socket = context.socket(zmq.ROUTER)
client_socket.bind("tcp://*:5555")

# Dealer para repassar mensagens a servidores REP
server_socket = context.socket(zmq.DEALER)
server_socket.bind("tcp://*:5556")

# Cria um proxy interno que conecta ROUTER <-> DEALER
zmq.proxy(client_socket, server_socket)

# Fecha recursos (nunca deve ser alcançado, mas por segurança)
client_socket.close()
server_socket.close()
context.term()
