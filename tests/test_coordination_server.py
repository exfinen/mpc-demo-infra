import os

import pytest
from sqlalchemy import create_engine
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from mpc_demo_infra.coordination_server.main import app
from mpc_demo_infra.coordination_server.database import Base, get_db, Voucher
from mpc_demo_infra.coordination_server.routes import (
    MPCStatus,
    indicated_joining_mpc, indicated_mpc_complete, is_data_sharing_in_progress
)
from mpc_demo_infra.coordination_server.config import settings

# Use a unique filename for each test run
TEST_DB_FILE = f"test_{os.getpid()}.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///./{TEST_DB_FILE}"

IDENTITY_1 = "test_identity_1"
IDENTITY_2 = "test_identity_2"

VOUCHER_CODE_1 = "test_voucher_code_1"
VOUCHER_CODE_2 = "test_voucher_code_2"

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
    def _create_voucher(code: str):
        voucher = Voucher(code=code)
        db_session.add(voucher)
        db_session.commit()
        db_session.refresh(voucher)
        return voucher
    return _create_voucher

def test_register_with_valid_voucher(client, db_session, create_voucher):
    """Test registration using a valid Voucher."""
    voucher = create_voucher(VOUCHER_CODE_1)

    # Verify that the Voucher exists in the database after creation
    db_voucher = db_session.query(Voucher).filter_by(code=voucher.code).first()
    assert db_voucher is not None, "Voucher not found in database after creation"

    response = client.post("/register", json={
        "voucher_code": voucher.code,
        "identity": IDENTITY_1
    })

    assert response.status_code == 200, f"Response: {response.json()}"
    assert "provider_id" in response.json()

    # Verify that the Voucher is marked as used
    db_voucher = db_session.query(Voucher).filter_by(code=voucher.code).first()
    assert db_voucher.data_provider is not None, "Voucher not marked as used after registration"


def test_register_with_invalid_voucher(client, db_session):
    """Test registration using an invalid Voucher."""
    another_identity = "test_identity_1"
    response = client.post("/register", json={
        "voucher_code": "INVALID_VOUCHER",
        "identity": another_identity
    })
    assert response.status_code == 400 and "Invalid voucher code" in response.json()["detail"], f"Response: {response.json()}"


def test_register_with_existing_identity(client, db_session, create_voucher):
    """Test registration with an existing identity."""

    # Create vouchers
    voucher1 = create_voucher(VOUCHER_CODE_1)
    voucher2 = create_voucher(VOUCHER_CODE_2)

    response = client.post("/register", json={
        "voucher_code": voucher1.code,
        "identity": IDENTITY_1
    })
    assert response.status_code == 200, f"Response: {response.json()}"

    # Attempt to register with an existing identity
    response = client.post("/register", json={
        "voucher_code": voucher2.code,
        "identity": IDENTITY_1
    })

    assert response.status_code == 400 and "Identity already exists" in response.json()["detail"], f"Response: {response.json()}"


def test_full_registration_and_verification_flow(client, db_session, create_voucher):
    voucher = create_voucher(VOUCHER_CODE_1)

    # Register
    register_response = client.post("/register", json={
        "voucher_code": voucher.code,
        "identity": IDENTITY_1
    })
    assert register_response.status_code == 200, f"Register Response: {register_response.json()}"

    # Verify
    verify_response = client.post("/verify_registration", json={
        "identity": IDENTITY_1
    })
    assert verify_response.status_code == 200, f"Verify Response: {verify_response.json()}"
    assert "client_id" in verify_response.json()
    assert isinstance(verify_response.json()["client_id"], int)

def test_verify_registration_success(client, db_session, create_voucher):
    # Create a voucher and register a data provider
    voucher = create_voucher(VOUCHER_CODE_1)
    register_response = client.post("/register", json={
        "voucher_code": voucher.code,
        "identity": IDENTITY_1
    })
    assert register_response.status_code == 200

    # Verify registration
    response = client.post("/verify_registration", json={"identity": IDENTITY_1})
    assert response.status_code == 200
    assert "client_id" in response.json()
    assert isinstance(response.json()["client_id"], int)

def test_verify_registration_nonexistent_identity(client, db_session):
    # Attempt to verify registration for non-existent identity
    response = client.post("/verify_registration", json={"identity": "nonexistent_identity"})
    assert response.status_code == 400
    assert "Identity not registered" in response.json()["detail"]

def test_verify_registration_multiple_providers(client, db_session, create_voucher):
    # Create vouchers and register multiple data providers
    voucher1 = create_voucher(VOUCHER_CODE_1)
    voucher2 = create_voucher(VOUCHER_CODE_2)

    client.post("/register", json={"voucher_code": voucher1.code, "identity": IDENTITY_1})
    client.post("/register", json={"voucher_code": voucher2.code, "identity": IDENTITY_2})

    # Verify registration for both providers
    response1 = client.post("/verify_registration", json={"identity": IDENTITY_1})
    response2 = client.post("/verify_registration", json={"identity": IDENTITY_2})

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json()["client_id"] != response2.json()["client_id"]


@pytest.fixture(autouse=True)
def reset_global_state():
    # Reset global state before each test
    indicated_joining_mpc.clear()
    indicated_mpc_complete.clear()
    is_data_sharing_in_progress.clear()


def test_check_share_data_status(client):
    response = client.get("/check_share_data_status")
    assert response.status_code == 200
    assert response.json() == {"status": MPCStatus.INITIAL.value}


def test_negotiate_share_data_first_party(client):
    response = client.post("/negotiate_share_data", json={"party_id": 1})
    assert response.json() == {"status": MPCStatus.WAITING_FOR_ALL_PARTIES.value, "port": settings.mpc_port}
    assert len(indicated_joining_mpc) == 1


def test_negotiate_share_data_last_party(client):
    # Simulate two parties already joined
    indicated_joining_mpc[1] = 0
    indicated_joining_mpc[2] = 0

    response = client.post("/negotiate_share_data", json={"party_id": 3})
    assert response.status_code == 200
    assert response.json() == {"status": MPCStatus.MPC_IN_PROGRESS.value, "port": settings.mpc_port}
    assert len(indicated_joining_mpc) == settings.num_parties
    assert is_data_sharing_in_progress.is_set()


def test_negotiate_share_data_already_in_progress(client):
    is_data_sharing_in_progress.set()
    response = client.post("/negotiate_share_data", json={"party_id": 1})
    assert response.status_code == 400
    assert "Data sharing already in progress" in response.json()["detail"]


def test_negotiate_share_data_party_already_joined(client):
    indicated_joining_mpc[1] = 0
    response = client.post("/negotiate_share_data", json={"party_id": 1})
    assert response.status_code == 400
    assert "Party already waiting" in response.json()["detail"]


def test_set_share_data_complete_success(client):
    # Simulate MPC in progress
    is_data_sharing_in_progress.set()
    indicated_joining_mpc[1] = 0
    indicated_joining_mpc[2] = 0
    indicated_joining_mpc[3] = 0

    response = client.post("/set_share_data_complete", json={"party_id": 1})
    assert response.status_code == 204
    assert 1 in indicated_mpc_complete


def test_set_share_data_complete_all_parties(client):
    # Simulate MPC in progress and two parties completed
    is_data_sharing_in_progress.set()
    indicated_joining_mpc[1] = 0
    indicated_joining_mpc[2] = 0
    indicated_joining_mpc[3] = 0
    indicated_mpc_complete[1] = 0
    indicated_mpc_complete[2] = 0

    response = client.post("/set_share_data_complete", json={"party_id": 3})
    assert response.status_code == 204
    assert len(indicated_joining_mpc) == 0
    assert len(indicated_mpc_complete) == 0
    assert not is_data_sharing_in_progress.is_set()


def test_set_share_data_complete_mpc_not_in_progress(client):
    response = client.post("/set_share_data_complete", json={"party_id": 1})
    assert response.status_code == 400
    assert "Cannot set share data complete: MPC is not in progress" in response.json()["detail"]


def test_get_current_state_initial(client):
    response = client.get("/check_share_data_status")
    assert response.status_code == 200
    assert response.json()["status"] == MPCStatus.INITIAL.value


def test_get_current_state_waiting_for_all_parties(client):
    indicated_joining_mpc[1] = 0
    response = client.get("/check_share_data_status")
    assert response.status_code == 200
    assert response.json()["status"] == MPCStatus.WAITING_FOR_ALL_PARTIES.value


def test_get_current_state_mpc_in_progress(client):
    is_data_sharing_in_progress.set()
    indicated_joining_mpc[1] = 0
    indicated_joining_mpc[2] = 0
    indicated_joining_mpc[3] = 0
    response = client.get("/check_share_data_status")
    assert response.status_code == 200
    assert response.json()["status"] == MPCStatus.MPC_IN_PROGRESS.value


def test_get_current_state_invalid_all_joined_not_in_progress(client):
    indicated_joining_mpc[1] = 0
    indicated_joining_mpc[2] = 0
    indicated_joining_mpc[3] = 0
    response = client.get("/check_share_data_status")
    assert response.status_code == 400
    assert "Invalid state: all parties have joined but MPC is not in progress" in response.json()["detail"]


def test_get_current_state_invalid_in_progress_not_all_joined(client):
    is_data_sharing_in_progress.set()
    indicated_joining_mpc[1] = 0
    indicated_joining_mpc[2] = 0
    response = client.get("/check_share_data_status")
    assert response.status_code == 400
    assert "Invalid state: MPC is in progress but not all parties have joined" in response.json()["detail"]


def test_get_current_state_invalid_completed_not_in_progress(client):
    indicated_mpc_complete[1] = 0
    response = client.get("/check_share_data_status")
    assert response.status_code == 400
    assert "Invalid state: parties have completed MPC but data sharing is not in progress" in response.json()["detail"]


def test_cleanup_stale_sessions(client):
    is_data_sharing_in_progress.set()
    indicated_joining_mpc[1] = 0
    indicated_mpc_complete[2] = 0

    response = client.post("/cleanup_sessions")
    assert response.status_code == 204

    response = client.get("/check_share_data_status")
    assert response.status_code == 200
    assert response.json()["status"] == MPCStatus.INITIAL.value
