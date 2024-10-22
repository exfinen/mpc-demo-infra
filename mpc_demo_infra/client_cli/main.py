import argparse
import asyncio
from pathlib import Path

from ..client_lib.lib import get_parties_certs, get_party_cert_path, share_data, query_computation
from .config import settings

# project_root/certs
PROJECT_ROOT = Path(__file__).parent.parent.parent
CERTS_PATH = Path(settings.certs_path)
TLSN_EXECUTABLE_DIR = Path(settings.tlsn_project_root) / "tlsn" / "examples" / "simple"

CMD_VERIFY_TLSN_PROOF = "cargo run --release --example simple_verifier"
CMD_GEN_TLSN_PROOF = "cargo run --release --example simple_prover"

DATA_TYPE = 0


async def notarize_and_share_data(voucher_code: str):
    num_parties = len(settings.party_hosts)
    CERTS_PATH.mkdir(parents=True, exist_ok=True)
    all_certs_exist = all(get_party_cert_path(CERTS_PATH, party_id).exists() for party_id in range(num_parties))
    if not all_certs_exist:
        print("Some party certificates are missing. Fetching them...")
        await get_parties_certs(
            settings.party_web_protocol,
            CERTS_PATH,
            settings.party_hosts,
            settings.party_ports
        )
        print("Party certificates have been fetched and saved.")

    # Gen tlsn proofs
    proof_file = PROJECT_ROOT / f"proof.json"
    process = await asyncio.create_subprocess_shell(
        f"cd {TLSN_EXECUTABLE_DIR} && {CMD_GEN_TLSN_PROOF} {DATA_TYPE} {str(proof_file.resolve())}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise Exception(f"TLSN proof generation failed with return code {process.returncode}, {stdout=}, {stderr=}")
    secret_input_line = next((line for line in stdout.decode().splitlines() if line.startswith(f"Party {DATA_TYPE} has ")), None)
    if not secret_input_line:
        raise ValueError(f"Could not find line for secret input")
    secret_input = int(secret_input_line.split()[3])
    with open(proof_file, "r") as f:
        tlsn_proof = f.read()

    # FIXME: `nonce` shouldn't be included in the proof
    # Should be changed when we're using newer version of tlsn
    def get_nonce_from_tlsn_proof(tlsn_proof: str):
        import json
        tlsn_proof = json.loads(tlsn_proof)
        private_openings = tlsn_proof["substrings"]["private_openings"]
        if len(private_openings) != 1:
            raise Exception(f"Expected 1 private opening, got {len(private_openings)}")
        commitment_index, openings = list(private_openings.items())[0]
        commitment_info, commitment = openings
        data_commitment_hash = bytes(commitment["hash"]).hex()
        data_commitment_nonce = bytes(commitment["nonce"]).hex()
        return data_commitment_hash, data_commitment_nonce
    _, nonce = get_nonce_from_tlsn_proof(tlsn_proof)
    # Share data
    await share_data(
        CERTS_PATH,
        settings.coordination_server_url,
        settings.party_hosts,
        voucher_code,
        tlsn_proof,
        secret_input,
        nonce,
    )


async def query_computation_and_verify(
    computation_index: int,
):
    num_parties = len(settings.party_hosts)
    CERTS_PATH.mkdir(parents=True, exist_ok=True)
    all_certs_exist = all(get_party_cert_path(CERTS_PATH, party_id).exists() for party_id in range(num_parties))
    if not all_certs_exist:
        print("Some party certificates are missing. Fetching them...")
        await get_parties_certs(
            settings.party_web_protocol,
            CERTS_PATH,
            settings.party_hosts,
            settings.party_ports
        )
        print("Party certificates have been fetched and saved.")
    results = await query_computation(
        CERTS_PATH,
        settings.coordination_server_url,
        settings.party_hosts,
        computation_index,
    )
    print(f"{results=}")


def notarize_and_share_data_cli():
    parser = argparse.ArgumentParser(description="Notarize and share data")
    parser.add_argument("voucher_code", type=str, help="The voucher code")
    args = parser.parse_args()
    asyncio.run(notarize_and_share_data(args.voucher_code))


def query_computation_and_verify_cli():
    parser = argparse.ArgumentParser(description="Query computation and verify results")
    parser.add_argument("computation_index", type=int, help="The computation index")
    args = parser.parse_args()
    asyncio.run(query_computation_and_verify(args.computation_index))
