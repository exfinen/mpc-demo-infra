from pydantic import BaseSettings
from pathlib import Path

this_file_path = Path(__file__).parent.resolve()

class Settings(BaseSettings):
    num_parties: int = 3
    party_id: int = 0
    program_bits: int = 256
    mpspdz_protocol: str = "malicious-rep-ring"

    # Database settings
    database_url: str = f"sqlite:///./party_0.db"

    # Coordination server settings
    coordination_server_url: str = "http://localhost:8005"
    # API key that coordination server uses in order to be able to access
    # `request_sharing_data_mpc` and `request_querying_computation_mpc` endpoints.
    # In production, we need https to protect the API key from being exposed.
    party_api_key: str = "1234567890"

    # ../../../tlsn
    tlsn_project_root: str = str(this_file_path.parent.parent.parent / "tlsn")

    port: int = 8006
    party_web_protocol: str = "http"
    party_hosts: list[str] = ["localhost", "localhost", "localhost"]
    party_ports: list[int] = [8006, 8007, 8008]
    mpspdz_project_root: str = str(this_file_path.parent.parent.parent / "MP-SPDZ")

    fullchain_pem_path: str = "ssl_certs/fullchain.pem"
    privkey_pem_path: str = "ssl_certs/privkey.pem"

    # logging
    max_bytes_mb = 20
    backup_count = 10
    
    # Debug flags
    perform_commitment_check: bool = False

    class Config:
        env_file = ".env.party"

settings = Settings()
