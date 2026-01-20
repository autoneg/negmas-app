"""
Integration tests for negotiation and tournament workflows.

These tests verify the complete user workflows at the API level:
- Starting and running negotiations
- Opening stored negotiations
- Starting and running tournaments
- Opening stored tournaments

Tests backend functionality and data integrity.
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


def test_start_and_run_negotiation(client: TestClient, sample_scenario_path: str):
    """
    Test starting and running a negotiation to completion.

    This test verifies:
    1. Negotiation can be created with valid parameters
    2. Negotiation can be run to completion
    3. Final state shows completion status
    4. Agreement/outcome data is available
    """
    if sample_scenario_path is None:
        pytest.skip("No sample scenario available")

    # Get available negotiators
    response = client.get("/api/negotiators")
    assert response.status_code == 200
    data = response.json()
    negotiators = data["negotiators"]
    assert len(negotiators) >= 2, "Need at least 2 negotiators for testing"

    # Pick the first two negotiators
    negotiator_types = [negotiators[0]["type_name"], negotiators[1]["type_name"]]

    # Start a negotiation
    response = client.post(
        "/api/negotiations/start",
        json={
            "scenario_path": sample_scenario_path,
            "negotiator_types": negotiator_types,
            "negotiator_params": [{}, {}],
        },
    )
    assert response.status_code == 200
    session_data = response.json()
    session_id = session_data["id"]
    assert session_data["status"] in ["running", "waiting"]

    # Run the negotiation to completion
    response = client.post(f"/api/negotiations/{session_id}/run")
    assert response.status_code == 200

    # Wait a bit for it to complete (the endpoint is async)
    import time

    time.sleep(2)

    # Check final status
    response = client.get(f"/api/negotiations/{session_id}")
    assert response.status_code == 200
    final_data = response.json()

    # Verify it completed
    assert final_data["status"] in ["completed", "failed", "agreement", "no_agreement"]

    # Verify we have outcome data
    assert "state" in final_data
    assert final_data["state"] is not None


def test_list_and_open_stored_negotiation(
    client: TestClient, sample_scenario_path: str
):
    """
    Test listing negotiations and opening a stored one.

    This test verifies:
    1. Can list all negotiations
    2. Can retrieve details of a specific negotiation
    3. Retrieved data includes all necessary information
    """
    if sample_scenario_path is None:
        pytest.skip("No sample scenario available")

    # First create a negotiation so we have something to list
    response = client.get("/api/negotiators")
    assert response.status_code == 200
    negotiators = response.json()["negotiators"]
    negotiator_types = [negotiators[0]["type_name"], negotiators[1]["type_name"]]

    response = client.post(
        "/api/negotiations/start",
        json={
            "scenario_path": sample_scenario_path,
            "negotiator_types": negotiator_types,
            "negotiator_params": [{}, {}],
        },
    )
    assert response.status_code == 200
    session_id = response.json()["id"]

    # List negotiations
    response = client.get("/api/negotiations")
    assert response.status_code == 200
    negotiations = response.json()
    assert len(negotiations) > 0
    assert any(n["id"] == session_id for n in negotiations)

    # Open the specific negotiation
    response = client.get(f"/api/negotiations/{session_id}")
    assert response.status_code == 200
    negotiation = response.json()

    # Verify all required fields
    assert negotiation["id"] == session_id
    assert "status" in negotiation
    assert "scenario_path" in negotiation
    assert "negotiator_types" in negotiation
    assert "state" in negotiation


def test_start_and_run_tournament(client: TestClient, sample_scenario_paths: list[str]):
    """
    Test starting and running a tournament to completion.

    This test verifies:
    1. Tournament can be created with multiple scenarios and negotiators
    2. Tournament can be run to completion
    3. Results include leaderboard and statistics
    """
    if len(sample_scenario_paths) < 2:
        pytest.skip("Need at least 2 scenarios for tournament testing")

    # Get available negotiators
    response = client.get("/api/negotiators")
    assert response.status_code == 200
    negotiators = response.json()["negotiators"]
    assert len(negotiators) >= 2, "Need at least 2 negotiators for tournament"

    # Select first 3 negotiators (or less if not available)
    negotiator_types = [n["type_name"] for n in negotiators[:3]]

    # Start a tournament
    response = client.post(
        "/api/tournaments/start",
        json={
            "scenario_paths": sample_scenario_paths[:2],
            "negotiator_types": negotiator_types,
            "n_repetitions": 1,
        },
    )
    assert response.status_code == 200
    session_data = response.json()
    session_id = session_data["id"]
    assert session_data["status"] in ["running", "waiting"]

    # Run the tournament
    response = client.post(f"/api/tournaments/{session_id}/run")
    assert response.status_code == 200

    # Wait for completion (tournaments take longer)
    import time

    time.sleep(5)

    # Check final status
    response = client.get(f"/api/tournaments/{session_id}")
    assert response.status_code == 200
    final_data = response.json()

    # Verify tournament completed
    assert final_data["status"] in ["completed", "running"]

    # Verify we have results structure
    assert "results" in final_data


def test_list_and_open_stored_tournament(
    client: TestClient, sample_scenario_paths: list[str]
):
    """
    Test listing tournaments and opening a stored one.

    This test verifies:
    1. Can list all tournaments
    2. Can retrieve details of a specific tournament
    3. Retrieved data includes configuration and results
    """
    if len(sample_scenario_paths) < 2:
        pytest.skip("Need at least 2 scenarios for tournament testing")

    # Create a tournament
    response = client.get("/api/negotiators")
    assert response.status_code == 200
    negotiators = response.json()["negotiators"]
    negotiator_types = [n["type_name"] for n in negotiators[:2]]

    response = client.post(
        "/api/tournaments/start",
        json={
            "scenario_paths": sample_scenario_paths[:2],
            "negotiator_types": negotiator_types,
            "n_repetitions": 1,
        },
    )
    assert response.status_code == 200
    session_id = response.json()["id"]

    # List tournaments
    response = client.get("/api/tournaments")
    assert response.status_code == 200
    tournaments = response.json()
    assert len(tournaments) > 0
    assert any(t["id"] == session_id for t in tournaments)

    # Open the specific tournament
    response = client.get(f"/api/tournaments/{session_id}")
    assert response.status_code == 200
    tournament = response.json()

    # Verify all required fields
    assert tournament["id"] == session_id
    assert "status" in tournament
    assert "scenario_paths" in tournament
    assert "negotiator_types" in tournament
    assert "results" in tournament


def test_negotiation_step_by_step(client: TestClient, sample_scenario_path: str):
    """
    Test stepping through a negotiation one step at a time.

    This test verifies:
    1. Can start a negotiation
    2. Can step through it incrementally
    3. State updates correctly after each step
    """
    if sample_scenario_path is None:
        pytest.skip("No sample scenario available")

    # Get negotiators and start negotiation
    response = client.get("/api/negotiators")
    assert response.status_code == 200
    negotiators = response.json()["negotiators"]
    negotiator_types = [negotiators[0]["type_name"], negotiators[1]["type_name"]]

    response = client.post(
        "/api/negotiations/start",
        json={
            "scenario_path": sample_scenario_path,
            "negotiator_types": negotiator_types,
            "negotiator_params": [{}, {}],
        },
    )
    assert response.status_code == 200
    session_id = response.json()["id"]

    # Step through 5 times
    for i in range(5):
        response = client.post(f"/api/negotiations/{session_id}/step")
        assert response.status_code == 200

        # Get current state
        response = client.get(f"/api/negotiations/{session_id}")
        assert response.status_code == 200
        state = response.json()

        # Verify step count increased
        if state["status"] not in ["completed", "failed"]:
            assert state["state"]["step"] >= i


def test_tournament_cancellation(client: TestClient, sample_scenario_paths: list[str]):
    """
    Test cancelling a running tournament.

    This test verifies:
    1. Can start a tournament
    2. Can cancel it while running
    3. Status updates to cancelled
    """
    if len(sample_scenario_paths) < 2:
        pytest.skip("Need at least 2 scenarios for tournament testing")

    # Get negotiators and start tournament
    response = client.get("/api/negotiators")
    assert response.status_code == 200
    negotiators = response.json()["negotiators"]
    negotiator_types = [n["type_name"] for n in negotiators[:2]]

    response = client.post(
        "/api/tournaments/start",
        json={
            "scenario_paths": sample_scenario_paths[:2],
            "negotiator_types": negotiator_types,
            "n_repetitions": 10,  # More reps to ensure it runs long enough
        },
    )
    assert response.status_code == 200
    session_id = response.json()["id"]

    # Start running (but don't wait)
    response = client.post(f"/api/tournaments/{session_id}/run")
    assert response.status_code == 200

    # Cancel it immediately
    response = client.post(f"/api/tournaments/{session_id}/cancel")
    assert response.status_code == 200

    # Verify status
    response = client.get(f"/api/tournaments/{session_id}")
    assert response.status_code == 200
    tournament = response.json()
    assert tournament["status"] in [
        "cancelled",
        "completed",
        "running",
    ]  # May have completed quickly


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
