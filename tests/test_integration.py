import os
import requests
import pytest
import asyncio
import aiohttp
from mpc_demo_infra.coordination_server.config import settings
from mpc_demo_infra.coordination_server.database import SessionLocal, Voucher

from .common import TLSN_PROOF


COMPUTATION_DB_URL_TEMPLATE = "sqlite:///./party_{party_id}.db"
# Adjust these ports as needed
COORDINATION_PORT = 5566
COMPUTATION_PORTS = [COORDINATION_PORT + 1, COORDINATION_PORT + 2, COORDINATION_PORT + 3]

CMD_PREFIX_COORDINATION_SERVER = ["poetry", "run", "coordination-server-run"]
CMD_PREFIX_COMPUTATION_PARTY_SERVER = ["poetry", "run", "computation-party-server-run"]

async def start_coordination_server(cmd: list[str], port: int):
    print(f"!@# Starting server on port {port}")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        env={**os.environ, "PORT": str(port)},
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
        },
        # stdout=asyncio.subprocess.PIPE,
        # stderr=asyncio.subprocess.PIPE
    )
    return process

@pytest.fixture(scope="function")
@pytest.mark.asyncio
async def servers():
    print(f"Setting up servers")
    # Remove the existing coordination.db file
    # Extract the coordination.db path from the database URL
    coordination_db_path = settings.database_url.split(":///")[-1]

    if os.path.exists(coordination_db_path):
        os.remove(coordination_db_path)

    for party_id in range(settings.num_parties):
        party_db_path = COMPUTATION_DB_URL_TEMPLATE.format(party_id=party_id).split(":///")[-1]
        if os.path.exists(party_db_path):
            os.remove(party_db_path)

    start_tasks = [
        start_coordination_server(CMD_PREFIX_COORDINATION_SERVER, COORDINATION_PORT),
    ] + [
        start_computation_party_server(CMD_PREFIX_COMPUTATION_PARTY_SERVER, party_id, port)
        for party_id, port in enumerate(COMPUTATION_PORTS)
    ]

    processes = await asyncio.gather(*start_tasks)

    print("!@# All servers started concurrently")

    await asyncio.sleep(2)

    yield

    for process in processes:
        process.terminate()
    await asyncio.gather(*[process.wait() for process in processes])
    print("All servers terminated")


@pytest.mark.asyncio
async def test_basic_integration(servers):
    print("Starting basic integration test")

    # Setup: Create necessary clients or API calls
    print("Setup: Creating necessary clients or API calls")

    # Test step 1: Verify coordination server is running
    print("Test step 1: Verifying coordination server is running")
    # Add voucher to coordination server
    # access db through db url

    voucher = "1234567890"
    identity = "test_identity"
    with SessionLocal() as db:
        voucher = Voucher(code=voucher)
        db.add(voucher)
        db.commit()
        db.refresh(voucher)

    # Register the user
    response = requests.post(f"http://localhost:{COORDINATION_PORT}/register", json={
        "voucher_code": voucher.code,
        "identity": identity
    })
    assert response.status_code == 200
    client_id = response.json()["provider_id"]
    print(f"!@# Client ID: {client_id}")

    # Request the data
    # for party_id in range(settings.num_parties):
    # asynchronously request /share_data for all parties
    async def request_share_data(party_id):
        party_port = COMPUTATION_PORTS[party_id]
        async with aiohttp.ClientSession() as session:
            async with session.post(f"http://localhost:{party_port}/share_data", json={
                "identity": identity,
                "tlsn_proof": TLSN_PROOF
            }) as response:
                assert response.status == 200
                data = await response.json()
                print(f"!@# Data: {data}")
        # TODO: Get mpc port and run client interface client


    await asyncio.gather(*[request_share_data(party_id) for party_id in range(settings.num_parties)])


    print("Test finished")

