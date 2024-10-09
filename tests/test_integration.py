import os
import pytest
import asyncio

from mpc_demo_infra.coordination_server.config import settings

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
    if os.path.exists(settings.database_url):
        os.remove(settings.database_url)
    for party_id in range(settings.num_parties):
        if os.path.exists(COMPUTATION_DB_URL_TEMPLATE.format(party_id=party_id)):
            os.remove(COMPUTATION_DB_URL_TEMPLATE.format(party_id=party_id))

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
    # TODO: Implement a check to ensure the coordination server is accessible

    # Test step 2: Verify computation party servers are running
    print("Test step 2: Verifying computation party servers are running")
    # TODO: Implement checks for each computation party server

    # Test step 3: Perform a basic MPC operation
    print("Test step 3: Performing a basic MPC operation")
    # TODO: Implement a simple MPC operation and verify the result

    # Cleanup: Any necessary cleanup steps
    print("Cleanup: Performing any necessary cleanup steps")

    print("Test completed, waiting for 10 seconds before terminating")
    await asyncio.sleep(1)  # Reduced from 1000 to 10 seconds for quicker debugging
    print("Test finished")

