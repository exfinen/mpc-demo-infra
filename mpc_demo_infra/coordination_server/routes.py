import re
import json
import asyncio
import tempfile
from pathlib import Path
import logging

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from .schemas import (
    RequestHasAddressSharedDataRequest, RequestHasAddressSharedDataResponse,
    RequestSharingDataRequest, RequestSharingDataResponse,
    RequestQueryComputationRequest, RequestQueryComputationResponse,
    RequestGetPositionRequest, RequestGetPositionResponse,
    RequestValidateComputationKeyRequest, RequestValidateComputationKeyResponse,
    RequestFinishComputationRequest, RequestFinishComputationResponse,
    RequestAddUserToQueueRequest, RequestAddUserToQueueResponse,
)
from .database import MPCSession, get_db, SessionLocal
from .config import settings
from ..constants import MAX_CLIENT_ID, CLIENT_TIMEOUT
from .user_queue import AddResult

router = APIRouter()

CMD_VERIFY_TLSN_PROOF = "cargo run --release --example binance_verifier"
TLSN_VERIFIER_PATH = Path(settings.tlsn_project_root) / "tlsn" / "examples" / "binance"


# Global lock for sharing data, to prevent concurrent sharing data requests.
sharing_data_lock = asyncio.Lock()


@router.get("/has_address_shared_data", response_model=RequestHasAddressSharedDataResponse)
async def has_address_shared_data(eth_address: str, db: Session = Depends(get_db)) -> bool:
    res = db.query(MPCSession).filter(MPCSession.eth_address == eth_address).first() is not None
    logger.info(f"has_address_shared_data: {eth_address}; {res}")
    return RequestHasAddressSharedDataResponse(has_shared_data=res)

def add_user_impl(add_user_func, queue_to_str, access_key: str):
    result = add_user_func(access_key)
    logger.info(f"add_user_to_queue: {access_key}; {queue_to_str()}")
    if result == AddResult.ALREADY_IN_QUEUE:
        logger.info(f"{access_key} not added. Already in the queue")
        return RequestAddUserToQueueResponse(result=AddResult.ALREADY_IN_QUEUE)
    elif result == AddResult.QUEUE_IS_FULL:
        logger.warn(f"{access_key} not added. The queue is full")
        return RequestAddUserToQueueResponse(result=AddResult.QUEUE_IS_FULL)
    else:
        logger.info(f"Added {access_key} to the queue")
        return RequestAddUserToQueueResponse(result=AddResult.SUCCEEDED)

@router.post("/add_user_to_queue", response_model=RequestAddUserToQueueResponse)
async def add_user_to_queue(request: RequestAddUserToQueueRequest, x: Request):
    return add_user_impl(
        x.app.state.user_queue.add_user,
        x.app.state.user_queue._queue_to_str,
        request.access_key
    )

@router.post("/add_priority_user_to_queue", response_model=RequestAddUserToQueueResponse)
async def add_priority_user_to_queue(request: RequestAddUserToQueueRequest, x: Request):
    return add_user_impl(
        x.app.state.user_queue.add_priority_user,
        x.app.state.user_queue._queue_to_str,
        request.access_key
    )

@router.post("/get_position", response_model=RequestGetPositionResponse)
async def get_position(request: RequestGetPositionRequest, x: Request):
    position = x.app.state.user_queue.get_position(request.access_key)
    computation_key = x.app.state.user_queue.get_computation_key(request.access_key)
    logger.info(f"get_position: {request.access_key}; position={position}, computation_key={computation_key}")
    return RequestGetPositionResponse(position=position, computation_key=computation_key)

@router.post("/validate_computation_key", response_model=RequestValidateComputationKeyResponse)
async def validate_computation_key(request: RequestValidateComputationKeyRequest, x: Request):
    is_valid = x.app.state.user_queue.validate_computation_key(request.access_key, request.computation_key)
    logger.info(f"validate_computation_key: {request.access_key}; {is_valid} {x.app.state.user_queue._queue_to_str()}")
    return RequestValidateComputationKeyResponse(is_valid=is_valid)

@router.post("/finish_computation", response_model=RequestFinishComputationResponse)
async def finish_computation(request: RequestFinishComputationRequest, x: Request):
    is_finished = x.app.state.user_queue.finish_computation(request.access_key, request.computation_key)
    logger.info(f"finish_computation: {request.access_key}; {x.app.state.user_queue._queue_to_str()}")
    return RequestFinishComputationResponse(is_finished=is_finished)

@router.post("/share_data", response_model=RequestSharingDataResponse)
async def share_data(request: RequestSharingDataRequest, x: Request, db: Session = Depends(get_db)):
    eth_address = request.eth_address
    tlsn_proof = request.tlsn_proof
    client_id = request.client_id
    client_cert_file = request.client_cert_file
    access_key = request.access_key
    computation_key = request.computation_key
    logger.info(f"Sharing data for {eth_address=}, {client_id=}, computation_key={computation_key}, access_key={access_key}")

    # Check if computation key is valid
    if not x.app.state.user_queue.validate_computation_key(access_key, computation_key):
        logger.error(f"Invalid computation key {computation_key}")
        raise HTTPException(status_code=400, detail=f"Invalid computation key {computation_key}")
    logger.info(f"{eth_address}: Computation key {computation_key} is valid")

    logger.info(f"Verifying registration for voucher code: {eth_address}")
    if client_id >= MAX_CLIENT_ID:
        logger.error(f"{eth_address}: Client ID is out of range: {client_id}")
        raise HTTPException(status_code=400, detail=f"{eth_address}: Client ID is out of range")

    # Verify TLSN proof.
    with tempfile.NamedTemporaryFile(delete=False) as temp_tlsn_proof_file:
        logger.info(f"Writing TLSN proof to temporary file: {temp_tlsn_proof_file.name}")
        # Store TLSN proof in temporary file.
        temp_tlsn_proof_file.write(request.tlsn_proof.encode('utf-8'))

        logger.info(f"Running TLSN proof verifier: {CMD_VERIFY_TLSN_PROOF} {temp_tlsn_proof_file.name}")
        # Run TLSN proof verifier
        process = await asyncio.create_subprocess_shell(
            f"cd {str(TLSN_VERIFIER_PATH)} && {CMD_VERIFY_TLSN_PROOF} {temp_tlsn_proof_file.name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        logger.info(f"Getting TLSN proof verification result")
        stdout, stderr = await process.communicate()
        try:
            uid = get_uid_from_tlsn_proof_verifier(stdout.decode('utf-8'))
            logger.info(f"Got UID from TLSN proof verifier: {uid}")
        except ValueError as e:
            logger.error(f"Failed to get UID from TLSN proof verifier: {e}")
            raise HTTPException(status_code=400, detail="Failed to get UID from TLSN proof verifier")
        if process.returncode != 0:
            logger.error(f"TLSN proof verification failed with return code {process.returncode}, {stdout=}, {stderr=}")
            raise HTTPException(status_code=400, detail=f"TLSN proof verification failed with return code {process.returncode}, {stdout=}, {stderr=}")
        logger.info(f"TLSN proof verification passed")

    # Check if uid already in db. If so, raise an error.
    if settings.prohibit_multiple_contributions:
        if db.query(MPCSession).filter(MPCSession.uid == uid).first():
            logger.error(f"UID {uid} already in database")
            raise HTTPException(status_code=400, detail=f"UID {uid} already shared data")

    # Acquire lock to prevent concurrent sharing data requests
    logger.info(f"Acquiring lock for sharing data for {eth_address=}")
    await sharing_data_lock.acquire()

    # Get secret index as number of MPC session
    num_mpc_sessions = db.query(MPCSession).count()
    secret_index = num_mpc_sessions + 1

    logger.info(f"Registration verified for voucher code: {eth_address}, {client_id=}")

    # FIXME: use rotated ports for now
    mpc_server_port_base, mpc_client_port_base = get_computation_query_mpc_ports()
    logger.info(f"Acquired lock. Using data sharing MPC ports: {mpc_server_port_base=}, {mpc_client_port_base=}")

    try:
        # l = asyncio.Event()

        async def request_sharing_data_all_parties():
            try:
                logger.info(f"Requesting sharing data MPC for {eth_address=}")
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
                    # l.set()
                    logger.info(f"Sending all requests concurrently")
                    # Send all requests concurrently
                    responses = await asyncio.gather(*tasks)
                    logger.info(f"Received responses for sharing data MPC for {eth_address=}")
                    # Check if all responses are successful
                    for party_id, response in enumerate(responses):
                        if response.status != 200:
                            logger.error(f"Failed to request sharing data MPC from {party_id}: {response.status}")
                            raise HTTPException(status_code=500, detail=f"Failed to request sharing data MPC from {party_id}. Details: {await response.text()}")
                    # Check if all data commitments are the same
                    data_commitments = [(await response.json())["data_commitment"] for response in responses]
                logger.info(f"All responses for sharing data MPC for {eth_address=} are successful. data_commitments={data_commitments}")
                if len(set(data_commitments)) != 1:
                    logger.error(f"Data commitments mismatch for {eth_address=}. Something is wrong with MPC. {data_commitments=}")
                    raise HTTPException(status_code=400, detail="Data commitments mismatch")
                logger.info(f"Data commitments for {eth_address=} are the same: {data_commitments=}")
                # Check if data commitment hash from TLSN proof and MPC matches
                tlsn_data_commitment_hash = get_data_commitment_hash_from_tlsn_proof(tlsn_proof)
                logger.info(f"tlsn_data_commitment_hash={tlsn_data_commitment_hash}, data_commitments[0]={data_commitments[0]}")
                # FIXME:
                # if tlsn_data_commitment_hash != data_commitments[0]:
                #     logger.error(f"Data commitment hash mismatch for {eth_address=}. Something is wrong with TLSN proof. {tlsn_data_commitment_hash=} != {data_commitments[0]=}")
                #     raise HTTPException(status_code=400, detail="Data commitment hash mismatch")
                logger.info(f"Data commitment hash from TLSN proof and MPC matches for {eth_address=}")

                # Proof is valid, copy to tlsn_proofs_dir, and delete the temp file.
                tlsn_proofs_dir = Path(settings.tlsn_proofs_dir)
                tlsn_proofs_dir.mkdir(parents=True, exist_ok=True)
                tlsn_proof_path = tlsn_proofs_dir / f"proof_{secret_index}.json"
                tlsn_proof_path.write_text(request.tlsn_proof)
                try:
                    temp_tlsn_proof_file.close()
                except IOError as e:
                    logger.warn(f"Failed to close temporary TLSN proof file: {e}")
                Path(temp_tlsn_proof_file.name).unlink(missing_ok=True)
                logger.info(f"TLSN proof saved to {tlsn_proof_path}")
                # Mark the voucher as used. A new db session is used to avoid using
                # `db`, which is possibly closed after we return.
                with SessionLocal() as db_session:
                    # Add MPC session to database
                    mpc_session = MPCSession(
                        eth_address=eth_address,
                        uid=uid,
                        tlsn_proof_path=str(tlsn_proof_path),
                    )
                    db_session.add(mpc_session)
                    db_session.commit()
                    logger.info(f"Committed changes to database for {eth_address=}")
            finally:
                sharing_data_lock.release()
                logger.info(f"Released lock for sharing data for {eth_address=}")

        logger.info(f"Creating task for sharing data MPC for {eth_address=}")
        share_data_task = asyncio.create_task(request_sharing_data_all_parties())
        #await asyncio.gather(share_data_task)
        logger.info(f"Waiting for sharing data MPC for {eth_address=}")
        # Wait until `gather` called, with a timeout
        # try:
        #     await asyncio.wait_for(l.wait(), timeout=CLIENT_TIMEOUT)
        # except asyncio.TimeoutError as e:
        #     logger.error(f"Timeout waiting for sharing data MPC for {eth_address=}, {CLIENT_TIMEOUT=}")
        #     raise e
        # Change the return statement
        return RequestSharingDataResponse(
            client_port_base=mpc_client_port_base
        )
    except Exception as e:
        logger.error(f"Failed to share data: {str(e)}")
        sharing_data_lock.release()
        logger.info(f"Released lock for sharing data for {eth_address=}")
        raise HTTPException(status_code=400, detail="Failed to share data")

@router.post("/query_computation", response_model=RequestQueryComputationResponse)
async def query_computation(request: RequestQueryComputationRequest, x: Request, db: Session = Depends(get_db)):
    client_id = request.client_id
    client_cert_file = request.client_cert_file
    access_key = request.access_key
    computation_key = request.computation_key

    # Check if computation key is valid
    if not x.app.state.user_queue.validate_computation_key(access_key, computation_key):
        logger.error(f"Invalid computation key ({computation_key})")
        raise HTTPException(status_code=400, detail=f"Invalid computation key {computation_key}")
    logger.info(f"Computation key ({computation_key}) is valid")

    logger.info(f"Querying computation for client {client_id}")
    if client_id >= MAX_CLIENT_ID:
        logger.error(f"Client ID is out of range: {client_id}")
        raise HTTPException(status_code=400, detail="Client ID is out of range")

    logger.info(f"Getting computation query MPC ports")
    mpc_server_port_base, mpc_client_port_base = get_computation_query_mpc_ports()
    logger.info(f"Using computation query MPC ports: {mpc_server_port_base=}, {mpc_client_port_base=}")

    num_data_providers = db.query(MPCSession).count()
    if num_data_providers == 0:
        logger.error(f"No MPC session found for {client_id=}")
        raise HTTPException(status_code=400, detail="No MPC session found")

    # l = asyncio.Event()

    async def request_querying_computation_all_parties():
        logger.info(f"Requesting querying computation MPC for {client_id=}")
        async with aiohttp.ClientSession() as session:
            tasks = []
            for party_host, party_port in zip(settings.party_hosts, settings.party_ports):
                url = f"{settings.party_web_protocol}://{party_host}:{party_port}/request_querying_computation_mpc"
                headers = {"X-API-Key": settings.party_api_key}
                task = session.post(url, json={
                    "num_data_providers": num_data_providers,
                    "mpc_port_base": mpc_server_port_base,
                    "client_id": client_id,
                    "client_port_base": mpc_client_port_base,
                    "client_cert_file": client_cert_file,
                }, headers=headers)
                tasks.append(task)
            # l.set()
            logger.info(f"Sending all requests concurrently")
            # Send all requests concurrently
            responses = await asyncio.gather(*tasks)
        # Check if all responses are successful
        logger.info(f"Received responses for querying computation MPC for {client_id=}")
        for party_id, response in enumerate(responses):
            if response.status != 200:
                logger.error(f"Failed to request querying computation MPC from {party_id}: {response.status}")
                raise HTTPException(status_code=500, detail=f"Failed to request querying computation MPC from {party_id}. Details: {await response.text()}")
        logger.info(f"All responses for querying computation MPC for {client_id=} are successful")

    logger.info(f"Creating task for querying computation MPC for {client_id=}")
    query_computation_task = asyncio.create_task(request_querying_computation_all_parties())
    #await asyncio.gather(query_computation_task)
    logger.info(f"Waiting for querying computation MPC for {client_id=}")
    # Wait until `gather` called, with a timeout
    # try:
    #     await asyncio.wait_for(l.wait(), timeout=CLIENT_TIMEOUT)
    # except asyncio.TimeoutError as e:
    #     logger.error(f"Timeout waiting for querying computation for {client_id=}, {CLIENT_TIMEOUT=}")
    #     raise e
    logger.info(f"Querying computation for {client_id=} passed")
    return RequestQueryComputationResponse(
        client_port_base=mpc_client_port_base
    )


def get_uid_from_tlsn_proof_verifier(stdout_from_tlsn_proof_verifier: str) -> int:
    print(f"stdout: {stdout_from_tlsn_proof_verifier}");
    uid_match = re.search(r'"uid":(\d+)[,}]', stdout_from_tlsn_proof_verifier)
    if uid_match:
        uid = uid_match.group(1)
        logger.info(f"UID: {uid}")
    else:
        raise ValueError(
            f"UID not found in stdout from TLSN proof verifier: {stdout_from_tlsn_proof_verifier}"
        )
    return int(uid)


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
