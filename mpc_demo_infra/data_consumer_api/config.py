from pydantic import BaseSettings
from pathlib import Path

this_file_path = Path(__file__).parent.resolve()

class Settings(BaseSettings):
    port: int = 8004
    # Coordination server settings
    coordination_server_url: str = "http://localhost:8005"

    # mpc-demo-infra/certs
    certs_path: str = str(this_file_path.parent.parent / "certs")
    # ../../../tlsn
    tlsn_project_root: str = str(this_file_path.parent.parent.parent / "tlsn")

    party_web_protocol: str = "http"
    party_hosts: list[str] = ["localhost", "localhost", "localhost"]
    party_ports: list[int] = [8006, 8007, 8008]

    fullchain_pem_path: str = "ssl_certs/fullchain.pem"
    privkey_pem_path: str = "ssl_certs/privkey.pem"

    poll_duration: int = 30

    class Config:
        env_file = ".env.consumer_api"

settings = Settings()
