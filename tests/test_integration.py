import os
import requests
import random
import pytest
import asyncio
import aiohttp
from pathlib import Path

from mpc_demo_infra.coordination_server.routes import MAX_CLIENT_ID
from mpc_demo_infra.coordination_server.config import settings
from mpc_demo_infra.coordination_server.database import SessionLocal, Voucher
from mpc_demo_infra.client import run_data_sharing_client, run_computation_query_client

from .common import (
    TLSN_PROOF_1,
    value_1,
    data_commitment_hash_1,
    nonce_1,
    input_bytes_1,
    TLSN_PROOF_2,
    value_2,
    data_commitment_hash_2,
    nonce_2,
    input_bytes_2,
)


COMPUTATION_DB_URL_TEMPLATE = "sqlite:///./party_{party_id}.db"
NUM_PARTIES = 3
# Adjust these ports as needed
COORDINATION_PORT = 5565
MPC_PORT_BASE = 8010
MAX_DATA_PROVIDERS = 10
CLIENT_PORT_BASE = 14000
COMPUTATION_HOSTS = ["localhost"] * NUM_PARTIES
COMPUTATION_PARTY_PORTS = [5566 + party_id for party_id in range(NUM_PARTIES)]
MPSPDZ_PROJECT_ROOT = Path(__file__).parent.parent.parent / "MP-SPDZ"
CERTS_PATH = MPSPDZ_PROJECT_ROOT / "Player-Data"

TIMEOUT_MPC = 60

CMD_PREFIX_COORDINATION_SERVER = ["poetry", "run", "coordination-server-run"]
CMD_PREFIX_COMPUTATION_PARTY_SERVER = ["poetry", "run", "computation-party-server-run"]

async def start_coordination_server(cmd: list[str], port: int, tlsn_proofs_dir: Path):
    party_ips = [f"{host}:{port}" for host, port in zip(COMPUTATION_HOSTS, COMPUTATION_PARTY_PORTS)]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        env={
            **os.environ,
            "NUM_PARTIES": str(NUM_PARTIES),
            "PORT": str(port),
            "PARTY_IPS": '["' + '","'.join(party_ips) + '"]',
            "MPC_PORT_BASE": str(MPC_PORT_BASE),
            "CLIENT_PORT_BASE": str(CLIENT_PORT_BASE),
            "TLSN_PROOFS_DIR": str(tlsn_proofs_dir),
        },
        # stdout=asyncio.subprocess.PIPE,
        # stderr=asyncio.subprocess.PIPE
    )
    return process

async def start_computation_party_server(cmd: list[str], party_id: int, port: int):
    process = await asyncio.create_subprocess_exec(
        *cmd,
        env={
            **os.environ,
            "PORT": str(port),
            "PARTY_ID": str(party_id),
            "DATABASE_URL": COMPUTATION_DB_URL_TEMPLATE.format(party_id=party_id),
            "COORDINATION_SERVER_URL": f"http://localhost:{COORDINATION_PORT}",
            "MAX_DATA_PROVIDERS": str(MAX_DATA_PROVIDERS),
        },
        # stdout=asyncio.subprocess.PIPE,
        # stderr=asyncio.subprocess.PIPE
    )
    return process


@pytest.fixture
def tlsn_proofs_dir(tmp_path):
    p = tmp_path / "tlsn_proofs"
    p.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture
@pytest.mark.asyncio
async def servers(tlsn_proofs_dir):
    print(f"Setting up servers")
    # Remove the existing coordination.db file
    # Extract the coordination.db path from the database URL
    coordination_db_path = settings.database_url.split(":///")[1]

    if os.path.exists(coordination_db_path):
        os.remove(coordination_db_path)

    for party_id in range(NUM_PARTIES):
        party_db_path = COMPUTATION_DB_URL_TEMPLATE.format(party_id=party_id).split(":///")[1]
        if os.path.exists(party_db_path):
            os.remove(party_db_path)

    start_tasks = [
        start_coordination_server(CMD_PREFIX_COORDINATION_SERVER, COORDINATION_PORT, tlsn_proofs_dir),
    ] + [
        start_computation_party_server(CMD_PREFIX_COMPUTATION_PARTY_SERVER, party_id, port)
        for party_id, port in enumerate(COMPUTATION_PARTY_PORTS)
    ]

    processes = await asyncio.gather(*start_tasks)

    print("!@# All servers started concurrently")

    await asyncio.sleep(2)

    yield

    # Graceful shutdown attempt
    for process in processes:
        process.terminate()

    # Ensure all processes are terminated
    await asyncio.gather(*[process.wait() for process in processes])
    print("All servers terminated")

    # Additional wait to allow OS to release resources
    await asyncio.sleep(1)



async def generate_client_cert(tmp_dir: Path) -> tuple[int, Path, Path]:
    client_id = random.randint(0, MAX_CLIENT_ID - 1)
    # openssl req -newkey rsa -nodes -x509 -out Player-Data/C$i.pem -keyout Player-Data/C$i.key -subj "/CN=C$i"
    cert_path = tmp_dir / f"C{client_id}.pem"
    key_path = tmp_dir / f"C{client_id}.key"
    process = await asyncio.create_subprocess_exec(
        "/usr/local/bin/openssl", "req", "-newkey", "rsa", "-nodes", "-x509", "-out", str(cert_path), "-keyout", str(key_path), "-subj", f"/CN=C{client_id}",
        # stdout=asyncio.subprocess.PIPE,
        # stderr=asyncio.subprocess.PIPE,
    )
    await process.wait()
    if process.returncode != 0:
        raise Exception(f"Failed to generate client cert for {client_id}")
    return client_id, cert_path, key_path


async def run_data_sharing_client_with_cert(
    client_port_base: int,
    client_id: int,
    cert_path: Path,
    key_path: Path,
    value: int,
    nonce: str
):
    return await asyncio.get_event_loop().run_in_executor(
        None,
        run_data_sharing_client,
        COMPUTATION_HOSTS,
        client_port_base,
        str(CERTS_PATH),
        client_id,
        str(cert_path),
        str(key_path),
        value,
        nonce
    )

async def run_computation_query_client_with_cert(
    client_port_base: int,
    client_id: int,
    cert_path: Path,
    key_path: Path,
    computation_index: int
):
    return await asyncio.get_event_loop().run_in_executor(
        None,
        run_computation_query_client,
        COMPUTATION_HOSTS,
        client_port_base,
        str(CERTS_PATH),
        client_id,
        str(cert_path),
        str(key_path),
        MAX_DATA_PROVIDERS,
        computation_index
    )


@pytest.mark.asyncio
async def test_basic_integration(servers, tlsn_proofs_dir: Path, tmp_path: Path):
    # Clean up the existing shares
    for party_id in range(NUM_PARTIES):
        (MPSPDZ_PROJECT_ROOT / "Persistence" /f"Transactions-P{party_id}.data").unlink(missing_ok=True)

    voucher1 = "1234567890"
    voucher2 = "0987654321"
    identity1 = "test_identity1"
    identity2 = "test_identity2"
    with SessionLocal() as db:
        voucher_1 = Voucher(code=voucher1)
        db.add(voucher_1)
        voucher_2 = Voucher(code=voucher2)
        db.add(voucher_2)
        db.commit()
        db.refresh(voucher_1)
        db.refresh(voucher_2)

    response_register_1 = requests.post(f"http://localhost:{COORDINATION_PORT}/register", json={
        "voucher_code": voucher1,
        "identity": identity1
    })
    assert response_register_1.status_code == 200

    response_register_2 = requests.post(f"http://localhost:{COORDINATION_PORT}/register", json={
        "voucher_code": voucher2,
        "identity": identity2
    })
    assert response_register_2.status_code == 200

    print(f"input_bytes_1: {input_bytes_1}")
    print(f"data_commitment_hash_1: {data_commitment_hash_1}")
    print(f"nonce_1: {nonce_1}")
    print(f"input_bytes_2: {input_bytes_2}")
    print(f"data_commitment_hash_2: {data_commitment_hash_2}")
    print(f"nonce_2: {nonce_2}")

    # Request the data
    # asynchronously request /share_data for all parties
    client_id_1, cert_path_1, key_path_1 = await generate_client_cert(tmp_path)
    with open(cert_path_1, "r") as cert_file:
        cert_file_content_1 = cert_file.read()
    async with aiohttp.ClientSession() as session:
        async with session.post(f"http://localhost:{COORDINATION_PORT}/share_data", json={
            "identity": identity1,
            "tlsn_proof": TLSN_PROOF_1,
            "client_cert_file": cert_file_content_1,
            "client_id": client_id_1,
            "input_bytes": input_bytes_1,
        }) as response:
            assert response.status == 200
            data = await response.json()
            client_port_1 = data["client_port_base"]

    # Wait until all computation parties started their MPC servers.
    print(f"!@# Running data sharing client for {identity1=}, {client_port_1=}, {client_id_1=}, {cert_path_1=}, {key_path_1=}, {value_1=}, {nonce_1=}")
    await run_data_sharing_client_with_cert(
        client_port_1,
        client_id_1,
        cert_path_1,
        key_path_1,
        value_1,
        nonce_1
    )

    # print(f"!@# Requesting share data for {identity2}")
    # client_id_2, cert_path_2, key_path_2 = await generate_client_cert(tmp_path)
    # with open(cert_path_2, "r") as cert_file:
    #     cert_file_content = cert_file.read()
    # async with aiohttp.ClientSession() as session:
    #     async with session.post(f"http://localhost:{COORDINATION_PORT}/share_data", json={
    #         "identity": identity2,
    #         "tlsn_proof": TLSN_PROOF_2,
    #         "client_cert_file": cert_file_content,
    #         "client_id": client_id_2,
    #         "input_bytes": input_bytes_2,
    #     }) as response:
    #         assert response.status == 200
    #         data = await response.json()
    #         client_port_2 = data["client_port_base"]
    #         client_id_2 = data["client_id"]
    # await asyncio.create_subprocess_shell(
    #     f"cd {MPSPDZ_PROJECT_ROOT} && python ExternalDemo/save_data_client.py {client_port_2} {NUM_PARTIES} {client_id_2} {cert_path_2} {key_path_2} {value_2} {nonce_2}",
    #     # stdout=asyncio.subprocess.PIPE,
    #     # stderr=asyncio.subprocess.PIPE
    # )
    # await process.wait()


    client_id_3, cert_path_3, key_path_3 = await generate_client_cert(tmp_path)
    computation_index = 0

    # Request querying computation
    with open(cert_path_3, "r") as cert_file:
        cert_file_content_3 = cert_file.read()
    async with aiohttp.ClientSession() as session:
        async with session.post(f"http://localhost:{COORDINATION_PORT}/query_computation", json={
            "client_id": client_id_3,
            "client_cert_file": cert_file_content_3,
        }) as response:
            assert response.status == 200
            data = await response.json()
            client_port_3 = data["client_port_base"]

    await run_computation_query_client_with_cert(
        client_port_3,
        client_id_3,
        cert_path_3,
        key_path_3,
        computation_index
    )

    # async def wait_until_request_fulfilled():
    #     # Poll if tlsn_proof is saved, which means the background task running MPC finished.
    #     tlsn_proof_path = tlsn_proofs_dir / f"proof_{client_id}.json"
    #     while not tlsn_proof_path.exists():
    #         await asyncio.sleep(1)

    # await asyncio.wait_for(
    #     asyncio.gather(
    #         task,
    #         wait_until_request_fulfilled()
    #     ),
    #     timeout=TIMEOUT_MPC,
    # )

    print("Test finished")
