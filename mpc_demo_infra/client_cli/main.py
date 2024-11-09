import argparse
import asyncio
from pathlib import Path
import json

from ..client_lib.lib import get_parties_certs, get_party_cert_path, share_data, query_computation
from .config import settings

# project_root/certs
PROJECT_ROOT = Path(__file__).parent.parent.parent
CERTS_PATH = Path(settings.certs_path)
TLSN_EXECUTABLE_DIR = Path(settings.tlsn_project_root) / "tlsn" / "examples" / "binance"

CMD_VERIFY_TLSN_PROOF = "cargo run --release --example binance_verifier"
CMD_GEN_TLSN_PROOF = "cargo run --release --example binance_prover"

async def notarize_and_share_data(voucher_code: str, api_key: str, api_secret: str):
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
    secret_file = PROJECT_ROOT/ f"secret.json"
    print(f"Generating binance ETH balance TLSN proof...")
    process = await asyncio.create_subprocess_shell(
        f"cd {TLSN_EXECUTABLE_DIR} && {CMD_GEN_TLSN_PROOF} {settings.notary_server_host} {settings.notary_server_port} {api_key} {api_secret} {str(proof_file.resolve())} {str(secret_file.resolve())}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise Exception(f"TLSN proof generation failed with return code {process.returncode}, {stdout=}, {stderr=}")
    with open(proof_file, "r") as f:
        tlsn_proof = f.read()
    with open(secret_file, "r") as f_secret:
        secret_data = json.load(f_secret)
        secret_input = float(secret_data["eth_free"])
        nonce = bytes(secret_data["nonce"]).hex()

    print(f"Sharing binance ETH balance data to MPC parties...")
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
    print(f"Binance ETH balance data has been shared secretly to MPC parties.")


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
    parser.add_argument("api_key", type=str, help="The API key")
    parser.add_argument("api_secret", type=str, help="The API secret")
    args = parser.parse_args()
    asyncio.run(notarize_and_share_data(args.voucher_code, args.api_key, args.api_secret))


def query_computation_and_verify_cli():
    parser = argparse.ArgumentParser(description="Query computation and verify results")
    parser.add_argument("computation_index", type=int, help="The computation index")
    args = parser.parse_args()
    asyncio.run(query_computation_and_verify(args.computation_index))
