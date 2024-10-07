# mpc_demo_infra/coordination_server/database_models.py

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
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
    data_provider = relationship("DataProvider", back_populates="voucher", uselist=False)

    def __repr__(self):
        return f"Voucher(id={self.id}, code={self.code})"


class DataProvider(Base):
    """
    Data provider table to keep track of data providers that have registered,
    and the voucher they used to register, and whether they have provided data yet.
    """
    __tablename__ = "data_providers"

    id = Column(Integer, primary_key=True, index=True)
    has_provided_data = Column(Boolean, default=False)
    identity = Column(String, nullable=False, unique=True)
    voucher = relationship("Voucher", back_populates="data_provider", uselist=False)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), nullable=False, unique=True)

    def __repr__(self):
        return f"DataProvider(id={self.id}, identity={self.identity}, has_provided_data={self.has_provided_data})"


def create_tables():
    """Create database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully for coordination server")
