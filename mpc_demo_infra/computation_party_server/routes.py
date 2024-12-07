import json
from concurrent.futures import ThreadPoolExecutor
import tempfile
import logging
import subprocess
from pathlib import Path
import shutil
from datetime import datetime
import asyncio
import os
import glob

import requests
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from .schemas import (
    GetPartyCertResponse,
    RequestSharingDataMPCRequest,
    RequestSharingDataMPCResponse,
    RequestQueryComputationMPCRequest,
    RequestQueryComputationMPCResponse,
)
from .database import get_db
from .config import settings
from .limiter import limiter
from ..constants import MAX_DATA_PROVIDERS

SHARE_DATA_ENDPOINT = "/request_sharing_data_mpc"
QUERY_COMPUTATION_ENDPOINT = "/request_querying_computation_mpc"

router = APIRouter()

# TLSN
CMD_VERIFY_TLSN_PROOF = "cargo run --release --example binance_verifier"
TLSN_VERIFIER_PATH = Path(settings.tlsn_project_root) / "tlsn" / "examples" / "binance"

# MP-SPDZ
MP_SPDZ_PROJECT_ROOT = Path(settings.mpspdz_project_root)
MPSPDZ_PROGRAM_DIR = MP_SPDZ_PROJECT_ROOT / "Programs" / "Source"
CERTS_PATH = MP_SPDZ_PROJECT_ROOT / "Player-Data"
CERTS_PATH.mkdir(parents=True, exist_ok=True)

TEMPLATE_PROGRAM_DIR = Path(__file__).parent.parent / "program"

SHARES_DIR = MP_SPDZ_PROJECT_ROOT / "Persistence"
SHARES_DIR.mkdir(parents=True, exist_ok=True)
BACKUP_SHARES_ROOT = MP_SPDZ_PROJECT_ROOT / "Backup"
BACKUP_SHARES_ROOT.mkdir(parents=True, exist_ok=True)
# To achieve program bits = 256, we need to use ring size = 257
# Ref: https://github.com/data61/MP-SPDZ/blob/894d38c748ab06a6eae8381f6b8c385cf0b2f5fa/Compiler/program.py#L277
CMD_COMPILE_MPC = f"./compile.py -R {settings.program_bits+1}"
MPC_VM_BINARY = f"{settings.mpspdz_protocol}-party.x"

@router.get("/get_party_cert", response_model=GetPartyCertResponse)
# @limiter.limit("1/minute")  # Override default limit for this route
def get_party_cert():
    party_id = settings.party_id
    cert_path = CERTS_PATH / f"P{party_id}.pem"
    with open(cert_path, "r") as cert_file:
        cert = cert_file.read()
    return GetPartyCertResponse(party_id=party_id, cert_file=cert)


@router.post(SHARE_DATA_ENDPOINT, response_model=RequestSharingDataMPCResponse)
def request_sharing_data_mpc(request: RequestSharingDataMPCRequest, db: Session = Depends(get_db)):
    secret_index = request.secret_index
    tlsn_proof = request.tlsn_proof
    mpc_port_base = request.mpc_port_base
    client_id = request.client_id
    client_port_base = request.client_port_base
    client_cert_file = request.client_cert_file
    logger.info(f"Requesting sharing data MPC for {secret_index=}")
    if secret_index >= MAX_DATA_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Secret index {secret_index} exceeds the maximum {MAX_DATA_PROVIDERS}")
    # 1. Verify TLSN proof
    with tempfile.NamedTemporaryFile() as temp_file:
        # Store TLSN proof in temporary file.
        temp_file.write(tlsn_proof.encode('utf-8'))

        # Run TLSN proof verifier
        try:
            subprocess.run(
                f"cd {str(TLSN_VERIFIER_PATH)} && {CMD_VERIFY_TLSN_PROOF} {temp_file.name}",
                check=True,
                shell=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to verify TLSN proof: {str(e)}")
            raise HTTPException(status_code=400, detail="Failed when verifying TLSN proof")

    # 2. Backup previous shares
    backup_shares_path = backup_shares(settings.party_id)
    logger.info(f"!@# backup_shares_path: {backup_shares_path}")
    logger.info(f"Backed up shares to {backup_shares_path}")

    # 3. Generate ip file
    ip_file_path = generate_ip_file(mpc_port_base)

    # 4. Generate client cert file
    clean_up_player_data_dir()
    generate_client_cert_file(client_id, client_cert_file)

    # 5. Fetch other parties' certs
    fetch_other_parties_certs()

    logger.info(f"Preparing data sharing program")
    num_bytes_input, tlsn_data_commitment_hash, tlsn_delta, tlsn_zero_encodings = extract_tlsn_proof_data(tlsn_proof)
    # Compile and run share_data program
    circuit_name, target_program_path = generate_data_sharing_program(
        secret_index,
        client_port_base,
        MAX_DATA_PROVIDERS,
        backup_shares_path is None,
        num_bytes_input,
        tlsn_delta,
        tlsn_zero_encodings,
    )
    logger.info(f"Compiling data sharing program {circuit_name}")
    compile_program(circuit_name)
    try:
        logger.info(f"Started computation: {circuit_name}")
        mpc_data_commitment_hash = run_data_sharing_program(circuit_name, ip_file_path)
    except Exception as e:
        logger.error(f"Computation {circuit_name} failed: {str(e)}")
        rollback_shares(settings.party_id, backup_shares_path)
        raise HTTPException(status_code=500, detail=str(e))

    logger.info(f"Verifying data commitment hash")
    # 3. Verify data commitment hash from TLSN proof and MPC matches or not. If not, rollback shares.
    logger.info(f"TLSN data commitment hash: {tlsn_data_commitment_hash}")
    logger.info(f"MPC data commitment hash: {mpc_data_commitment_hash}")
    # FIXME:
    # if mpc_data_commitment_hash != tlsn_data_commitment_hash:
    #     logger.error(f"Data commitment hash mismatch between TLSN proof and MPC. Rolling back shares to {backup_shares_path}")
    #     rollback_shares(settings.party_id, backup_shares_path)
    #     raise HTTPException(status_code=500, detail="Data commitment hash mismatch between TLSN proof and MPC")
    return RequestSharingDataMPCResponse(data_commitment=tlsn_data_commitment_hash)


@router.post(QUERY_COMPUTATION_ENDPOINT, response_model=RequestQueryComputationMPCResponse)
def request_querying_computation_mpc(request: RequestQueryComputationMPCRequest, db: Session = Depends(get_db)):
    mpc_port_base = request.mpc_port_base
    client_id = request.client_id
    client_port_base = request.client_port_base
    client_cert_file = request.client_cert_file
    num_data_providers = request.num_data_providers
    logger.info(f"Querying computation")

    shares_path = SHARES_DIR / f"Transactions-P{settings.party_id}.data"
    if not shares_path.exists():
        raise HTTPException(status_code=400, detail="No data available")

    # Prepare for IP file
    ip_file_path = generate_ip_file(mpc_port_base)

    # Generate client cert file
    clean_up_player_data_dir()
    generate_client_cert_file(client_id, client_cert_file)

    # Fetch other parties' certs
    fetch_other_parties_certs()

    circuit_name, target_program_path = generate_computation_query_program(
        client_port_base,
        MAX_DATA_PROVIDERS,
        num_data_providers,
    )

    logger.info(f"Compiling computation query program {circuit_name}")
    compile_program(circuit_name)
    logger.info(f"Started computation: {circuit_name}")
    try:
        run_computation_query_program(circuit_name, ip_file_path)
    except Exception as e:
        logger.error(f"Computation {circuit_name} failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    logger.info("MPC query computation finished")
    return RequestQueryComputationMPCResponse()


def generate_ip_file(mpc_port_base: int) -> str:
    # Prepare for IP file
    mpc_addresses = [
        f"{host}:{mpc_port_base + party_id}" for party_id, host in enumerate(settings.party_hosts)
    ]
    with tempfile.NamedTemporaryFile(delete=False) as ip_file:
        logger.info(f"Writing IP addresses to {ip_file.name}: {mpc_addresses}")
        ip_file.write("\n".join(mpc_addresses).encode('utf-8'))
        ip_file.flush()
    return ip_file.name


def clean_up_player_data_dir() -> None:
    logger.info(f"Cleaning up {CERTS_PATH}...")
    zero_files = glob.glob(os.path.join(CERTS_PATH, "*.0"))
    c_pem_files = glob.glob(os.path.join(CERTS_PATH, "C*.pem"))
    for file in zero_files + c_pem_files:
        try:
            os.remove(file)
            logger.info(f"Deleted: {file}")
        except Exception as e:
            logger.error(f"Failed to delete {file}: {e}")


def generate_client_cert_file(client_id: int, client_cert_file: str) -> Path:
    # Save client's cert file to CERTS_PATH
    client_cert_path = CERTS_PATH / f"C{client_id}.pem"
    with open(client_cert_path, "w") as cert_file:
        cert_file.write(client_cert_file)
    # c_rehash
    subprocess.run(
        f"c_rehash {CERTS_PATH}",
        check=True,
        shell=True,
    )
    logger.info(f"Created {client_cert_path} and called c_rehash {CERTS_PATH}")
    return client_cert_path


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
        # If there is no backup, it means it's the first run and failed.
        # So just unlink the current shares
        dest_path.unlink(missing_ok=True)
        return
    else:
        # else, copy the backup shares back
        shutil.copy(backup_path, dest_path)


def generate_data_sharing_program(
    secret_index: int,
    client_port_base: int,
    max_data_providers: int,
    is_first_run: bool,
    input_bytes: int,
    tlsn_delta: str,
    tlsn_zero_encodings: list[str]
) -> str:
    # Generate share_data_<client_id>.mpc with template in program/share_data.mpc
    template_path = TEMPLATE_PROGRAM_DIR / "share_data.mpc"
    with open(template_path, "r") as template_file:
        program_content = template_file.read()
    circuit_name = f"share_data_{secret_index}"
    target_program_path = MPSPDZ_PROGRAM_DIR / f"{circuit_name}.mpc"
    program_content = program_content.replace("{secret_index}", str(secret_index))
    program_content = program_content.replace("{client_port_base}", str(client_port_base))
    program_content = program_content.replace("{max_data_providers}", str(max_data_providers))
    program_content = program_content.replace("{input_bytes}", str(input_bytes))
    program_content = program_content.replace("{delta}", repr(tlsn_delta))
    program_content = program_content.replace("{zero_encodings}", repr(tlsn_zero_encodings))

    # Remove lines that contains '# NOTE: Skipped if it's the first run'
    if is_first_run:
        program_content = '\n'.join([line for line in program_content.split('\n') if "# NOTE: Skipped if it's the first run" not in line])

    with open(target_program_path, "w") as program_file:
        program_file.write(program_content)
    return circuit_name, target_program_path


def generate_computation_query_program(
    client_port_base: int,
    max_data_providers: int,
    num_data_providers: int,
) -> str:
    template_path = TEMPLATE_PROGRAM_DIR / "query_computation.mpc"
    with open(template_path, "r") as template_file:
        program_content = template_file.read()
    circuit_name = f"query_computation_{client_port_base}"
    target_program_path = MPSPDZ_PROGRAM_DIR / f"{circuit_name}.mpc"
    program_content = program_content.replace("{client_port_base}", str(client_port_base))
    program_content = program_content.replace("{max_data_providers}", str(max_data_providers))
    program_content = program_content.replace("{num_data_providers}", str(num_data_providers))
    with open(target_program_path, "w") as program_file:
        program_file.write(program_content)
    return circuit_name, target_program_path


def compile_program(circuit_name: str):
    # Compile share_data_<client_id>.mpc
    subprocess.run(
        f"cd {settings.mpspdz_project_root} && {CMD_COMPILE_MPC} {circuit_name}",
        check=True,
        shell=True,
    )


def run_program(circuit_name: str, ip_file_path: str):
    binary_path = Path(settings.mpspdz_project_root) / MPC_VM_BINARY
    if not binary_path.exists():
        # Build the binary if not exists
        raise Exception(f"Binary {binary_path} not found. Build it by running `make {MPC_VM_BINARY}` under {settings.mpspdz_project_root}")
    # Run share_data_<client_id>.mpc
    # cmd_run_mpc = f"./{MPC_VM_BINARY} -N {settings.num_parties} -p {settings.party_id} -OF . {circuit_name} -ip {str(ip_file_path)}"
    # ./replicated-ring-party.x -ip ip_rep -p 0 tutorial
    cmd_run_mpc = f"./{MPC_VM_BINARY} -ip {str(ip_file_path)} -p {settings.party_id} -OF . {circuit_name}"
    logger.info(f"Executing a program with {MPC_VM_BINARY}")
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
    else:
        logger.info(f"Successfully executed")

    return process


def run_data_sharing_program(circuit_name: str, ip_file_path: Path) -> list[str]:
    process = run_program(circuit_name, ip_file_path)
    output_lines = process.stdout.split('\n')

    commitments = []
    for line in output_lines:
        # Only get the commitments
        # Case for 'Reg[0] = 0x28059a08d116926177e4dfd87e72da4cd44966b61acc3f21870156b868b81e6a #'
        if line.startswith('Reg['):
            # 0xed7ec2253e5b9f15a2157190d87d4fd7f4949ab219978f9915d12c03674dd161
            after_equal = line.split('=')[1].strip()
            # ed7ec2253e5b9f15a2157190d87d4fd7f4949ab219978f9915d12c03674dd161
            reg_value = after_equal.split(' ')[0][2:]
            commitments.append(reg_value)
        # logger.error(f"!@# line: {line}")

    # for err in process.stderr.split('\n'):
    #     logger.error(f"!@# err: {err}")
    if len(commitments) != 1:
        raise ValueError(f"Expected 1 commitment, got {len(commitments)}")
    return commitments[0]


def run_computation_query_program(circuit_name: str, ip_file_path: Path) -> list[str]:
    return run_program(circuit_name, ip_file_path)
    # # 'Result of computation 0: 10'
    # output_lines = process.stdout.split('\n')
    # outputs = []
    # for line in output_lines:
    #     if line.startswith('Result of computation:'):
    #         outputs.append(line.split(',')[0].strip()[-1])
    #         outputs.append(line.split(',')[1].strip())
    #         outputs.append(line.split(',')[2].strip())
    #         outputs.append(line.split(',')[3].strip())
    # if len(outputs) != 4:
    #     raise ValueError(f"Expected 4 output, got {len(outputs)}")
    # return outputs


def extract_tlsn_proof_data(tlsn_proof: str):
    WORD_SIZE = 16
    WORDS_PER_LABEL = 8

    tlsn_proof = json.loads(tlsn_proof)
    private_openings = tlsn_proof["substrings"]["private_openings"]
    if len(private_openings) != 1:
        raise Exception(f"Expected 1 private opening, got {len(private_openings)}")
    commitment_index, openings = list(private_openings.items())[0]
    commitment_info, commitment = openings
    data_commitment_hash = bytes(commitment["hash"]).hex()
    # FIXME: `nonce` shouldn't be included in the proof
    # data_commitment_nonce = bytes(commitment["nonce"]).hex()

    encodings = tlsn_proof["encodings"]
    deltas = []
    zero_encodings = []
    num_bytes_input = len(encodings)
    for e in encodings:
        delta = e["U8"]["state"]["delta"]
        labels = e["U8"]["labels"]
        if len(delta) != WORD_SIZE:
            raise Exception(f"Expected {WORD_SIZE} bytes in delta, got {len(delta)}")
        delta_hex = bytes(delta).hex()
        deltas.append(delta_hex)
        if len(labels) != WORDS_PER_LABEL:
            raise Exception(f"Expected {WORDS_PER_LABEL} labels, got {len(labels)}")
        for l in labels:
            if len(l) != WORD_SIZE:
                raise Exception(f"Expected {WORD_SIZE} bytes in label, got {len(l)}")
            label_hex = bytes(l).hex()
            zero_encodings.append(label_hex)
    if len(zero_encodings) != WORDS_PER_LABEL * len(encodings):
        raise Exception(f"Expected {WORDS_PER_LABEL * len(encodings)} labels, got {len(zero_encodings)}")
    if not len(set(deltas)) == 1:
        raise Exception(f"Expected all deltas to be the same, got {deltas}")
    return num_bytes_input, data_commitment_hash, deltas[0], zero_encodings


def fetch_other_parties_certs():
    CERTS_PATH.mkdir(parents=True, exist_ok=True)

    def get_party_cert(host: str, port: int, party_id: int):
        url = f"{settings.party_web_protocol}://{host}:{port}/get_party_cert"
        logger.info(f"Fetching party cert from {host}:{port}")
        response = requests.get(url)
        if response.status_code != 200:
            logger.error(f"Failed to fetch party cert from {host}:{port}, text: {response.text}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch party cert from {host}:{port}, text: {response.text}")
        data = response.json()
        if data["party_id"] != party_id:
            logger.error(f"party_id mismatch, expected {party_id}, got {data['party_id']}")
            raise HTTPException(status_code=500, detail=f"Party ID mismatch, expected {party_id}, got {data['party_id']}")
        logger.info(f"Fetched party cert from {host}:{port}")
        (CERTS_PATH / f"P{party_id}.pem").write_text(data["cert_file"])
        logger.info(f"Saved party cert to {CERTS_PATH / f'P{party_id}.pem'}")

    with ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(get_party_cert, host, port, party_id)
            for party_id, (host, port) in enumerate(zip(settings.party_hosts, settings.party_ports))
            if party_id != settings.party_id
        ]
        for future in futures:
            future.result()
