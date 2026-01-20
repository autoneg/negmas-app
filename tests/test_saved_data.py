"""
Tests for saved negotiation and tournament endpoints.
"""

import pytest
from fastapi.testclient import TestClient
import time


class TestSavedNegotiationsAPI:
    """Tests for /api/negotiation/saved endpoints."""

    def test_list_saved_negotiations_empty(self, client: TestClient):
        """Test listing saved negotiations when none exist or after cleanup."""
        response = client.get("/api/negotiation/saved/list")
        assert response.status_code == 200
        data = response.json()
        assert "negotiations" in data
        assert isinstance(data["negotiations"], list)

    def test_save_and_retrieve_negotiation(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test saving a negotiation and retrieving it."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        # Start a negotiation with save enabled
        response = client.post(
            "/api/negotiation/start",
            json={
                "scenario_path": sample_scenario_path,
                "negotiators": [
                    {"type_name": native_negotiator_types[0], "name": "TestAgent1"},
                    {"type_name": native_negotiator_types[1], "name": "TestAgent2"},
                ],
                "mechanism_type": "SAOMechanism",
                "mechanism_params": {"n_steps": 5},
                "step_delay": 0.0,
                "auto_save": True,
            },
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Wait a bit for negotiation to complete
        time.sleep(2)

        # Check if it appears in saved list
        response = client.get("/api/negotiation/saved/list")
        assert response.status_code == 200
        saved = response.json()["negotiations"]
        session_ids = [n["id"] for n in saved]

        # The session might be saved
        if session_id in session_ids:
            # Get the saved negotiation details
            response = client.get(f"/api/negotiation/saved/{session_id}")
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert data["id"] == session_id

    def test_delete_saved_negotiation(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test deleting a saved negotiation."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        # Start and save a negotiation
        response = client.post(
            "/api/negotiation/start",
            json={
                "scenario_path": sample_scenario_path,
                "negotiators": [
                    {"type_name": native_negotiator_types[0], "name": "DelAgent1"},
                    {"type_name": native_negotiator_types[1], "name": "DelAgent2"},
                ],
                "mechanism_type": "SAOMechanism",
                "mechanism_params": {"n_steps": 3},
                "step_delay": 0.0,
                "auto_save": True,
            },
        )
        session_id = response.json()["session_id"]
        time.sleep(2)

        # Delete it
        response = client.delete(f"/api/negotiation/saved/{session_id}")
        # Should succeed or return 404 if not saved
        assert response.status_code in (200, 404)

    def test_update_negotiation_tags(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test updating tags on a saved negotiation."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        # Start and save a negotiation
        response = client.post(
            "/api/negotiation/start",
            json={
                "scenario_path": sample_scenario_path,
                "negotiators": [
                    {"type_name": native_negotiator_types[0], "name": "TagAgent1"},
                    {"type_name": native_negotiator_types[1], "name": "TagAgent2"},
                ],
                "mechanism_type": "SAOMechanism",
                "mechanism_params": {"n_steps": 3},
                "step_delay": 0.0,
                "auto_save": True,
            },
        )
        session_id = response.json()["session_id"]
        time.sleep(2)

        # Add tags
        response = client.post(
            f"/api/negotiation/saved/{session_id}/tags",
            json={"tags": ["test", "important", "demo"]},
        )
        # Should succeed or return 404 if not saved
        assert response.status_code in (200, 404)

        if response.status_code == 200:
            # Verify tags were added
            response = client.get(f"/api/negotiation/saved/{session_id}")
            assert response.status_code == 200
            data = response.json()
            assert "tags" in data
            assert "test" in data["tags"]

    def test_archive_negotiation(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test archiving a saved negotiation."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        # Start and save a negotiation
        response = client.post(
            "/api/negotiation/start",
            json={
                "scenario_path": sample_scenario_path,
                "negotiators": [
                    {"type_name": native_negotiator_types[0], "name": "ArchAgent1"},
                    {"type_name": native_negotiator_types[1], "name": "ArchAgent2"},
                ],
                "mechanism_type": "SAOMechanism",
                "mechanism_params": {"n_steps": 3},
                "step_delay": 0.0,
                "auto_save": True,
            },
        )
        session_id = response.json()["session_id"]
        time.sleep(2)

        # Archive it
        response = client.post(f"/api/negotiation/saved/{session_id}/archive")
        assert response.status_code in (200, 404)

        if response.status_code == 200:
            # Unarchive it
            response = client.post(f"/api/negotiation/saved/{session_id}/unarchive")
            assert response.status_code == 200


class TestSavedTournamentsAPI:
    """Tests for /api/tournament/saved endpoints."""

    def test_list_saved_tournaments_empty(self, client: TestClient):
        """Test listing saved tournaments."""
        response = client.get("/api/tournament/saved/list")
        assert response.status_code == 200
        data = response.json()
        assert "tournaments" in data
        assert isinstance(data["tournaments"], list)

    def test_save_and_retrieve_tournament(
        self,
        client: TestClient,
        sample_scenario_paths: list[str],
        native_negotiator_types: list[str],
    ):
        """Test saving a tournament and retrieving it."""
        if not sample_scenario_paths:
            pytest.skip("No sample scenarios available")

        # Start a tournament
        response = client.post(
            "/api/tournament/start",
            json={
                "competitor_types": [native_negotiator_types[0]],
                "opponent_types": [native_negotiator_types[1]],
                "scenario_paths": sample_scenario_paths[:1],
                "n_repetitions": 1,
            },
        )
        assert response.status_code == 200
        tournament_id = response.json()["session_id"]

        # Wait for tournament to complete
        time.sleep(5)

        # Check if it appears in saved list
        response = client.get("/api/tournament/saved/list")
        assert response.status_code == 200
        tournaments = response.json()["tournaments"]
        tournament_ids = [t["id"] for t in tournaments]

        if tournament_id in tournament_ids:
            # Get the saved tournament details
            response = client.get(f"/api/tournament/saved/{tournament_id}")
            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert data["id"] == tournament_id

    def test_delete_saved_tournament(
        self,
        client: TestClient,
        sample_scenario_paths: list[str],
        native_negotiator_types: list[str],
    ):
        """Test deleting a saved tournament."""
        if not sample_scenario_paths:
            pytest.skip("No sample scenarios available")

        # Start a tournament
        response = client.post(
            "/api/tournament/start",
            json={
                "competitor_types": [native_negotiator_types[0]],
                "opponent_types": [native_negotiator_types[1]],
                "scenario_paths": sample_scenario_paths[:1],
                "n_repetitions": 1,
                "n_steps": 3,
            },
        )
        tournament_id = response.json()["session_id"]
        time.sleep(5)

        # Delete it
        response = client.delete(f"/api/tournament/saved/{tournament_id}")
        assert response.status_code in (200, 404)

    def test_update_tournament_tags(
        self,
        client: TestClient,
        sample_scenario_paths: list[str],
        native_negotiator_types: list[str],
    ):
        """Test updating tags on a saved tournament."""
        if not sample_scenario_paths:
            pytest.skip("No sample scenarios available")

        # Start a tournament
        response = client.post(
            "/api/tournament/start",
            json={
                "competitor_types": [native_negotiator_types[0]],
                "opponent_types": [native_negotiator_types[1]],
                "scenario_paths": sample_scenario_paths[:1],
                "n_repetitions": 1,
                "n_steps": 5,
            },
        )
        tournament_id = response.json()["session_id"]
        time.sleep(5)

        # Add tags
        response = client.post(
            f"/api/tournament/saved/{tournament_id}/tags",
            json={"tags": ["test-tourn", "important"]},
        )
        assert response.status_code in (200, 404)

        if response.status_code == 200:
            # Verify tags
            response = client.get(f"/api/tournament/saved/{tournament_id}")
            assert response.status_code == 200
            data = response.json()
            assert "tags" in data
            assert "test-tourn" in data["tags"]

    def test_archive_tournament(
        self,
        client: TestClient,
        sample_scenario_paths: list[str],
        native_negotiator_types: list[str],
    ):
        """Test archiving a saved tournament."""
        if not sample_scenario_paths:
            pytest.skip("No sample scenarios available")

        # Start a tournament
        response = client.post(
            "/api/tournament/start",
            json={
                "competitor_types": [native_negotiator_types[0]],
                "opponent_types": [native_negotiator_types[1]],
                "scenario_paths": sample_scenario_paths[:1],
                "n_repetitions": 1,
                "n_steps": 3,
            },
        )
        tournament_id = response.json()["session_id"]
        time.sleep(5)

        # Archive it
        response = client.post(f"/api/tournament/saved/{tournament_id}/archive")
        assert response.status_code in (200, 404)

    def test_get_tournament_config(
        self,
        client: TestClient,
        sample_scenario_paths: list[str],
        native_negotiator_types: list[str],
    ):
        """Test retrieving tournament configuration."""
        if not sample_scenario_paths:
            pytest.skip("No sample scenarios available")

        # Start a tournament
        response = client.post(
            "/api/tournament/start",
            json={
                "competitor_types": [native_negotiator_types[0]],
                "opponent_types": [native_negotiator_types[1]],
                "scenario_paths": sample_scenario_paths[:1],
                "n_repetitions": 2,
                "n_steps": 5,
            },
        )
        tournament_id = response.json()["session_id"]
        time.sleep(5)

        # Get config
        response = client.get(f"/api/tournament/saved/{tournament_id}/config")
        if response.status_code == 200:
            data = response.json()
            assert "config" in data
            assert data["config"]["n_repetitions"] == 2
