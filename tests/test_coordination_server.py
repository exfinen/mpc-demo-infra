import os
import pytest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy import create_engine
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from pathlib import Path

from mpc_demo_infra.coordination_server.main import app
from mpc_demo_infra.coordination_server.database import Base, get_db, Voucher, DataProvider
from mpc_demo_infra.coordination_server.config import settings

# Use a unique filename for each test run
TEST_DB_FILE = f"test_{os.getpid()}.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///./{TEST_DB_FILE}"

IDENTITY_1 = "test_identity_1"
IDENTITY_2 = "test_identity_2"

VOUCHER_CODE_1 = "test_voucher_code_1"
VOUCHER_CODE_2 = "test_voucher_code_2"

MOCK_TLSN_PROOF = '{"substrings": {"private_openings": {"0": [0, {"hash": [0, 1, 2, 3]}]}}}'

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

@pytest.mark.asyncio
async def test_share_data_with_registered_identity(tmp_path, client, db_session, create_voucher):
    """Test sharing data with a registered identity."""
    # First, register the identity
    voucher = create_voucher(VOUCHER_CODE_1)
    client.post("/register", json={
        "voucher_code": voucher.code,
        "identity": IDENTITY_1
    })

    data_provider: DataProvider | None = db_session.query(DataProvider).filter(DataProvider.identity == IDENTITY_1).first()
    assert data_provider is not None, "Data provider not found in database after registration"
    client_id = data_provider.id

    # Mock tlsn_proofs_dir and thus we know if share_data succeeds, tlsn_proof is saved at the path.
    expected_tlsn_dir = tmp_path / "tlsn_proofs"
    settings.tlsn_proofs_dir = str(expected_tlsn_dir)
    expected_tlsn_dir.mkdir(parents=True, exist_ok=True)
    expected_tlsn_proof = expected_tlsn_dir / f"proof_{client_id}.json"

    # Mock the TLSN proof verification process
    with patch('asyncio.create_subprocess_shell', new_callable=AsyncMock) as mock_subprocess:
        mock_subprocess.return_value.communicate.return_value = (b'', b'')
        mock_subprocess.return_value.returncode = 0

        # Mock the aiohttp ClientSession
        with patch('aiohttp.ClientSession') as mock_session:
            mock_post = AsyncMock()
            mock_session.return_value.__aenter__.return_value.post = mock_post

            # Create mock responses with different data commitments
            same_commitment = "commitment1"
            mock_responses = [
                AsyncMock(status=200, json=AsyncMock(return_value={"data_commitment": same_commitment})),
                AsyncMock(status=200, json=AsyncMock(return_value={"data_commitment": same_commitment})),
                AsyncMock(status=200, json=AsyncMock(return_value={"data_commitment": same_commitment}))
            ]
            mock_post.side_effect = mock_responses
            # Mock get_data_commitment_hash_from_tlsn_proof to return the same commitment
            with patch('mpc_demo_infra.coordination_server.routes.get_data_commitment_hash_from_tlsn_proof', return_value=same_commitment):
                response = client.post("/share_data", json={
                    "identity": IDENTITY_1,
                    "tlsn_proof": MOCK_TLSN_PROOF
                })

    assert response.status_code == 200, f"Response: {response.json()}"
    assert "mpc_port_base" in response.json()
    assert "client_port" in response.json()
    assert expected_tlsn_proof.exists(), "Expected TLSN proof file not found"

def test_share_data_with_unregistered_identity(client, db_session):
    """Test sharing data with an unregistered identity."""
    response = client.post("/share_data", json={
        "identity": "unregistered_identity",
        "tlsn_proof": MOCK_TLSN_PROOF
    })

    assert response.status_code == 400 and "Identity not registered" in response.json()["detail"], f"Response: {response.json()}"

@pytest.mark.asyncio
async def test_share_data_with_invalid_tlsn_proof(client, db_session, create_voucher):
    """Test sharing data with an invalid TLSN proof."""
    # First, register the identity
    voucher = create_voucher(VOUCHER_CODE_1)
    client.post("/register", json={
        "voucher_code": voucher.code,
        "identity": IDENTITY_1
    })

    # Mock the TLSN proof verification process to fail
    with patch('asyncio.create_subprocess_shell', new_callable=AsyncMock) as mock_subprocess:
        mock_subprocess.return_value.communicate.return_value = (b'', b'Verification failed')
        mock_subprocess.return_value.returncode = 1

        # Now attempt to share data with invalid proof
        response = client.post("/share_data", json={
            "identity": IDENTITY_1,
            "tlsn_proof": "invalid_proof"
        })

    assert response.status_code == 400 and "TLSN proof verification failed" in response.json()["detail"], f"Response: {response.json()}"

@pytest.mark.asyncio
async def test_share_data_with_mismatched_data_commitments_from_parties(tmp_path, client, db_session, create_voucher):
    """Test sharing data with mismatched data commitments from different parties."""
    # First, register the identity
    voucher = create_voucher(VOUCHER_CODE_1)
    client.post("/register", json={
        "voucher_code": voucher.code,
        "identity": IDENTITY_1
    })

    data_provider: DataProvider | None = db_session.query(DataProvider).filter(DataProvider.identity == IDENTITY_1).first()
    assert data_provider is not None, "Data provider not found in database after registration"
    client_id = data_provider.id

    # Mock tlsn_proofs_dir and thus we know if share_data succeeds, tlsn_proof is saved at the path.
    expected_tlsn_dir = tmp_path / "tlsn_proofs"
    settings.tlsn_proofs_dir = str(expected_tlsn_dir)
    expected_tlsn_dir.mkdir(parents=True, exist_ok=True)
    expected_tlsn_proof = expected_tlsn_dir / f"proof_{client_id}.json"

    # Mock the TLSN proof verification process
    with patch('asyncio.create_subprocess_shell', new_callable=AsyncMock) as mock_subprocess:
        mock_subprocess.return_value.communicate.return_value = (b'', b'')
        mock_subprocess.return_value.returncode = 0

        # Mock the aiohttp ClientSession to return different data commitments
        with patch('aiohttp.ClientSession') as mock_session:
            mock_post = AsyncMock()
            mock_session.return_value.__aenter__.return_value.post = mock_post

            # Create mock responses with different data commitments
            mock_responses = [
                AsyncMock(status=200, json=AsyncMock(return_value={"data_commitment": "commitment1"})),
                AsyncMock(status=200, json=AsyncMock(return_value={"data_commitment": "commitment2"})),
                AsyncMock(status=200, json=AsyncMock(return_value={"data_commitment": "commitment1"}))
            ]
            mock_post.side_effect = mock_responses

            # Now attempt to share data
            response = client.post("/share_data", json={
                "identity": IDENTITY_1,
                "tlsn_proof": MOCK_TLSN_PROOF
            })

    assert response.status_code == 200, f"Expected status code 200, but got {response.status_code}"
    assert not expected_tlsn_proof.exists(), "Expected TLSN proof file not found"

@pytest.mark.asyncio
async def test_share_data_with_mismatched_data_commitments_tlsn_and_mpc(tmp_path, client, db_session, create_voucher):
    """Test sharing data with a registered identity."""
    # First, register the identity
    voucher = create_voucher(VOUCHER_CODE_1)
    client.post("/register", json={
        "voucher_code": voucher.code,
        "identity": IDENTITY_1
    })

    data_provider: DataProvider | None = db_session.query(DataProvider).filter(DataProvider.identity == IDENTITY_1).first()
    assert data_provider is not None, "Data provider not found in database after registration"
    client_id = data_provider.id

    # Mock tlsn_proofs_dir and thus we know if share_data succeeds, tlsn_proof is saved at the path.
    expected_tlsn_dir = tmp_path / "tlsn_proofs"
    settings.tlsn_proofs_dir = str(expected_tlsn_dir)
    expected_tlsn_dir.mkdir(parents=True, exist_ok=True)
    expected_tlsn_proof = expected_tlsn_dir / f"proof_{client_id}.json"

    # Mock the TLSN proof verification process
    with patch('asyncio.create_subprocess_shell', new_callable=AsyncMock) as mock_subprocess:
        mock_subprocess.return_value.communicate.return_value = (b'', b'')
        mock_subprocess.return_value.returncode = 0

        # Mock the aiohttp ClientSession
        with patch('aiohttp.ClientSession') as mock_session:
            mock_post = AsyncMock()
            mock_session.return_value.__aenter__.return_value.post = mock_post

            # Create mock responses with different data commitments
            commitment_1 = "commitment1"
            commitment_2 = "commitment2"
            mock_responses = [
                AsyncMock(status=200, json=AsyncMock(return_value={"data_commitment": commitment_1})),
                AsyncMock(status=200, json=AsyncMock(return_value={"data_commitment": commitment_1})),
                AsyncMock(status=200, json=AsyncMock(return_value={"data_commitment": commitment_1}))
            ]
            mock_post.side_effect = mock_responses
            # Mock get_data_commitment_hash_from_tlsn_proof to return the same commitment
            with patch('mpc_demo_infra.coordination_server.routes.get_data_commitment_hash_from_tlsn_proof', return_value=commitment_2):
                response = client.post("/share_data", json={
                    "identity": IDENTITY_1,
                    "tlsn_proof": MOCK_TLSN_PROOF
                })

    assert response.status_code == 200, f"Response: {response.json()}"
    assert "mpc_port_base" in response.json()
    assert "client_port" in response.json()
    assert not expected_tlsn_proof.exists(), "Expected TLSN proof file not found"
