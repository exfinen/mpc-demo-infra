import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mpc_demo_infra.coordination_server.main import app
from mpc_demo_infra.coordination_server.database import Base, get_db, Voucher
from fastapi.testclient import TestClient

# Use a unique filename for each test run
TEST_DB_FILE = f"test_{os.getpid()}.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///./{TEST_DB_FILE}"

# Create engine and sessionmaker
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create database tables at the start of the test session and delete them at the end."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    os.remove(TEST_DB_FILE)

@pytest.fixture(scope="function")
def db_session():
    """Create a new database session for each test function and rollback the transaction after the test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def override_get_db(db_session):
    """Override FastAPI's get_db dependency to return the test database session."""
    def _override():
        yield db_session
    app.dependency_overrides[get_db] = _override
    yield
    app.dependency_overrides[get_db] = None

@pytest.fixture(scope="function")
def client(override_get_db):
    """Create a TestClient instance with the overridden dependency."""
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def create_voucher(db_session):
    """Create a Voucher instance and add it to the test database."""
    def _create_voucher(code="TEST_VOUCHER"):
        voucher = Voucher(code=code)
        db_session.add(voucher)
        db_session.commit()
        db_session.refresh(voucher)
        return voucher
    return _create_voucher

def test_register_with_valid_voucher(client, db_session, create_voucher):
    """Test registration using a valid Voucher."""
    voucher = create_voucher()

    # Verify that the Voucher exists in the database after creation
    db_voucher = db_session.query(Voucher).filter_by(code=voucher.code).first()
    assert db_voucher is not None, "Voucher not found in database after creation"

    response = client.post("/register", json={"voucher_code": voucher.code})

    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.content}")

    assert response.status_code == 200, f"Response: {response.json()}"
    assert "provider_id" in response.json()

    # Verify that the Voucher is marked as used
    db_voucher = db_session.query(Voucher).filter_by(code=voucher.code).first()
    assert db_voucher.data_provider is not None, "Voucher not marked as used after registration"
