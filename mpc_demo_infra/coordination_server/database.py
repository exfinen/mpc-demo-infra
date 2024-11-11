# mpc_demo_infra/coordination_server/database_models.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from .config import settings
from sqlalchemy.sql import func

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


# MPC Session
class MPCSession(Base):
    __tablename__ = "mpc_sessions"

    id = Column(Integer, primary_key=True, index=True)
    eth_address = Column(String, index=True, nullable=False)
    uid = Column(Integer, index=True, nullable=False)
    tlsn_proof_path = Column(String, nullable=False)


def create_tables():
    """Create database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully for coordination server")
