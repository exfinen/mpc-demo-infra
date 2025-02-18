# Copied and modified from https://github.com/ZKStats/MP-SPDZ/tree/demo_client/DevConDemo
import asyncio
import aiohttp
import random
from pathlib import Path
import secrets
import logging
import subprocess

from .client import Client, octetStream
from ..constants import MAX_CLIENT_ID, MAX_DATA_PROVIDERS, CLIENT_TIMEOUT
from mpc_demo_infra.coordination_server.user_queue import AddResult

logger = logging.getLogger(__name__)

EMPTY_COMMITMENT = '0'
BINANCE_DECIMAL_PRECISION = 2
BINANCE_DECIMAL_SCALE = 10**BINANCE_DECIMAL_PRECISION

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
    max_client_wait: int,
):
    logger.info(f"Setting up data sharing client with {party_hosts=}, {port_base=}...")
    client = Client(party_hosts, port_base, client_id, certs_path, cert_file, key_file, CLIENT_TIMEOUT, max_client_wait)
    logger.info(f"Created Client instance")

    for socket in client.sockets:
        os = octetStream()
        os.store(0)
        os.Send(socket)

    logger.info("Sending private inputs to computation party servers ...")
    client.send_private_inputs([input_value, reverse_bytes(hex_to_int(nonce))])
    logger.info("Finished sending private inputs")
    outputs = client.receive_outputs(1)
    logger.info(f"!@# data_sharing_client.py outputs: {outputs}")
    commitment = outputs[0]
    logger.info(f"!@# data_sharing_client.py commitment: {hex(reverse_bytes(commitment))}")


from dataclasses import dataclass

@dataclass(frozen=True)
class StatsResults:
    num_data_providers: int
    max: float
    mean: float
    median: float
    gini_coefficient: float


def safe_div(a, b):
    if b == 0:
        return 0
    else:
        return a / b


def run_computation_query_client(
    party_hosts: list[str],
    port_base: int,
    certs_path: str,
    client_id: int,
    cert_file: str,
    key_file: str,
    max_data_providers: int,
    max_client_wait: int,
):
    # client id should be assigned by our server
    client = Client(party_hosts, port_base, client_id, certs_path, cert_file, key_file, CLIENT_TIMEOUT, max_client_wait)

    for socket in client.sockets:
        os = octetStream()
        # computationIndex is public, not need to be secret shared.
        os.store(0)
        os.Send(socket)
    # If computation returns more than one value, need to change the following line.
    output_list = client.receive_outputs(5 + max_data_providers)
    logger.info(f"Stats of Data: {output_list}")
    num_data_providers = int(output_list[0])

    results = StatsResults(
        num_data_providers = num_data_providers,
        max = safe_div(output_list[1], 10 * BINANCE_DECIMAL_SCALE),
        mean = safe_div(output_list[2], num_data_providers * 10 * BINANCE_DECIMAL_SCALE),
        median = safe_div(output_list[3], 10 * BINANCE_DECIMAL_SCALE),
        gini_coefficient = safe_div(output_list[4], num_data_providers * output_list[2]) - 1,
    )
    logger.info(f"Number of data providers: {results.num_data_providers}")
    logger.info(f"Max: {results.max}")
    logger.info(f"Mean: {results.mean}")
    logger.info(f"Median: {results.median}")
    logger.info(f"Gini Coefficient: {results.gini_coefficient}")

    # return {index -> commitment}
    data_commitments = [hex(reverse_bytes(i))[2:] for i in output_list[5:]]
    commitments = {
        # index is 1-based, commitment is hex string without 0x prefix
        index + 1: commitment for index, commitment in enumerate(data_commitments) if commitment != EMPTY_COMMITMENT
    }
    return results, commitments


async def generate_client_cert(max_client_id: int, certs_path: Path, client_id: int = None) -> tuple[int, Path, Path]:
    if client_id is None:
        # currently the number of simultaneously executing computations is limited to 1
        # and the client_id is fixed to 0 unless overridden
        client_id = 0

    # openssl req -newkey rsa -nodes -x509 -out Player-Data/C$i.pem -keyout Player-Data/C$i.key -subj "/CN=C$i"
    cert_path = certs_path / f"C{client_id}.pem"
    key_path = certs_path / f"C{client_id}.key"
    certs_path.mkdir(parents=True, exist_ok=True)
    process = await asyncio.create_subprocess_exec(
        "openssl", "req", "-newkey", "rsa", "-nodes", "-x509", "-out", str(cert_path), "-keyout", str(key_path), "-subj", f"/CN=C{client_id}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    await process.wait()
    if process.returncode != 0:
        raise Exception(f"Failed to generate client cert for {client_id}")

    subprocess.run(
        f"c_rehash {certs_path}",
        check=True,
        shell=True,
    )
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
        logger.info(f"Marking computation to be finished with {computation_key=}...")
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
    eth_address: str,
    tlsn_proof: str,
    value: float,
    nonce: str,
    access_key: str,
    computation_key: str,
    client_id: int,
    max_client_wait: int,
):
    if await validate_computation_key(coordination_server_url, access_key, computation_key) == False:
        raise Exception(f"Computation key is invalid")
    else:
        logger.info(f"Validated computation key: {computation_key}")

    client_id, cert_path, key_path = await generate_client_cert(MAX_CLIENT_ID, all_certs_path, client_id)
    with open(cert_path, "r") as cert_file:
        cert_file_content = cert_file.read()

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{coordination_server_url}/share_data", json={
        "eth_address": eth_address,
        "tlsn_proof": tlsn_proof,
        "client_cert_file": cert_file_content,
        "client_id": client_id,
        "access_key": access_key,
        "computation_key": computation_key,
        }) as response:
            if response.status != 200:
                json = await response.json()
                raise Exception(f"{json['detail']}")
            data = await response.json()
            client_port_base = data["client_port_base"]

    # Wait until all computation parties started their MPC servers.
    logger.info(f"!@# Running data sharing client for {eth_address=}, {client_port_base=}, {client_id=}, {cert_path=}, {key_path=}, {value=}, {nonce=}")

    result = await asyncio.get_event_loop().run_in_executor(
        None,
        run_data_sharing_client,
        computation_party_hosts,
        client_port_base,
        str(all_certs_path),
        client_id,
        str(cert_path),
        str(key_path),
        int(value*10*BINANCE_DECIMAL_SCALE),
        nonce,
        max_client_wait,
    )
    return result


async def add_user_to_queue(coordination_server_url: str, access_key: str, poll_duration: int, use_print: bool = False) -> None:
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{coordination_server_url}/add_user_to_queue", json={
                "access_key": access_key,
            }) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["result"] == AddResult.QUEUE_IS_FULL:
                        if use_print:
                            print(f"The queue is currently full. Please wait for your turn.", end='\r', flush=True)
                        else:
                            logger.warn(f"The queue is currently full. Please wait for your turn.")
                    else:
                        return
        await asyncio.sleep(poll_duration)


async def add_priority_user_to_queue(coordination_server_url: str, access_key: str, poll_duration: int, use_print: bool = False) -> None:
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{coordination_server_url}/add_priority_user_to_queue", json={
                "access_key": access_key,
            }) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["result"] == AddResult.QUEUE_IS_FULL:
                        if use_print:
                            print(f"The queue is currently full. Please wait for your turn.", end='\r', flush=True)
                        else:
                            logger.warn(f"The queue is currently full. Please wait for your turn.")
                    else:
                        return
        await asyncio.sleep(poll_duration)


async def poll_queue_until_ready(coordination_server_url: str, access_key: str, poll_duration: int, use_print: bool = False) -> str:
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{coordination_server_url}/get_position", json={
                "access_key": access_key,
            }) as response:
                if response.status == 200:
                    data = await response.json()
                    position = data["position"]
                    if position is None:
                        if use_print:
                            print("| The queue is currently full. Please wait for your turn.", end='\r', flush=True)
                        else:
                            logger.warn("| The queue is currently full. Please wait for your turn.")
                    else:
                        if position == 0:
                            if use_print:
                                print(f"| Computation servers are ready. Your requested computation will begin shortly.", end='\r', flush=True)
                            else:
                                logger.info("| Computation servers are ready. Your requested computation will begin shortly.")
                            return data["computation_key"]
                        else:
                            if use_print:
                                print(f"| You're #{position} in line", end='\r', flush=True)
                            else:
                                logger.info(f"| You're #{position} in line")
                else:
                    if use_print:
                        print(f"| Server error. Status {response.status}", end='\r', flush=True)
                    else:
                        logger.error(f"| Server error. Status {response.status}")
        await asyncio.sleep(poll_duration)


async def query_computation_from_data_consumer_api(
    all_certs_path: Path,
    coordination_server_url: str,
    computation_party_hosts: list[str],
    poll_duration: int,
    party_web_protocol: str,
    certs_path: Path,
    party_hosts: list[str],
    party_ports: list[int],
    max_client_wait: int,
):
    access_key = secrets.token_urlsafe(16)
    await add_priority_user_to_queue(coordination_server_url, access_key, poll_duration)
    computation_key = await poll_queue_until_ready(coordination_server_url, access_key, poll_duration)
    try:
        logger.info("Fetching parties certs")
        await fetch_parties_certs(
            party_web_protocol=party_web_protocol,
            certs_path=certs_path,
            party_hosts=party_hosts,
            party_ports=party_ports,
        )
        logger.info("Parties certs fetched")

        return await query_computation(
            all_certs_path,
            coordination_server_url,
            computation_party_hosts,
            access_key,
            computation_key,
            max_client_wait,
        )
    finally:
        logger.info("Query computation finished")
        await mark_queue_computation_to_be_finished(coordination_server_url, access_key, computation_key)


async def query_computation(
    all_certs_path: Path,
    coordination_server_url: str,
    computation_party_hosts: list[str],
    access_key: str,
    computation_key: str,
    max_client_wait: int,
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
            if response.status != 200:
                raise Exception(f"Failed to query computation: {response.status=}, {await response.text()=}")
            data = await response.json()
            client_port_base = data["client_port_base"]
    logger.info(f"!@# Running computation query client for {access_key=}, {computation_key=}, {client_port_base=}")
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
        max_client_wait,
    )
    return results



async def fetch_parties_certs(
    party_web_protocol: str,  # http or https
    certs_path: Path,
    party_hosts: list[str],
    party_ports: list[int],
):
    async def get_party_cert(session, host: str, port: int, party_id: int):
        url = f"{party_web_protocol}://{host}:{port}/get_party_cert"
        logger.info(f"Fetching party cert with {url}...")
        async with session.get(url) as response:
            if response.status != 200:
                raise Exception(f"Failed to get party cert: {response.status=}, {await response.text()=}")
            data = await response.json()
            if data["party_id"] != party_id:
                raise Exception(f'{data["party_id"]=}, {party_id=}')
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


def locate_binance_verifier(binance_verifier_locations):
    binance_verifier_dir = None
    for (dir, exec_cmd) in binance_verifier_locations:
        if (dir / "binance_verifier").exists():
            binance_verifier_dir = dir
            binance_verifier_exec_cmd = exec_cmd
            break
    if binance_verifier_dir is None:
        raise FileNotFoundError(f"binance_verifier not found in {binance_verifier_locations}. Please build it in TLSN repo.")
    logger.info(f"Found binance_verifier in {binance_verifier_dir}")
    return binance_verifier_dir, binance_verifier_exec_cmd


