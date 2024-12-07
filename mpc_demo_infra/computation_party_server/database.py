# mpc_demo_infra/coordination_server/database_models.py

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy import create_engine
from .config import settings
import logging

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    future=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=True, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DataProvider(Base):
    """
    Data provider table to keep track of data providers that have registered,
    and the voucher they used to register, and whether they have provided data yet.
    """
    __tablename__ = "data_providers"

    id = Column(Integer, primary_key=True, index=True)
    data_provider_id = Column(Integer, nullable=False)
    tlsn_proof_path = Column(String, nullable=False)


def create_tables():
    """Create database tables"""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully for coordination server")
