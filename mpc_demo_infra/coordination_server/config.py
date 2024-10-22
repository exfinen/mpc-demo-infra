from pydantic import BaseSettings
from typing import List
from pathlib import Path

this_file_path = Path(__file__).parent.resolve()

class Settings(BaseSettings):
    num_parties: int = 3
    port: int = 8005

    # Allowed IPs for access control
    allowed_ips: List[str] = ["192.168.1.100", "192.168.1.101"]

    # Database settings
    database_url: str = "sqlite:///./coordination.db"

    tlsn_project_root: str = str(this_file_path.parent.parent.parent / "tlsn")

    # mpc-demo-infra/tlsn_proofs
    tlsn_proofs_dir: str = str(this_file_path.parent.parent / "tlsn_proofs")

    # API Keys for additional authentication (optional)
    api_keys: List[str] = ["your_api_key_1", "your_api_key_2"]

    # should specify a range for ports
    free_ports_start: int = 8010
    # including the end port
    free_ports_end: int = 8100

    party_web_protocol: str = "http"
    # Party IPs. Used to whitelist IPs that can access party-server-only APIs.
    party_hosts: List[str] = ["localhost", "localhost", "localhost"]
    party_ports: List[int] = [8006, 8007, 8008]

    class Config:
        env_file = ".env.coord"


settings = Settings()
