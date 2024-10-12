import os
import requests
import pytest
import asyncio
import aiohttp
import signal
from mpc_demo_infra.coordination_server.config import settings
from mpc_demo_infra.coordination_server.database import SessionLocal, Voucher

from .common import TLSN_PROOF


COMPUTATION_DB_URL_TEMPLATE = "sqlite:///./party_{party_id}.db"
# Adjust these ports as needed
COORDINATION_PORT = 5566
COMPUTATION_PORTS = [COORDINATION_PORT + 1, COORDINATION_PORT + 2, COORDINATION_PORT + 3]

CMD_PREFIX_COORDINATION_SERVER = ["poetry", "run", "coordination-server-run"]
CMD_PREFIX_COMPUTATION_PARTY_SERVER = ["poetry", "run", "computation-party-server-run"]

async def start_coordination_server(cmd: list[str], port: int, mpc_ports: list[int]):
    print(f"!@# Starting server on port {port}")
    party_ips = [f"localhost:{port}" for port in mpc_ports]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        env={
            **os.environ,
            "PORT": str(port),
            "PARTY_IPS": '["' + '","'.join(party_ips) + '"]',
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
    coordination_db_path = settings.database_url.split(":///")[1]

    if os.path.exists(coordination_db_path):
        os.remove(coordination_db_path)

    for party_id in range(settings.num_parties):
        party_db_path = COMPUTATION_DB_URL_TEMPLATE.format(party_id=party_id).split(":///")[1]
        if os.path.exists(party_db_path):
            os.remove(party_db_path)

    start_tasks = [
        start_coordination_server(CMD_PREFIX_COORDINATION_SERVER, COORDINATION_PORT, COMPUTATION_PORTS),
    ] + [
        start_computation_party_server(CMD_PREFIX_COMPUTATION_PARTY_SERVER, party_id, port)
        for party_id, port in enumerate(COMPUTATION_PORTS)
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


@pytest.mark.asyncio
async def test_basic_integration(servers):
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

    # Request the data
    # for party_id in range(settings.num_parties):
    # asynchronously request /share_data for all parties
    async with aiohttp.ClientSession() as session:
        async with session.post(f"http://localhost:{COORDINATION_PORT}/share_data", json={
            "identity": identity,
            "tlsn_proof": TLSN_PROOF
        }) as response:
            assert response.status == 200
            data = await response.json()
            print(f"!@# Data: {data}")
            mpc_ports = data["mpc_ports"]
    assert len(mpc_ports) == settings.num_parties
    await asyncio.sleep(10)
    # TODO: Run client interface client and connect to mpc_ports

    print("Test finished")
