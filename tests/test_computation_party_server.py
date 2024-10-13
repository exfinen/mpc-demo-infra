import subprocess
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
import requests

from mpc_demo_infra.computation_party_server.main import app
from mpc_demo_infra.computation_party_server.routes import share_data, query_computation
from mpc_demo_infra.computation_party_server.schemas import ShareDataRequest, QueryComputationRequest
from mpc_demo_infra.computation_party_server.config import settings

from .common import TLSN_PROOF

client = TestClient(app)


@pytest.fixture
def mock_db():
    return MagicMock()

@patch('mpc_demo_infra.computation_party_server.routes.requests.post')
@patch('mpc_demo_infra.computation_party_server.routes.run_program')
def test_share_data_success(mock_run, mock_post, mock_db):
    identity = "id@zkstats.io"
    client_id = 1
    mpc_port_base = 55688

    # Mock responses for successful identity verification and negotiation
    mock_identity_response = MagicMock()
    mock_identity_response.json.return_value = {"client_id": client_id}

    mock_negotiate_response = MagicMock()
    mock_negotiate_response.json.return_value = {"ports": [mpc_port_base + i for i in range(settings.num_parties)]}

    mock_set_complete_response = MagicMock()
    mock_set_complete_response.status_code = 204
    mock_post.side_effect = [
        mock_identity_response, mock_negotiate_response, mock_set_complete_response,
    ]

    # Mock run_program
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    request_data = ShareDataRequest(
        identity=identity,
        tlsn_proof=TLSN_PROOF,
    )
    response = client.post("/share_data", json=request_data.dict())

    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "Data shared successfully"}

    # Check that three POST requests were made
    assert mock_post.call_count == 3

    # Check the first call (identity verification)
    mock_post.assert_any_call(
        f"{settings.coordination_server_url}/verify_registration",
        json={"identity": identity}
    )

    # Check the second call (negotiate share data)
    mock_post.assert_any_call(
        f"{settings.coordination_server_url}/negotiate_share_data",
        json={"party_id": settings.party_id, "identity": identity}
    )

    # Check the third call (set share data complete)
    mock_post.assert_any_call(
        f"{settings.coordination_server_url}/set_share_data_complete",
        json={"party_id": settings.party_id, "identity": identity}
    )

    # Check that run_program was called
    mock_run.assert_called_once()


@patch('mpc_demo_infra.computation_party_server.routes.requests.post')
def test_share_data_identity_verification_failed(mock_post, mock_db):
    # Mock the response from the coordination server to simulate a failed verification
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.RequestException("Verification failed")
    mock_post.return_value = mock_response

    request_data = ShareDataRequest(
        identity="invalid_id@zkstats.io",
        tlsn_proof=TLSN_PROOF,
    )
    response = client.post("/share_data", json=request_data.dict())

    assert response.status_code == 400
    assert response.json() == {"detail": "Failed to verify identity with coordination server"}

    mock_post.assert_called_once()


@patch('mpc_demo_infra.computation_party_server.routes.requests.post')
def test_share_data_invalid_tlsn_proof(mock_post, mock_db):
    identity = "id@zkstats.io"
    client_id = 1
    # Mock the response from the coordination server
    mock_response = MagicMock()
    mock_response.json.return_value = {"client_id": client_id}
    mock_post.return_value = mock_response

    # Create an invalid TLSN proof by modifying a few characters
    invalid_tlsn_proof = TLSN_PROOF.replace('129', '128').replace('50', '51')

    request_data = ShareDataRequest(
        identity=identity,
        tlsn_proof=invalid_tlsn_proof,
    )
    response = client.post("/share_data", json=request_data.dict())

    assert response.status_code == 400
    assert response.json() == {"detail": "Failed when verifying TLSN proof"}

    # Ensure that the request to the coordination server was not made
    mock_post.assert_called_once()


@patch('mpc_demo_infra.computation_party_server.routes.requests.post')
def test_share_data_negotiate_share_data_fails(mock_post, mock_db):
    identity = "id@zkstats.io"
    client_id = 1
    # Mock the response from the coordination server for identity verification
    mock_identity_response = MagicMock()
    mock_identity_response.json.return_value = {"client_id": client_id}

    # Mock the response from the coordination server for negotiate_share_data
    mock_negotiate_response = MagicMock()
    mock_negotiate_response.raise_for_status.side_effect = requests.RequestException("Negotiation failed")

    # Set up the mock to return different responses for different calls
    mock_post.side_effect = [mock_identity_response, mock_negotiate_response]

    request_data = ShareDataRequest(
        identity=identity,
        tlsn_proof=TLSN_PROOF,
    )
    response = client.post("/share_data", json=request_data.dict())

    assert response.status_code == 400
    assert response.json() == {"detail": "Failed to negotiate share data with coordination server"}

    # Ensure that both POST requests were made
    assert mock_post.call_count == 2

    # Check the first call (identity verification)
    mock_post.assert_any_call(
        f"{settings.coordination_server_url}/verify_registration",
        json={"identity": identity}
    )

    # Check the second call (negotiate_share_data)
    mock_post.assert_any_call(
        f"{settings.coordination_server_url}/negotiate_share_data",
        json={"party_id": settings.party_id, "identity": identity}
    )

@patch('mpc_demo_infra.computation_party_server.routes.requests.post')
@patch('mpc_demo_infra.computation_party_server.routes.run_program')
def test_share_data_set_share_data_complete_fails(mock_run, mock_post, mock_db):
    identity = "id@zkstats.io"
    client_id = 1
    mpc_port_base = 55688

    # Mock responses for successful identity verification and negotiation
    mock_identity_response = MagicMock()
    mock_identity_response.json.return_value = {"client_id": client_id}

    mock_negotiate_response = MagicMock()
    mock_negotiate_response.json.return_value = {"ports": [mpc_port_base + i for i in range(settings.num_parties)]}

    # Mock response for set_share_data_complete that fails
    mock_set_complete_response = MagicMock()
    mock_set_complete_response.raise_for_status.side_effect = requests.RequestException("Failed to set share data complete")

    # Set up the mock to return different responses for different calls
    mock_post.side_effect = [mock_identity_response, mock_negotiate_response, mock_set_complete_response]

    # Mock run_program
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    request_data = ShareDataRequest(
        identity=identity,
        tlsn_proof=TLSN_PROOF,
    )
    response = client.post("/share_data", json=request_data.dict())

    assert response.status_code == 400
    assert response.json() == {"detail": "Failed to set share data complete with coordination server"}

    # Ensure that all three POST requests were made
    assert mock_post.call_count == 3

    # Check the first call (identity verification)
    mock_post.assert_any_call(
        f"{settings.coordination_server_url}/verify_registration",
        json={"identity": identity}
    )

    # Check the second call (negotiate_share_data)
    mock_post.assert_any_call(
        f"{settings.coordination_server_url}/negotiate_share_data",
        json={"party_id": settings.party_id, "identity": identity}
    )

    # Check the third call (set_share_data_complete)
    mock_post.assert_any_call(
        f"{settings.coordination_server_url}/set_share_data_complete",
        json={"party_id": settings.party_id, "identity": identity}
    )

    # Check that run_program was called
    mock_run.assert_called_once()


@patch('mpc_demo_infra.computation_party_server.routes.requests.post')
@patch('mpc_demo_infra.computation_party_server.routes.run_program')
def test_share_data_mpc(mock_run, mock_post, mock_db):
    identity = "id@zkstats.io"
    client_id = 1
    mpc_port_base = 55688

    # Mock responses for successful identity verification and negotiation
    mock_identity_response = MagicMock()
    mock_identity_response.json.return_value = {"client_id": client_id}

    mock_negotiate_response = MagicMock()
    mock_negotiate_response.json.return_value = {"ports": [mpc_port_base + i for i in range(settings.num_parties)]}

    # Mock response for set_share_data_complete that fails
    mock_set_complete_response = MagicMock()
    mock_set_complete_response.raise_for_status.side_effect = requests.RequestException("Failed to set share data complete")

    # Set up the mock to return different responses for different calls
    mock_post.side_effect = [mock_identity_response, mock_negotiate_response, mock_set_complete_response]

    # Mock run_program
    mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    request_data = ShareDataRequest(
        identity=identity,
        tlsn_proof=TLSN_PROOF,
    )
    response = client.post("/share_data", json=request_data.dict())

    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "Data shared successfully"}

    # Ensure that all three POST requests were made
    assert mock_post.call_count == 3

    # Check the first call (identity verification)
    mock_post.assert_any_call(
        f"{settings.coordination_server_url}/verify_registration",
        json={"identity": identity}
    )

    # Check the second call (negotiate_share_data)
    mock_post.assert_any_call(
        f"{settings.coordination_server_url}/negotiate_share_data",
        json={"party_id": settings.party_id, "identity": identity}
    )

    # Check the third call (set_share_data_complete)
    mock_post.assert_any_call(
        f"{settings.coordination_server_url}/set_share_data_complete",
        json={"party_id": settings.party_id, "identity": identity}
    )

    # Check that run_program was called
    mock_run.assert_called_once()


@pytest.fixture
def mock_subprocess_run():
    with patch("subprocess.run") as mock_run:
        yield mock_run

def test_request_sharing_data_mpc(mock_subprocess_run):
    # Mock the TLSN proof verification
    mock_subprocess_run.return_value.returncode = 0

    # Mock the backup_shares function
    with patch("mpc_demo_infra.computation_party_server.routes.backup_shares") as mock_backup:
        mock_backup.return_value = None

        # Mock the prepare_data_sharing_program function
        with patch("mpc_demo_infra.computation_party_server.routes.prepare_data_sharing_program") as mock_prepare:
            mock_prepare.return_value = "test_circuit"

            # Mock the compile_program function
            with patch("mpc_demo_infra.computation_party_server.routes.compile_program") as mock_compile:
                # Mock the run_data_sharing_program function
                with patch("mpc_demo_infra.computation_party_server.routes.run_data_sharing_program") as mock_run:
                    mock_run.return_value = (0.5, "test_commitment")

                    response = client.post("/request_sharing_data_mpc", json={
                        "client_id": 1,
                        "mpc_port_base": 14000,
                        "tlsn_proof": '{"substrings": {"private_openings": {"test": [null, {"hash": [0]}]}}}'
                    })

    assert response.status_code == 200
    assert response.json() == {"data_commitment": "test_commitment"}

def test_query_computation():
    response = client.post("/query_computation", json={"computation_index": 1})
    assert response.status_code == 200
    assert response.json()["success"] == True
    assert response.json()["computation_index"] == 1

# Add more tests as needed for other functions and edge cases
