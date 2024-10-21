from pydantic import BaseSettings
from pathlib import Path

this_file_path = Path(__file__).parent

class Settings(BaseSettings):
    num_parties: int = 3
    party_id: int = 0
    max_data_providers: int = 10

    # Database settings
    database_url: str = f"sqlite:///./party_0.db"

    # Coordination server settings
    coordination_server_url: str = "http://localhost:8000"

    # ../../tlsn_
    tlsn_project_root: str = str(this_file_path.parent.parent.parent / "tlsn")


    tlsn_proofs_dir: str = f"tlsn_proofs"

    port: int = 8006
    party_ips: list[str] = ["localhost", "localhost", "localhost"]
    mpspdz_project_root: str = str(this_file_path.parent.parent.parent / "MP-SPDZ")

    class Config:
        env_file = ".env"

settings = Settings()
