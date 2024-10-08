from pydantic import BaseSettings

class Settings(BaseSettings):
    num_parties: int = 3
    party_id: int = 0

    # Database settings
    database_url: str = f"sqlite:///./party_{party_id}.db"

    # Coordination server settings
    coordination_server_url: str = "http://localhost:8000"

    tlsn_project_root: str = "/Users/mhchia/projects/work/pse/tlsn"

    tlsn_proofs_dir: str = f"tlsn_proofs"

    server_port: int = 8000
    party_ips: list[str] = ["localhost", "localhost", "localhost"]
    mpspdz_project_root: str = "/Users/mhchia/projects/work/pse/MP-SPDZ"

    class Config:
        env_file = ".env"

settings = Settings()
