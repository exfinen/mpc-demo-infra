from pydantic import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Allowed IPs for access control
    allowed_ips: List[str] = ["192.168.1.100", "192.168.1.101"]

    # Database settings
    database_url: str = "sqlite:///./coordination.db"

    # API Keys for additional authentication (optional)
    api_keys: List[str] = ["your_api_key_1", "your_api_key_2"]

    mpc_port: int = 8010
    num_parties: int = 3

    # Party IPs
    party_ips: List[str] = ["localhost:6666", "localhost:6667", "localhost:6668"]
    class Config:
        env_file = ".env"

settings = Settings()
