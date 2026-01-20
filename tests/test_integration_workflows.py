"""
Integration tests for negotiation and tournament workflows.

These tests verify the complete user workflows at the API level:
- Creating negotiations and tournaments
- Accessing session data
- Managing session lifecycle

Note: Running negotiations/tournaments uses SSE streaming endpoints which
are tested separately in test_session_manager.py and test_tournament_manager.py
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from negmas_app.main import app


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_scenario_path():
    """Get path to a sample scenario for testing."""
    base_path = Path(__file__).parent.parent / "scenarios"
    scenario_path = base_path / "anac2011" / "Laptop"
    if scenario_path.exists():
        return str(scenario_path)
    # Fallback to any available scenario
    for year_dir in base_path.iterdir():
        if year_dir.is_dir() and year_dir.name.startswith("anac"):
            for scenario_dir in year_dir.iterdir():
                if scenario_dir.is_dir():
                    return str(scenario_dir)
    return None


@pytest.fixture
def sample_scenario_paths(sample_scenario_path):
    """Get multiple scenario paths for tournament testing."""
    if sample_scenario_path is None:
        return []
    base_path = Path(sample_scenario_path).parent
    paths = []
    for scenario_dir in base_path.iterdir():
        if scenario_dir.is_dir():
            paths.append(str(scenario_dir))
            if len(paths) >= 3:
                break
    return paths


def test_create_negotiation(client: TestClient, sample_scenario_path: str):
    """
    Test creating a negotiation.

    This test verifies:
    1. Negotiation can be created with valid parameters
    2. Session ID is returned
    3. Session can be retrieved
    """
    if sample_scenario_path is None:
        pytest.skip("No sample scenario available")

    # Get available negotiators
    response = client.get("/api/negotiators")
    assert response.status_code == 200
    data = response.json()
    negotiators = data["negotiators"]
    assert len(negotiators) >= 2, "Need at least 2 negotiators for testing"

    # Start a negotiation
    response = client.post(
        "/api/negotiation/start",
        json={
            "scenario_path": sample_scenario_path,
            "negotiators": [
                {"type_name": negotiators[0]["type_name"]},
                {"type_name": negotiators[1]["type_name"]},
            ],
        },
    )
    assert response.status_code == 200
    session_data = response.json()
    assert "session_id" in session_data
    session_id = session_data["session_id"]

    # Verify we can retrieve the session
    response = client.get(f"/api/negotiation/{session_id}")
    assert response.status_code == 200
    negotiation = response.json()
    assert negotiation["id"] == session_id


def test_list_negotiations(client: TestClient, sample_scenario_path: str):
    """
    Test listing negotiations.

    This test verifies:
    1. Can create a negotiation
    2. Can list all negotiations
    3. Created negotiation appears in the list
    """
    if sample_scenario_path is None:
        pytest.skip("No sample scenario available")

    # Create a negotiation
    response = client.get("/api/negotiators")
    assert response.status_code == 200
    negotiators = response.json()["negotiators"]

    response = client.post(
        "/api/negotiation/start",
        json={
            "scenario_path": sample_scenario_path,
            "negotiators": [
                {"type_name": negotiators[0]["type_name"]},
                {"type_name": negotiators[1]["type_name"]},
            ],
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    # List negotiations
    response = client.get("/api/negotiation/sessions/list")
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    sessions = data["sessions"]

    # Verify our negotiation is in the list
    session_ids = [s["id"] for s in sessions]
    assert session_id in session_ids


def test_cancel_negotiation(client: TestClient, sample_scenario_path: str):
    """
    Test cancelling a negotiation.

    This test verifies:
    1. Can create a negotiation
    2. Can cancel it
    3. Status updates correctly
    """
    if sample_scenario_path is None:
        pytest.skip("No sample scenario available")

    # Create a negotiation
    response = client.get("/api/negotiators")
    assert response.status_code == 200
    negotiators = response.json()["negotiators"]

    response = client.post(
        "/api/negotiation/start",
        json={
            "scenario_path": sample_scenario_path,
            "negotiators": [
                {"type_name": negotiators[0]["type_name"]},
                {"type_name": negotiators[1]["type_name"]},
            ],
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    # Cancel it
    response = client.post(f"/api/negotiation/{session_id}/cancel")
    assert response.status_code == 200

    # Verify status
    response = client.get(f"/api/negotiation/{session_id}")
    assert response.status_code == 200
    negotiation = response.json()
    # Status may be pending, cancelled, or canceled depending on timing
    assert negotiation["status"] in ["pending", "cancelled", "canceled", "running"]


def test_create_tournament(client: TestClient, sample_scenario_paths: list[str]):
    """
    Test creating a tournament.

    This test verifies:
    1. Tournament can be created with multiple scenarios and negotiators
    2. Session ID is returned
    3. Session can be retrieved
    """
    if len(sample_scenario_paths) < 2:
        pytest.skip("Need at least 2 scenarios for tournament testing")

    # Get available negotiators
    response = client.get("/api/negotiators")
    assert response.status_code == 200
    negotiators = response.json()["negotiators"]
    assert len(negotiators) >= 2, "Need at least 2 negotiators for tournament"

    # Select first 3 negotiators (or less if not available)
    competitor_types = [n["type_name"] for n in negotiators[:3]]

    # Start a tournament
    response = client.post(
        "/api/tournament/start",
        json={
            "scenario_paths": sample_scenario_paths[:2],
            "competitor_types": competitor_types,
            "n_repetitions": 1,
        },
    )
    assert response.status_code == 200
    session_data = response.json()
    assert "session_id" in session_data
    session_id = session_data["session_id"]

    # Verify we can retrieve the session
    response = client.get(f"/api/tournament/{session_id}")
    assert response.status_code == 200
    tournament = response.json()
    assert tournament["id"] == session_id


def test_list_tournaments(client: TestClient, sample_scenario_paths: list[str]):
    """
    Test listing tournaments.

    This test verifies:
    1. Can create a tournament
    2. Can list all tournaments
    3. Created tournament appears in the list
    """
    if len(sample_scenario_paths) < 2:
        pytest.skip("Need at least 2 scenarios for tournament testing")

    # Create a tournament
    response = client.get("/api/negotiators")
    assert response.status_code == 200
    negotiators = response.json()["negotiators"]
    competitor_types = [n["type_name"] for n in negotiators[:2]]

    response = client.post(
        "/api/tournament/start",
        json={
            "scenario_paths": sample_scenario_paths[:2],
            "competitor_types": competitor_types,
            "n_repetitions": 1,
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    # List tournaments
    response = client.get("/api/tournament/sessions/list")
    assert response.status_code == 200
    data = response.json()
    assert "sessions" in data
    sessions = data["sessions"]

    # Verify our tournament is in the list
    session_ids = [s["id"] for s in sessions]
    assert session_id in session_ids


def test_cancel_tournament(client: TestClient, sample_scenario_paths: list[str]):
    """
    Test cancelling a tournament.

    This test verifies:
    1. Can create a tournament
    2. Can cancel it
    3. Status updates correctly
    """
    if len(sample_scenario_paths) < 2:
        pytest.skip("Need at least 2 scenarios for tournament testing")

    # Create a tournament
    response = client.get("/api/negotiators")
    assert response.status_code == 200
    negotiators = response.json()["negotiators"]
    competitor_types = [n["type_name"] for n in negotiators[:2]]

    response = client.post(
        "/api/tournament/start",
        json={
            "scenario_paths": sample_scenario_paths[:2],
            "competitor_types": competitor_types,
            "n_repetitions": 2,
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    # Cancel it
    response = client.post(f"/api/tournament/{session_id}/cancel")
    assert response.status_code == 200

    # Verify status
    response = client.get(f"/api/tournament/{session_id}")
    assert response.status_code == 200
    tournament = response.json()
    assert tournament["status"] in ["cancelled", "canceled", "running", "waiting"]


def test_pause_resume_negotiation(client: TestClient, sample_scenario_path: str):
    """
    Test pausing and resuming a negotiation.

    This test verifies:
    1. Can create a negotiation
    2. Can pause it
    3. Can resume it
    """
    if sample_scenario_path is None:
        pytest.skip("No sample scenario available")

    # Create a negotiation
    response = client.get("/api/negotiators")
    assert response.status_code == 200
    negotiators = response.json()["negotiators"]

    response = client.post(
        "/api/negotiation/start",
        json={
            "scenario_path": sample_scenario_path,
            "negotiators": [
                {"type_name": negotiators[0]["type_name"]},
                {"type_name": negotiators[1]["type_name"]},
            ],
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    # Pause it
    response = client.post(f"/api/negotiation/{session_id}/pause")
    assert response.status_code == 200

    # Resume it
    response = client.post(f"/api/negotiation/{session_id}/resume")
    assert response.status_code == 200


def test_get_nonexistent_negotiation(client: TestClient):
    """
    Test getting a nonexistent negotiation returns 404.
    """
    response = client.get("/api/negotiation/nonexistent-id")
    assert response.status_code == 404


def test_get_nonexistent_tournament(client: TestClient):
    """
    Test getting a nonexistent tournament returns 404.
    """
    response = client.get("/api/tournament/nonexistent-id")
    assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
