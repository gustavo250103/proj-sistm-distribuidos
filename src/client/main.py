import zmq

req_address = "broker"
req_port = 5555

sub_address = "proxy"
sub_port = 5558

context = zmq.Context()

# Cliente REQ -> envia pedidos ao broker
req_socket = context.socket(zmq.REQ)
req_socket.connect(f"tcp://{req_address}:{req_port}")

# Cliente SUB -> escuta mensagens publicadas
sub_socket = context.socket(zmq.SUB)
sub_socket.connect(f"tcp://{sub_address}:{sub_port}")
sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")  # "" = assina tudo
