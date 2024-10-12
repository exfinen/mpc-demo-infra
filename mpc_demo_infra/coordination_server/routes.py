import json
import asyncio
import tempfile
from pathlib import Path
from dataclasses import dataclass
import logging

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from .schemas import (
    NegotiateShareDataRequest, NegotiateShareDataResponse,
    RegisterDataProviderRequest, RegisterDataProviderResponse,
    VerifyRegistrationRequest, VerifyRegistrationResponse,
    MPCStatus, CheckShareDataStatusResponse,
    SetShareDataCompleteRequest,
    RequestSharingDataRequest, RequestSharingDataResponse,
)
from .database import DataProvider, Voucher, get_db
from .config import settings

router = APIRouter()

CMD_VERIFYTLSN_PROOF = "cargo run --release --example simple_verifier"
TLSN_VERIFIER_PATH = Path(settings.tlsn_project_root) / "tlsn" / "examples" / "simple"

TIMEOUT_CALLING_COMPUTATION_SERVERS = 30


@router.post("/register", response_model=RegisterDataProviderResponse)
def register(request: RegisterDataProviderRequest, db: Session = Depends(get_db)):
    logger.info(f"Attempting to register provider with identity: {request.identity}")
    # Check if voucher is valid
    voucher: Voucher | None = db.query(Voucher).filter(Voucher.code == request.voucher_code).first()
    if not voucher:
        raise HTTPException(status_code=400, detail="Invalid voucher code")
    if voucher.data_provider:
        raise HTTPException(status_code=400, detail="Voucher already used")

    # Check if identity has existed, raise error
    if db.query(DataProvider).filter(DataProvider.identity == request.identity).first():
        raise HTTPException(status_code=400, detail="Identity already exists")

    # Create a new data provider and associate it with the voucher
    new_provider = DataProvider(voucher=voucher, identity=request.identity)
    db.add(new_provider)
    db.commit()
    db.refresh(new_provider)
    logger.info(f"Successfully registered provider with id: {new_provider.id}")
    return {"provider_id": new_provider.id}


# Global lock for sharing data, to prevent concurrent sharing data requests.
sharing_data_lock = asyncio.Lock()


@router.post("/share_data", response_model=RequestSharingDataResponse)
async def share_data(request: RequestSharingDataRequest, db: Session = Depends(get_db)):
    identity = request.identity
    tlsn_proof = request.tlsn_proof

    logger.info(f"Verifying registration for identity: {identity}")
    # Check if identity has not registered, raise error
    data_provider: DataProvider | None = db.query(DataProvider).filter(DataProvider.identity == identity).first()
    if not data_provider:
        raise HTTPException(status_code=400, detail="Identity not registered")
    logger.info(f"Registration verified for identity: {identity}")
    client_id = data_provider.id

    # Verify TLSN proof.
    with tempfile.NamedTemporaryFile(delete=False) as temp_tlsn_proof_file:
        # Store TLSN proof in temporary file.
        temp_tlsn_proof_file.write(request.tlsn_proof.encode('utf-8'))

        # Run TLSN proof verifier
        process = await asyncio.create_subprocess_shell(
            f"cd {str(TLSN_VERIFIER_PATH)} && {CMD_VERIFYTLSN_PROOF} {temp_tlsn_proof_file.name}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise HTTPException(status_code=400, detail=f"TLSN proof verification failed with return code {process.returncode}, {stdout=}, {stderr=}")

    # Acquire lock to prevent concurrent sharing data requests
    logger.info(f"Acquiring lock for sharing data for {identity=}")
    await sharing_data_lock.acquire()

    try:
        # Request computation parties servers to run MPC
        mpc_ports = [settings.mpc_port_base + party_id for party_id in range(settings.num_parties)]
        l = asyncio.Event()

        # Return ports for computation parties servers to run MPC so that user can run client to connect.
        # Then, calls `request_sharing_data_mpc` on each computation party server.
        async def request_sharing_data_all_parties():
            try:
                logger.info(f"Requesting sharing data MPC for {identity=}")
                async with aiohttp.ClientSession() as session:
                    tasks = []
                    for party_ip in settings.party_ips:
                        url = f"{settings.protocol}://{party_ip}/request_sharing_data_mpc"
                        task = session.post(url, json={
                            "client_id": client_id,
                            "mpc_ports": mpc_ports,
                            "tlsn_proof": tlsn_proof
                        })
                        tasks.append(task)
                    l.set()
                    print(f"!@# tasks={tasks}")
                    # Send all requests concurrently
                    responses = await asyncio.gather(*tasks)
                # Check if all responses are successful
                logger.info(f"Received responses for sharing data MPC for {identity=}")
                for party_id, response in enumerate(responses):
                    if response.status != 200:
                        logger.error(f"Failed to request sharing data MPC from {party_id}: {response.status}")
                        raise HTTPException(status_code=500, detail=f"Failed to request sharing data MPC from {party_id}")
                logger.debug(f"All responses for sharing data MPC for {identity=} are successful")
                # Check if all data commitments are the same
                data_commitments = [(await response.json())["data_commitment"] for response in responses]
                if len(set(data_commitments)) != 1:
                    logger.error(f"Data commitments mismatch for {identity=}. Something is wrong with MPC. {data_commitments=}")
                    raise HTTPException(status_code=400, detail="Data commitments mismatch")
                logger.debug(f"Data commitments for {identity=} are the same: {data_commitments=}")
                # Check if data commitment hash from TLSN proof and MPC matches
                tlsn_data_commitment_hash = get_data_commitment_hash_from_tlsn_proof(tlsn_proof)
                if tlsn_data_commitment_hash != data_commitments[0]:
                    logger.error(f"Data commitment hash mismatch for {identity=}. Something is wrong with TLSN proof. {tlsn_data_commitment_hash=} != {data_commitments[0]=}")
                    raise HTTPException(status_code=400, detail="Data commitment hash mismatch")
                logger.debug(f"Data commitment hash from TLSN proof and MPC matches for {identity=}")

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
            finally:
                sharing_data_lock.release()
                logger.info(f"Released lock for sharing data for {identity=}")

        asyncio.create_task(request_sharing_data_all_parties())
        # Wait until `gather` called, with a timeout
        try:
            await asyncio.wait_for(l.wait(), timeout=TIMEOUT_CALLING_COMPUTATION_SERVERS)
        except asyncio.TimeoutError as e:
            logger.error(f"Timeout waiting for sharing data MPC for {identity=}, {TIMEOUT_CALLING_COMPUTATION_SERVERS=}")
            raise e
        # Return ports for computation parties servers to run MPC so that user can run client to connect
        return RequestSharingDataResponse(mpc_ports=mpc_ports)
    except Exception as e:
        logger.error(f"Failed to share data: {str(e)}")
        sharing_data_lock.release()
        raise HTTPException(status_code=400, detail="Failed to share data")


def get_data_commitment_hash_from_tlsn_proof(tlsn_proof: str) -> str:
    proof_data = json.loads(tlsn_proof)
    private_openings = proof_data["substrings"]["private_openings"]
    if len(private_openings) != 1:
        raise ValueError(f"Expected 1 private opening, got {len(private_openings)}")
    _, openings = list(private_openings.items())[0]
    commitment = openings[1]
    data_commitment_hash = bytes(commitment["hash"]).hex()
    return data_commitment_hash
