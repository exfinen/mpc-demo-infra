import re
import tempfile
import logging
import subprocess
from threading import Lock, Event
from pathlib import Path

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from .schemas import (
    ShareDataRequest,
    ShareDataResponse,
    QueryComputationRequest,
    QueryComputationResponse,
)
from .database import get_db
from .config import settings

router = APIRouter()

CMD_VERIFYTLSN_PROOF = "cargo run --release --example simple_verifier"
TLSN_VERIFIER_PATH = Path(settings.tlsn_project_root) / "tlsn" / "examples" / "simple"
MPSPDZ_PROGRAM_DIR = Path(settings.mpspdz_project_root) / "Programs" / "Source"
TEMPLATE_PROGRAM_DIR = Path(__file__).parent.parent / "program"
CMD_COMPILE_MPC = "./compile.py"
CMD_RUN_MPC = f"./semi-party.x"


@router.post("/share_data", response_model=ShareDataResponse)
def share_data(request: ShareDataRequest, db: Session = Depends(get_db)):
    logger.info("%s is sharing data", request.identity)
    coordination_server_url = settings.coordination_server_url

    # 1. Call verify_identity on coordination server
    verify_url = f"{coordination_server_url}/verify_identity"
    verify_data = {"identity": request.identity}

    try:
        response = requests.post(verify_url, json=verify_data)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to verify identity: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to verify identity with coordination server")

    client_id = response.json()["client_id"]

    # 2. Verify TLSN proof
    with tempfile.NamedTemporaryFile() as temp_file:
        # Store TLSN proof in temporary file.
        temp_file.write(request.tlsn_proof.encode('utf-8'))

        # Run TLSN proof verifier
        try:
            subprocess.run(
                f"cd {str(TLSN_VERIFIER_PATH)} && {CMD_VERIFYTLSN_PROOF} {temp_file.name}",
                check=True,
                shell=True,
                # capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to verify TLSN proof: {str(e)}")
            raise HTTPException(status_code=400, detail="Failed when verifying TLSN proof")

        # Proof is valid, copy to tlsn_proofs_dir and delete the temp file.
        tlsn_proofs_dir = Path(settings.tlsn_proofs_dir)
        tlsn_proofs_dir.mkdir(parents=True, exist_ok=True)
        tlsn_proof_path = tlsn_proofs_dir / f"proof_{client_id}.json"
        tlsn_proof_path.write_text(request.tlsn_proof)

    # 3. Call /negotiate_share_data on coordination server and get mpc port
    negotiate_url = f"{coordination_server_url}/negotiate_share_data"
    negotiate_data = {"party_id": settings.party_id, "identity": request.identity}
    try:
        response = requests.post(negotiate_url, json=negotiate_data)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to negotiate share data: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to negotiate share data with coordination server")
    print(f"mpc_port: {response.json()}")
    mpc_ports = response.json()["ports"]
    if len(mpc_ports) != settings.num_parties:
        raise HTTPException(status_code=400, detail="Failed to negotiate share data with coordination server")

    # Prepare for IP file
    mpc_addresses = [
        f"{ip}:{port}" for ip, port in zip(settings.party_ips, mpc_ports)
    ]
    with tempfile.NamedTemporaryFile(delete=False) as ip_file:
        ip_file.write("\n".join(mpc_addresses).encode('utf-8'))
        ip_file.flush()

    # 4. Compile and run share_data_<client_id>.mpc
    circuit_name = prepare_data_sharing_program(client_id)
    compile_program(circuit_name)
    run_program(circuit_name, ip_file.name)

    # 5. Call /set_share_data_complete on coordination server
    set_complete_url = f"{coordination_server_url}/set_share_data_complete"
    set_complete_data = {"party_id": settings.party_id, "identity": request.identity}
    try:
        response = requests.post(set_complete_url, json=set_complete_data)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to set share data complete: {str(e)}")
        raise HTTPException(status_code=400, detail="Failed to set share data complete with coordination server")

    logger.info(f"Identity verified for party {client_id}")
    # Call verify_registration on coordination server
    # TODO: implement
    return ShareDataResponse(success=True, message="Data shared successfully")


@router.post("/query_computation", response_model=QueryComputationResponse)
def query_computation(request: QueryComputationRequest, db: Session = Depends(get_db)):
    logger.info(f"Querying computation {request.computation_index}")
    # TODO: implement
    return QueryComputationResponse(success=True, message="Computation queried successfully", computation_index=request.computation_index, computation_result="")


def prepare_data_sharing_program(client_id: int):
    # Generate share_data_<client_id>.mpc with template in program/share_data.mpc
    template_path = TEMPLATE_PROGRAM_DIR / "share_data.mpc"
    with open(template_path, "r") as template_file:
        program_content = template_file.read()
    circuit_name = f"share_data_{client_id}"
    target_program_path = MPSPDZ_PROGRAM_DIR / f"{circuit_name}.mpc"
    program_content = program_content.replace("{client_id}", str(client_id))
    with open(target_program_path, "w") as program_file:
        program_file.write(program_content)
    return circuit_name


def compile_program(circuit_name: str):
    # Compile share_data_<client_id>.mpc
    subprocess.run(
        f"cd {settings.mpspdz_project_root} && {CMD_COMPILE_MPC} {circuit_name}",
        check=True,
        shell=True,
    )


def run_program(circuit_name: str, ip_file_path: str):
    # Run share_data_<client_id>.mpc
    cmd_run_mpc = f"{CMD_RUN_MPC} -N {settings.num_parties} -p {settings.party_id} -OF . {circuit_name} -ip {ip_file_path}"
    return subprocess.run(
        f"cd {settings.mpspdz_project_root} && {cmd_run_mpc}",
        check=True,
        shell=True,
        capture_output=True,
        text=True
    )
