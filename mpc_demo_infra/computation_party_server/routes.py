import json
import tempfile
import logging
import subprocess
from pathlib import Path
import shutil
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from .schemas import (
    RequestSharingDataMPCRequest,
    RequestSharingDataMPCResponse,
    QueryComputationRequest,
    QueryComputationResponse,
    RequestCertResponse,
)
from .database import get_db
from .config import settings

router = APIRouter()

# TLSN
CMD_VERIFYTLSN_PROOF = "cargo run --release --example simple_verifier"
TLSN_VERIFIER_PATH = Path(settings.tlsn_project_root) / "tlsn" / "examples" / "simple"

# MP-SPDZ
MP_SPDZ_PROJECT_ROOT = Path(settings.mpspdz_project_root)
MPSPDZ_PROGRAM_DIR = MP_SPDZ_PROJECT_ROOT / "Programs" / "Source"
CLIENT_CERT_PATH = MP_SPDZ_PROJECT_ROOT / "Player-Data"

TEMPLATE_PROGRAM_DIR = Path(__file__).parent.parent / "program"

SHARES_DIR = MP_SPDZ_PROJECT_ROOT / "Persistence"
BACKUP_SHARES_ROOT = MP_SPDZ_PROJECT_ROOT / "Backup"
CMD_COMPILE_MPC = "./compile.py -F 256"
CMD_RUN_MPC = f"./semi-party.x"


@router.post("/request_cert", response_model=RequestCertResponse)
def request_cert():
    with open(CLIENT_CERT_PATH / f"P{settings.party_id}.pem", "r") as cert_file:
        cert_file_content = cert_file.read()
    return RequestCertResponse(cert_file=cert_file_content)


@router.post("/request_sharing_data_mpc", response_model=RequestSharingDataMPCResponse)
def request_sharing_data_mpc(request: RequestSharingDataMPCRequest, db: Session = Depends(get_db)):
    secret_index = request.secret_index
    tlsn_proof = request.tlsn_proof
    mpc_port_base = request.mpc_port_base
    client_id = request.client_id
    client_port = request.client_port
    client_cert_file = request.client_cert_file
    logger.info(f"Requesting sharing data MPC for {secret_index=}")
    # 1. Verify TLSN proof
    with tempfile.NamedTemporaryFile() as temp_file:
        # Store TLSN proof in temporary file.
        temp_file.write(tlsn_proof.encode('utf-8'))

        # Run TLSN proof verifier
        try:
            subprocess.run(
                f"cd {str(TLSN_VERIFIER_PATH)} && {CMD_VERIFYTLSN_PROOF} {temp_file.name}",
                check=True,
                shell=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to verify TLSN proof: {str(e)}")
            raise HTTPException(status_code=400, detail="Failed when verifying TLSN proof")
    # 2. Backup previous shares
    backup_shares_path = backup_shares(settings.party_id)
    logger.debug(f"Backed up shares to {backup_shares_path}")

    # Prepare for IP file
    mpc_addresses = [
        f"{ip}:{mpc_port_base + party_id}" for party_id, ip in enumerate(settings.party_ips)
    ]
    with tempfile.NamedTemporaryFile(delete=False) as ip_file:
        logger.debug(f"Writing IP addresses to {ip_file.name}: {mpc_addresses}")
        ip_file.write("\n".join(mpc_addresses).encode('utf-8'))
        ip_file.flush()

    # Save client's cert file to CLIENT_CERT_PATH
    client_cert_path = CLIENT_CERT_PATH / f"C{client_id}.pem"
    with open(client_cert_path, "w") as cert_file:
        cert_file.write(client_cert_file)

    # c_rehash
    subprocess.run(
        f"c_rehash {CLIENT_CERT_PATH}",
        check=True,
        shell=True,
    )

    logger.debug(f"Preparing data sharing program")
    # Compile and run share_data program
    circuit_name = prepare_data_sharing_program(secret_index, client_port, settings.max_data_providers, backup_shares_path is None)
    logger.debug(f"Compiling data sharing program {circuit_name}")
    compile_program(circuit_name)
    try:
        logger.debug(f"Running program {circuit_name}")
        mpc_data_commitment_hash = run_data_sharing_program(circuit_name, ip_file.name)
    except Exception as e:
        logger.error(f"Failed to run program {circuit_name}: {str(e)}")
        rollback_shares(settings.party_id, backup_shares_path)
        raise HTTPException(status_code=500, detail=str(e))
    logger.debug(f"Commitment: {mpc_data_commitment_hash}")

    logger.debug(f"Verifying data commitment hash")
    # 3. Verify data commitment hash from TLSN proof and MPC matches or not. If not, rollback shares.
    tlsn_data_commitment_hash = get_data_commitment_hash_from_tlsn_proof(tlsn_proof)
    logger.debug(f"TLSN data commitment hash: {tlsn_data_commitment_hash}")
    logger.debug(f"MPC data commitment hash: {mpc_data_commitment_hash}")
    if mpc_data_commitment_hash != tlsn_data_commitment_hash:
        logger.error(f"Data commitment hash mismatch between TLSN proof and MPC. Rolling back shares to {backup_shares_path}")
        rollback_shares(settings.party_id, backup_shares_path)
        raise HTTPException(status_code=500, detail="Data commitment hash mismatch between TLSN proof and MPC")
    return RequestSharingDataMPCResponse(data_commitment=tlsn_data_commitment_hash)


def get_data_commitment_hash_from_tlsn_proof(tlsn_proof: str) -> str:
    proof_data = json.loads(tlsn_proof)
    private_openings = proof_data["substrings"]["private_openings"]
    if len(private_openings) != 1:
        raise ValueError(f"Expected 1 private opening, got {len(private_openings)}")
    _, openings = list(private_openings.items())[0]
    commitment = openings[1]
    data_commitment_hash = bytes(commitment["hash"]).hex()
    return data_commitment_hash


@router.post("/query_computation", response_model=QueryComputationResponse)
def query_computation(request: QueryComputationRequest, db: Session = Depends(get_db)):
    logger.info(f"Querying computation {request.computation_index}")
    # TODO: implement
    return QueryComputationResponse(success=True, message="Computation queried successfully", computation_index=request.computation_index, computation_result="")


def get_backup_shares_dir(party_id: int):
    dir = BACKUP_SHARES_ROOT / str(party_id)
    dir.mkdir(parents=True, exist_ok=True)
    return dir


def backup_shares(party_id: int) -> Path | None:
    # Persistence/Transactions-P{party_id}.data
    source_path = SHARES_DIR / f"Transactions-P{party_id}.data"
    if not source_path.exists():
        return None
    dir = get_backup_shares_dir(party_id)
    # TODO: probably should use "MPC_SESSION_ID" instead of time.
    # but we need to store MPC_SESSION ahead.
    # Get current timestamp
    current_time = datetime.now()

    # Format the timestamp
    timestamp = current_time.strftime("%Y-%m-%d-%H-%M-%S")
    # Current shares path
    # Use the timestamp in your file name
    dest_path = dir / f"Transactions-P{party_id}.data.{timestamp}"
    # Copy the file to the new location
    shutil.copy(source_path, dest_path)
    return dest_path


def rollback_shares(party_id: int, backup_path: Path | None):
    dest_path = SHARES_DIR / f"Transactions-P{party_id}.data"
    if backup_path is None:
        # If there is no backup, just unlink the current shares
        dest_path.unlink()
        return
    else:
        # else, copy the backup shares back
        shutil.copy(backup_path, dest_path)


def prepare_data_sharing_program(secret_index: int, client_port: int, max_data_providers: int, is_first_run: bool):
    # Generate share_data_<client_id>.mpc with template in program/share_data.mpc
    template_path = TEMPLATE_PROGRAM_DIR / "share_data.mpc"
    with open(template_path, "r") as template_file:
        program_content = template_file.read()
    circuit_name = f"share_data_{secret_index}"
    target_program_path = MPSPDZ_PROGRAM_DIR / f"{circuit_name}.mpc"
    program_content = program_content.replace("{secret_index}", str(secret_index))
    program_content = program_content.replace("{client_port}", str(client_port))
    program_content = program_content.replace("{max_data_providers}", str(max_data_providers))
    if is_first_run:
        # Remove lines that contains '# NOTE: Skipped if it's the first run'
        program_content = '\n'.join([line for line in program_content.split('\n') if "# NOTE: Skipped if it's the first run" not in line])
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

    # Run the MPC program
    try:
        process = subprocess.run(
            f"cd {settings.mpspdz_project_root} && {cmd_run_mpc}",
            shell=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        raise e
    if process.returncode != 0:
        raise Exception(f"!@# Failed to run program {circuit_name}: {process.stdout}, {process.stderr}")
    return process


def run_data_sharing_program(circuit_name: str, ip_file_path: str) -> list[str]:
    process = run_program(circuit_name, ip_file_path)
    output_lines = process.stdout.split('\n')

    outputs = []
    OUTPUT_PREFIX = "output: "
    commitments = []
    for line in output_lines:
        # if line.startswith(OUTPUT_PREFIX):
        #     outputs.append(float(line[len(OUTPUT_PREFIX):].strip()))
        # Case for 'Reg[0] = 0x28059a08d116926177e4dfd87e72da4cd44966b61acc3f21870156b868b81e6a #'
        if line.startswith('Reg['):
            # 0xed7ec2253e5b9f15a2157190d87d4fd7f4949ab219978f9915d12c03674dd161
            after_equal = line.split('=')[1].strip()
            # ed7ec2253e5b9f15a2157190d87d4fd7f4949ab219978f9915d12c03674dd161
            reg_value = after_equal.split(' ')[0][2:]
            commitments.append(reg_value)
        print(f"!@# line: {line}")

    for err in process.stderr.split('\n'):
        print(f"!@# err: {err}")
    if len(commitments) != 1:
        raise ValueError(f"Expected 1 commitment, got {len(commitments)}")
    # if len(outputs) != 1:
    #     raise ValueError(f"Expected 1 output, got {len(outputs)}")
    return commitments[0]
