from pydantic import BaseSettings
from pathlib import Path

this_file_path = Path(__file__).parent.resolve()

class Settings(BaseSettings):
    num_parties: int = 3
    party_id: int = 0
    program_bits: int = 256
    mpspdz_protocol: str = "replicated-ring"

    # Database settings
    database_url: str = f"sqlite:///./party_0.db"

    # Coordination server settings
    coordination_server_url: str = "http://localhost:8005"
    party_api_key: str = "1234567890"

    # ../../../tlsn
    tlsn_project_root: str = str(this_file_path.parent.parent.parent / "tlsn")

    port: int = 8006
    party_hosts: list[str] = ["localhost", "localhost", "localhost"]
    mpspdz_project_root: str = str(this_file_path.parent.parent.parent / "MP-SPDZ")

    class Config:
        env_file = ".env.party"

settings = Settings()
