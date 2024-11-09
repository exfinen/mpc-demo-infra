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


# ORM
class Voucher(Base):
    __tablename__ = "vouchers"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    is_used = Column(Boolean, default=False)

    def __repr__(self):
        return f"Voucher(id={self.id}, code={self.code}, is_used={self.is_used})"

# MPC Session
class MPCSession(Base):
    __tablename__ = "mpc_sessions"

    id = Column(Integer, primary_key=True, index=True)
    voucher_code = Column(String, unique=True, index=True, nullable=False)
    tlsn_proof_path = Column(String, nullable=False)


def create_tables():
    """Create database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully for coordination server")
