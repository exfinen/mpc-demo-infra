import json
import asyncio
import tempfile
from pathlib import Path
import logging

import aiohttp
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from .schemas import (
    RequestSharingDataRequest, RequestSharingDataResponse,
    RequestQueryComputationRequest, RequestQueryComputationResponse,
)
from .database import Voucher, get_db
from .config import settings
from ..constants import MAX_CLIENT_ID

router = APIRouter()

CMD_VERIFY_TLSN_PROOF = "cargo run --release --example simple_verifier"
TLSN_VERIFIER_PATH = Path(settings.tlsn_project_root) / "tlsn" / "examples" / "simple"

TIMEOUT_CALLING_COMPUTATION_SERVERS = 60


# Global lock for sharing data, to prevent concurrent sharing data requests.
sharing_data_lock = asyncio.Lock()


@router.post("/share_data", response_model=RequestSharingDataResponse)
async def share_data(request: RequestSharingDataRequest, db: Session = Depends(get_db)):
    voucher_code = request.voucher_code
    client_id = request.client_id
    tlsn_proof = request.tlsn_proof
    client_cert_file = request.client_cert_file
    logger.debug(f"Sharing data for {voucher_code=}, {client_id=}")

    logger.debug(f"Verifying registration for voucher code: {voucher_code}")
    if client_id >= MAX_CLIENT_ID:
        logger.error(f"Client ID is out of range: {client_id}")
        raise HTTPException(status_code=400, detail="Client ID is out of range")
    # Check if voucher exists
    voucher: Voucher | None = db.query(Voucher).filter(Voucher.code == voucher_code).first()
    if not voucher:
        logger.error(f"Voucher code not found: {voucher_code}")
        raise HTTPException(status_code=400, detail="Voucher code not found")
    if voucher.is_used:
        logger.error(f"Voucher code already used: {voucher_code}")
        raise HTTPException(status_code=400, detail="Voucher code already used")
    voucher.is_used = True
    secret_index = voucher.id

    logger.debug(f"Registration verified for voucher code: {voucher_code}, {client_id=}")

    # Verify TLSN proof.
    with tempfile.NamedTemporaryFile(delete=False) as temp_tlsn_proof_file:
        logger.debug(f"Writing TLSN proof to temporary file: {temp_tlsn_proof_file.name}")
        # Store TLSN proof in temporary file.
        temp_tlsn_proof_file.write(request.tlsn_proof.encode('utf-8'))

        logger.debug(f"Running TLSN proof verifier: {CMD_VERIFY_TLSN_PROOF} {temp_tlsn_proof_file.name}")
        # Run TLSN proof verifier
        process = await asyncio.create_subprocess_shell(
            f"cd {str(TLSN_VERIFIER_PATH)} && {CMD_VERIFY_TLSN_PROOF} {temp_tlsn_proof_file.name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        logger.debug(f"Getting TLSN proof verification result")
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            logger.error(f"TLSN proof verification failed with return code {process.returncode}, {stdout=}, {stderr=}")
            raise HTTPException(status_code=400, detail=f"TLSN proof verification failed with return code {process.returncode}, {stdout=}, {stderr=}")
        logger.debug(f"TLSN proof verification passed")

    # Acquire lock to prevent concurrent sharing data requests
    logger.debug(f"Acquiring lock for sharing data for {voucher_code=}")
    await sharing_data_lock.acquire()

    mpc_server_port_base, mpc_client_port_base = get_data_sharing_mpc_ports()
    logger.debug(f"Acquired lock. Using data sharing MPC ports: {mpc_server_port_base=}, {mpc_client_port_base=}")

    try:
        l = asyncio.Event()

        async def request_sharing_data_all_parties():
            try:
                logger.info(f"Requesting sharing data MPC for {voucher_code=}")
                async with aiohttp.ClientSession() as session:
                    tasks = []
                    for party_host, party_port in zip(settings.party_hosts, settings.party_ports):
                        url = f"{settings.party_web_protocol}://{party_host}:{party_port}/request_sharing_data_mpc"
                        headers = {"X-API-Key": settings.party_api_key}
                        task = session.post(url, json={
                            "tlsn_proof": tlsn_proof,
                            "mpc_port_base": mpc_server_port_base,
                            "secret_index": secret_index,
                            "client_id": client_id,
                            "client_port_base": mpc_client_port_base,
                            "client_cert_file": client_cert_file,
                        }, headers=headers)
                        tasks.append(task)
                    l.set()
                    logger.debug(f"Sending all requests concurrently")
                    # Send all requests concurrently
                    responses = await asyncio.gather(*tasks)
                # Check if all responses are successful
                logger.debug(f"Received responses for sharing data MPC for {voucher_code=}")
                for party_id, response in enumerate(responses):
                    if response.status != 200:
                        logger.error(f"Failed to request sharing data MPC from {party_id}: {response.status}")
                        raise HTTPException(status_code=500, detail=f"Failed to request sharing data MPC from {party_id}. Details: {await response.text()}")
                logger.debug(f"All responses for sharing data MPC for {voucher_code=} are successful")
                # Check if all data commitments are the same
                data_commitments = [(await response.json())["data_commitment"] for response in responses]
                if len(set(data_commitments)) != 1:
                    logger.error(f"Data commitments mismatch for {voucher_code=}. Something is wrong with MPC. {data_commitments=}")
                    raise HTTPException(status_code=400, detail="Data commitments mismatch")
                logger.debug(f"Data commitments for {voucher_code=} are the same: {data_commitments=}")
                # Check if data commitment hash from TLSN proof and MPC matches
                tlsn_data_commitment_hash = get_data_commitment_hash_from_tlsn_proof(tlsn_proof)
                if tlsn_data_commitment_hash != data_commitments[0]:
                    logger.error(f"Data commitment hash mismatch for {voucher_code=}. Something is wrong with TLSN proof. {tlsn_data_commitment_hash=} != {data_commitments[0]=}")
                    raise HTTPException(status_code=400, detail="Data commitment hash mismatch")
                logger.debug(f"Data commitment hash from TLSN proof and MPC matches for {voucher_code=}")

                # Proof is valid, copy to tlsn_proofs_dir, and delete the temp file.
                tlsn_proofs_dir = Path(settings.tlsn_proofs_dir)
                tlsn_proofs_dir.mkdir(parents=True, exist_ok=True)
                tlsn_proof_path = tlsn_proofs_dir / f"proof_{client_id}.json"
                tlsn_proof_path.write_text(request.tlsn_proof)
                try:
                    temp_tlsn_proof_file.close()
                except IOError as e:
                    logger.warning(f"Failed to close temporary TLSN proof file: {e}")
                try:
                    Path(temp_tlsn_proof_file.name).unlink()
                except (FileNotFoundError, PermissionError) as e:
                    logger.warning(f"Failed to delete temporary TLSN proof file: {e}")
                logger.debug(f"TLSN proof saved to {tlsn_proof_path}")
                db.commit()
                logger.debug(f"Committed changes to database for {voucher_code=}")
            finally:
                sharing_data_lock.release()
                logger.info(f"Released lock for sharing data for {voucher_code=}")

        logger.debug(f"Creating task for sharing data MPC for {voucher_code=}")
        asyncio.create_task(request_sharing_data_all_parties())
        logger.debug(f"Waiting for sharing data MPC for {voucher_code=}")
        # Wait until `gather` called, with a timeout
        try:
            await asyncio.wait_for(l.wait(), timeout=TIMEOUT_CALLING_COMPUTATION_SERVERS)
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout waiting for sharing data MPC for {voucher_code=}, {TIMEOUT_CALLING_COMPUTATION_SERVERS=}")
            raise e
        # Change the return statement
        return RequestSharingDataResponse(
            client_port_base=mpc_client_port_base
        )
    except Exception as e:
        logger.error(f"Failed to share data: {str(e)}")
        sharing_data_lock.release()
        logger.info(f"Released lock for sharing data for {voucher_code=}")
        raise HTTPException(status_code=400, detail="Failed to share data")

@router.post("/query_computation", response_model=RequestQueryComputationResponse)
async def query_computation(request: RequestQueryComputationRequest, db: Session = Depends(get_db)):
    client_id = request.client_id
    client_cert_file = request.client_cert_file
    logger.debug(f"Querying computation for client {client_id}")
    if client_id >= MAX_CLIENT_ID:
        logger.error(f"Client ID is out of range: {client_id}")
        raise HTTPException(status_code=400, detail="Client ID is out of range")

    logger.debug(f"Getting computation query MPC ports")
    mpc_server_port_base, mpc_client_port_base = get_computation_query_mpc_ports()
    logger.debug(f"Using computation query MPC ports: {mpc_server_port_base=}, {mpc_client_port_base=}")

    l = asyncio.Event()

    async def request_querying_computation_all_parties():
        logger.info(f"Requesting querying computation MPC for {client_id=}")
        async with aiohttp.ClientSession() as session:
            tasks = []
            for party_host, party_port in zip(settings.party_hosts, settings.party_ports):
                url = f"{settings.party_web_protocol}://{party_host}:{party_port}/request_querying_computation_mpc"
                headers = {"X-API-Key": settings.party_api_key}
                task = session.post(url, json={
                    "mpc_port_base": mpc_server_port_base,
                    "client_id": client_id,
                    "client_port_base": mpc_client_port_base,
                    "client_cert_file": client_cert_file,
                }, headers=headers)
                tasks.append(task)
            l.set()
            logger.debug(f"Sending all requests concurrently")
            # Send all requests concurrently
            responses = await asyncio.gather(*tasks)
        # Check if all responses are successful
        logger.debug(f"Received responses for querying computation MPC for {client_id=}")
        for party_id, response in enumerate(responses):
            if response.status != 200:
                logger.error(f"Failed to request querying computation MPC from {party_id}: {response.status}")
                raise HTTPException(status_code=500, detail=f"Failed to request querying computation MPC from {party_id}. Details: {await response.text()}")
        logger.debug(f"All responses for querying computation MPC for {client_id=} are successful")

    logger.debug(f"Creating task for querying computation MPC for {client_id=}")
    asyncio.create_task(request_querying_computation_all_parties())
    logger.debug(f"Waiting for querying computation MPC for {client_id=}")
    # Wait until `gather` called, with a timeout
    try:
        await asyncio.wait_for(l.wait(), timeout=TIMEOUT_CALLING_COMPUTATION_SERVERS)
    except asyncio.TimeoutError as e:
        logger.error(f"Timeout waiting for querying computation for {client_id=}, {TIMEOUT_CALLING_COMPUTATION_SERVERS=}")
        raise e
    logger.debug(f"Querying computation for {client_id=} passed")
    return RequestQueryComputationResponse(
        client_port_base=mpc_client_port_base
    )


def get_data_commitment_hash_from_tlsn_proof(tlsn_proof: str) -> str:
    proof_data = json.loads(tlsn_proof)
    private_openings = proof_data["substrings"]["private_openings"]
    if len(private_openings) != 1:
        raise ValueError(f"Expected 1 private opening, got {len(private_openings)}")
    _, openings = list(private_openings.items())[0]
    commitment = openings[1]
    data_commitment_hash = bytes(commitment["hash"]).hex()
    return data_commitment_hash


# Ports allocation:
# if num_parties = 3, free_ports_start = 8010, free_ports_end = 8100
# free_ports = [8010, 8011, 8012, ..., 8100]

def get_data_sharing_mpc_ports() -> tuple[int, int]:
    """
    Ports for data sharing MPC server/client are fixed since we can reuse the same ports,
    since only one data provider can share data at a time.

    data_sharing_mpc_server_ports = [
        free_ports_start, ..., free_ports_start + num_parties - 1,
    ]
    data_sharing_mpc_client_ports = [
        free_ports_start + num_parties, ..., free_ports_start + 2 * num_parties - 1,
    ]
    """
    server_port_base = settings.free_ports_start
    client_port_base = settings.free_ports_start + settings.num_parties
    return server_port_base, client_port_base


# NOTE: Shouldn't need a lock since it's all async and thus `get_computation_query_mpc_ports` is atomic.
# If any thread is used, we should use a lock here.
next_query_port_base = settings.free_ports_start + 2 * settings.num_parties

def get_computation_query_mpc_ports() -> tuple[int, int]:
    """
    Ports for computation query MPC server/client are dynamic since there can be multiple clients querying at the same time.
    """
    global next_query_port_base
    # server_ports =[next_query_port_base, ..., next_query_port_base + num_parties - 1]
    server_port_base = next_query_port_base
    # client_ports = [next_query_port_base + num_parties, ..., next_query_port_base + 2 * num_parties - 1]
    client_port_base = next_query_port_base + settings.num_parties
    if client_port_base + settings.num_parties > settings.free_ports_end:
        # Used up all ports, wrap around
        next_query_port_base = settings.free_ports_start + 2 * settings.num_parties
    else:
        next_query_port_base = client_port_base + settings.num_parties
    return server_port_base, client_port_base
