from pydantic import BaseSettings
from typing import List

class Settings(BaseSettings):
    party_id: int = 0

    # Database settings
    database_url: str = f"sqlite:///./party_{party_id}.db"

    # Coordination server settings
    coordination_server_url: str = "http://localhost:8000"

    tlsn_project_root: str = "/Users/mhchia/projects/work/pse/tlsn"
    tlsn_verifier_path: str = f"{tlsn_project_root}/tlsn/examples/simple"

    tlsn_proofs_dir: str = f"tlsn_proofs"
    port: int = 8000
    mpc_port: int = 8010

    class Config:
        env_file = ".env"

settings = Settings()
