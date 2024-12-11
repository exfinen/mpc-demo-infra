from pydantic import BaseSettings
from pathlib import Path

this_file_path = Path(__file__).parent.resolve()

class Settings(BaseSettings):
    # Coordination server settings
    coordination_server_url: str = "http://localhost:8005"
    notary_server_host: str = "notary.mpcstats.org"
    notary_server_port: int = 8003

    # mpc-demo-infra/certs
    certs_path: str = str(this_file_path.parent.parent / "certs")
    # ../../../tlsn
    tlsn_project_root: str = str(this_file_path.parent.parent.parent / "tlsn")

    party_web_protocol: str = "http"
    party_hosts: list[str] = ["localhost", "localhost", "localhost"]
    party_ports: list[int] = [8006, 8007, 8008]

    # logging
    max_bytes_mb = 20
    backup_count = 10
    
    class Config:
        env_file = ".env.client_cli"

    poll_duration: int = 10

settings = Settings()
