# Copied and modified from https://github.com/ZKStats/MP-SPDZ/tree/demo_client/DevConDemo

from .client import Client, octetStream


def hex_to_int(hex):
    return int(hex, 16)

def reverse_bytes(integer):
    # Convert integer to bytes, assuming it is a 32-bit integer (4 bytes)
    byte_length = (integer.bit_length() + 7) // 8 or 1
    byte_representation = integer.to_bytes(byte_length, byteorder='big')

    # Reverse the byte order
    reversed_bytes = byte_representation[::-1]

    # Convert the reversed bytes back to an integer
    reversed_integer = int.from_bytes(reversed_bytes, byteorder='big')

    return reversed_integer


def run_data_sharing_client(
    party_hosts: list[str],
    port_base: int,
    certs_path: str,
    client_id: int,
    cert_file: str,
    key_file: str,
    input_value: int,
    nonce: str,
):
    client = Client(party_hosts, port_base, client_id, certs_path, cert_file, key_file)

    for socket in client.sockets:
        os = octetStream()
        os.store(0)
        os.Send(socket)

    client.send_private_inputs([input_value, reverse_bytes(hex_to_int(nonce))])
    print("finish sending private inputs")
    outputs = client.receive_outputs(1)
    print("!@# data_sharing_client.py outputs: ", outputs)
    commitment = outputs[0]
    print("!@# data_sharing_client.py commitment: ", hex(reverse_bytes(commitment)))


def run_computation_query_client(
    party_hosts: list[str],
    port_base: int,
    certs_path: str,
    client_id: int,
    cert_file: str,
    key_file: str,
    max_data_providers: int,
    computation_index: int,
):
    # client id should be assigned by our server
    client = Client(party_hosts, port_base, client_id, certs_path, cert_file, key_file)

    for socket in client.sockets:
        os = octetStream()
        # computationIndex is public, not need to be secret shared.
        os.store(computation_index)
        os.Send(socket)
    output_list = client.receive_outputs(1+max_data_providers)
    print('Computation index',computation_index, "is", output_list[0])
    for i in range(max_data_providers):
        print('commitment: ',i, 'is', hex(reverse_bytes(output_list[i+1])))
