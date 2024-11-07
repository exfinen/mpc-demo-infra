# Copied and modified from https://github.com/ZKStats/MP-SPDZ/tree/demo_client/DevConDemo
import asyncio
import aiohttp
import random
from pathlib import Path
import secrets

from .client import Client, octetStream
from ..constants import MAX_CLIENT_ID, MAX_DATA_PROVIDERS, CLIENT_TIMEOUT

EMPTY_COMMITMENT = '0'

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
    client = Client(party_hosts, port_base, client_id, certs_path, cert_file, key_file, CLIENT_TIMEOUT)

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
    client = Client(party_hosts, port_base, client_id, certs_path, cert_file, key_file, CLIENT_TIMEOUT)

    for socket in client.sockets:
        os = octetStream()
        # computationIndex is public, not need to be secret shared.
        os.store(computation_index)
        os.Send(socket)
    # If computation returns more than one value, need to change the following line.
    output_list = client.receive_outputs(1 + max_data_providers)
    # TODO: Need to change the following line if computation returns more than one value.
    results = output_list[0:1]
    print('Computation index',computation_index, "is", results)

    # return {index -> commitment}
    data_commitments = [hex(reverse_bytes(i))[2:] for i in output_list[1:]]
    commitments = {
        # index is 1-based, commitment is hex string without 0x prefix
        index + 1: commitment for index, commitment in enumerate(data_commitments) if commitment != EMPTY_COMMITMENT
    }
    return results, commitments


async def generate_client_cert(max_client_id: int, certs_path: Path) -> tuple[int, Path, Path]:
    client_id = random.randint(0, max_client_id - 1)
    # openssl req -newkey rsa -nodes -x509 -out Player-Data/C$i.pem -keyout Player-Data/C$i.key -subj "/CN=C$i"
    cert_path = certs_path / f"C{client_id}.pem"
    key_path = certs_path / f"C{client_id}.key"
    process = await asyncio.create_subprocess_exec(
        "openssl", "req", "-newkey", "rsa", "-nodes", "-x509", "-out", str(cert_path), "-keyout", str(key_path), "-subj", f"/CN=C{client_id}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await process.wait()
    if process.returncode != 0:
        raise Exception(f"Failed to generate client cert for {client_id}")
    return client_id, cert_path, key_path


async def validate_computation_key(coordination_server_url: str, access_key: str, computation_key: str) -> None:
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{coordination_server_url}/validate_computation_key", json={
            "access_key": access_key,
            "computation_key": computation_key,
        }) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Failed to validate computation key {computation_key}. Response: {response.status} {response.reason}")
            data = await response.json()
            return data["is_valid"]


async def mark_queue_computation_to_be_finished(coordination_server_url: str, access_key: str, computation_key: str) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{coordination_server_url}/finish_computation", json={
            "access_key": access_key,
            "computation_key": computation_key,
        }) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Failed to finish computation with {computation_key}. Response: {response.status} {response.reason}")
            data = await response.json()
            return data["is_finished"]


async def share_data(
    all_certs_path: Path,
    coordination_server_url: str,
    computation_party_hosts: list[str],
    voucher_code: str,
    tlsn_proof: str,
    value: int,
    nonce: str,
    computation_key: str,
):
    if await validate_computation_key(coordination_server_url, voucher_code, computation_key) == False:
        raise Exception(f"Computation key is invalid")

    client_id, cert_path, key_path = await generate_client_cert(MAX_CLIENT_ID, all_certs_path)
    with open(cert_path, "r") as cert_file:
        cert_file_content = cert_file.read()
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{coordination_server_url}/share_data", json={
            "voucher_code": voucher_code,
            "tlsn_proof": tlsn_proof,
            "client_cert_file": cert_file_content,
            "client_id": client_id,
            "computation_key": computation_key,
        }) as response:
            await mark_queue_computation_to_be_finished(coordination_server_url, voucher_code, computation_key)

            if response.status != 200:
                json = await response.json()
                raise Exception(f"{json['detail']}")
            data = await response.json()
            client_port_base = data["client_port_base"]

    # Wait until all computation parties started their MPC servers.
    print(f"!@# Running data sharing client for {voucher_code=}, {client_port_base=}, {client_id=}, {cert_path=}, {key_path=}, {value=}, {nonce=}")
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            run_data_sharing_client,
            computation_party_hosts,
            client_port_base,
            str(all_certs_path),
            client_id,
            str(cert_path),
            str(key_path),
            value,
            nonce
        )
        return result
    finally:
        await mark_queue_computation_to_be_finished(coordination_server_url, voucher_code, computation_key)


async def query_computation_from_data_consumer_api(
    all_certs_path: Path,
    coordination_server_url: str,
    computation_party_hosts: list[str],
    access_key: str,
    computation_index: int,
):
    access_key = secrets.token_urlsafe(16)
    await add_user_to_queue(access_key)
    computation_key = await poll_queue_until_ready(access_key)

    return await query_computation(
        all_certs_path,
        coordination_server_url,
        computation_party_hosts,
        access_key,
        computation_index,
        computation_key,
    )


async def query_computation(
    all_certs_path: Path,
    coordination_server_url: str,
    computation_party_hosts: list[str],
    access_key: str,
    computation_index: int,
    computation_key: str,
):
    if await validate_computation_key(coordination_server_url, access_key, computation_key) == False:
        raise Exception(f"Error: Computation key is invalid")

    client_id, cert_path, key_path = await generate_client_cert(MAX_CLIENT_ID, all_certs_path)
    with open(cert_path, "r") as cert_file:
        cert_file_content = cert_file.read()
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{coordination_server_url}/query_computation", json={
            "client_id": client_id,
            "client_cert_file": cert_file_content,
            "computation_key": computation_key,
            "access_key": access_key,
        }) as response:
            assert response.status == 200
            data = await response.json()
            client_port_base = data["client_port_base"]

    try:
        results, commitments = await asyncio.get_event_loop().run_in_executor(
            None,
            run_computation_query_client,
            computation_party_hosts,
            client_port_base,
            str(all_certs_path),
            client_id,
            str(cert_path),
            str(key_path),
            MAX_DATA_PROVIDERS,
            computation_index
        )
        # TODO: Verify commitments with tlsn proofs
        return results
    finally:
        await mark_queue_computation_to_be_finished(coordination_server_url, access_key, computation_key)


async def query_computation_from_data_consumer_api(
    all_certs_path: Path,
    coordination_server_url: str,
    computation_party_hosts: list[str],
    computation_index: int,
):
    print("called")
    access_key = secrets.token_urlsafe(16)
    await add_user_to_queue(access_key)
    print("added user to the queue")
    computation_key = await poll_queue_until_ready(access_key)
    print(f"calling query_computation: {access_key}, {computation_key}")

    return await query_computation(
        all_certs_path,
        coordination_server_url,
        computation_party_hosts,
        computation_index,
        computation_key,
    )


async def fetch_parties_certs(
    party_web_protocol: str,  # http or https
    certs_path: Path,
    party_hosts: list[str],
    party_ports: list[int],
):
    async def get_party_cert(session, host: str, port: int, party_id: int):
        async with session.get(f"{party_web_protocol}://{host}:{port}/get_party_cert") as response:
            assert response.status == 200
            data = await response.json()
            assert data["party_id"] == party_id
            return data["cert_file"]
    # Get party certs concurrently
    async with aiohttp.ClientSession() as session:
        party_certs = await asyncio.gather(
            *[get_party_cert(session, host, port, party_id) for party_id, (host, port) in enumerate(zip(party_hosts, party_ports))]
        )
    certs_path.mkdir(parents=True, exist_ok=True)
    # Write party certs to files
    for party_id, cert in enumerate(party_certs):
        (certs_path / f"P{party_id}.pem").write_text(cert)
