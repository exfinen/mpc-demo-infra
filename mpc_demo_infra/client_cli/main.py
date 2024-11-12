import argparse
import asyncio
from pathlib import Path
import json
import secrets

from ..client_lib.lib import fetch_parties_certs, share_data, query_computation, add_user_to_queue, poll_queue_until_ready
from .config import settings

# project_root/certs
PROJECT_ROOT = Path(__file__).parent.parent.parent
CERTS_PATH = Path(settings.certs_path)
TLSN_EXECUTABLE_DIR = Path(settings.tlsn_project_root) / "tlsn" / "examples" / "binance"

CMD_VERIFY_TLSN_PROOF = "cargo run --release --example binance_verifier"
CMD_GEN_TLSN_PROOF = "cargo run --release --example binance_prover"


async def notarize_and_share_data(eth_address: str, api_key: str, api_secret: str):
    print("Fetching party certificates...")
    await fetch_parties_certs(
        settings.party_web_protocol,
        CERTS_PATH,
        settings.party_hosts,
        settings.party_ports
    )
    print("Party certificates have been fetched and saved.")

    # Gen tlsn proofs
    print(f"Generating Binance ETH balance TLSN proof...")
    proof_file = PROJECT_ROOT / f"proof.json"
    secret_file = PROJECT_ROOT/ f"secret.json"
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

    print(f"Sharing Binance ETH balance data to MPC parties...")
    await add_user_to_queue(settings.coordination_server_url, eth_address, settings.poll_duration)
    computation_key = await poll_queue_until_ready(settings.coordination_server_url, eth_address, settings.poll_duration)
    # Share data
    await share_data(
        CERTS_PATH,
        settings.coordination_server_url,
        settings.party_hosts,
        eth_address,
        tlsn_proof,
        secret_input,
        nonce,
        computation_key,
    )
    print(f"Binance ETH balance data has been shared secretly to MPC parties.")


async def query_computation_and_verify():
    access_key = secrets.token_urlsafe(16)
    await add_user_to_queue(settings.coordination_server_url, access_key, settings.poll_duration)
    computation_key = await poll_queue_until_ready(settings.coordination_server_url, access_key, settings.poll_duration)

    print("Fetching party certificates...")
    await fetch_parties_certs(
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
        access_key,
        computation_key,
    )
    print(f"{results=}")


def notarize_and_share_data_cli():
    parser = argparse.ArgumentParser(description="Notarize and share data")
    parser.add_argument("eth_address", type=str, help="The voucher code")
    parser.add_argument("api_key", type=str, help="The API key")
    parser.add_argument("api_secret", type=str, help="The API secret")
    args = parser.parse_args()
    try:
        asyncio.run(notarize_and_share_data(args.eth_address, args.api_key, args.api_secret))
        print("Computation finished")
    except Exception as e:
        print(e)


def query_computation_and_verify_cli():
    try:
        asyncio.run(query_computation_and_verify())
        print("Computation finished")
    except Exception as e:
        print(e)
