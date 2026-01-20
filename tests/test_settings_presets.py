"""
Tests for settings API endpoints - specifically preset and recent session endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestSessionPresetsAPI:
    """Tests for /api/settings/presets/sessions endpoints."""

    def test_get_session_presets_empty(self, client: TestClient):
        """Test getting session presets when none exist."""
        response = client.get("/api/settings/presets/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert isinstance(data["presets"], list)

    def test_save_session_preset(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test saving a session preset."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        preset_data = {
            "name": "Test Preset",
            "scenario_path": sample_scenario_path,
            "scenario_name": "Test Scenario",
            "negotiators": [
                {
                    "type_name": native_negotiator_types[0],
                    "name": "Agent1",
                    "source": "native",
                    "requires_bridge": False,
                    "params": {},
                },
                {
                    "type_name": native_negotiator_types[1],
                    "name": "Agent2",
                    "source": "native",
                    "requires_bridge": False,
                    "params": {},
                },
            ],
            "mechanism_type": "SAOMechanism",
            "mechanism_params": {"n_steps": 100},
            "share_ufuns": False,
            "mode": "realtime",
            "step_delay": 100,
            "show_plot": True,
            "show_offers": True,
        }

        response = client.post("/api/settings/presets/sessions", json=preset_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Preset"
        assert data["scenario_path"] == sample_scenario_path
        assert len(data["negotiators"]) == 2

    def test_get_session_presets_after_save(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test that saved presets appear in the list."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        # Save a preset
        preset_data = {
            "name": "Test Preset 2",
            "scenario_path": sample_scenario_path,
            "scenario_name": "Test Scenario",
            "negotiators": [
                {
                    "type_name": native_negotiator_types[0],
                    "name": "Agent1",
                    "source": "native",
                    "requires_bridge": False,
                    "params": {},
                }
            ],
            "mechanism_type": "SAOMechanism",
            "mechanism_params": {},
        }
        client.post("/api/settings/presets/sessions", json=preset_data)

        # Get presets
        response = client.get("/api/settings/presets/sessions")
        assert response.status_code == 200
        data = response.json()
        preset_names = [p["name"] for p in data["presets"]]
        assert "Test Preset 2" in preset_names

    def test_delete_session_preset(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test deleting a session preset."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        # Save a preset
        preset_data = {
            "name": "Preset To Delete",
            "scenario_path": sample_scenario_path,
            "scenario_name": "Test Scenario",
            "negotiators": [],
        }
        client.post("/api/settings/presets/sessions", json=preset_data)

        # Delete it
        response = client.delete("/api/settings/presets/sessions/Preset To Delete")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify it's gone
        response = client.get("/api/settings/presets/sessions")
        preset_names = [p["name"] for p in response.json()["presets"]]
        assert "Preset To Delete" not in preset_names

    def test_delete_nonexistent_preset(self, client: TestClient):
        """Test deleting a preset that doesn't exist."""
        response = client.delete("/api/settings/presets/sessions/NonExistent")
        # Should still return success: false or handle gracefully
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False


class TestRecentSessionsAPI:
    """Tests for /api/settings/presets/recent endpoints."""

    def test_get_recent_sessions_empty(self, client: TestClient):
        """Test getting recent sessions when none exist."""
        # Clear first
        client.delete("/api/settings/presets/recent")

        response = client.get("/api/settings/presets/recent")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_add_recent_session(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test adding a session to recent history."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        session_data = {
            "scenario_path": sample_scenario_path,
            "scenario_name": "Recent Test Scenario",
            "negotiators": [
                {
                    "type_name": native_negotiator_types[0],
                    "name": "Agent1",
                    "source": "native",
                    "requires_bridge": False,
                    "params": {},
                }
            ],
            "mechanism_type": "SAOMechanism",
            "mechanism_params": {"n_steps": 50},
        }

        response = client.post("/api/settings/presets/recent", json=session_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_recent_sessions_after_add(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test that added sessions appear in recent list."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        # Add a session
        session_data = {
            "scenario_path": sample_scenario_path,
            "scenario_name": "Recent Test 2",
            "negotiators": [],
        }
        client.post("/api/settings/presets/recent", json=session_data)

        # Get recent sessions
        response = client.get("/api/settings/presets/recent")
        assert response.status_code == 200
        data = response.json()
        scenario_names = [s["scenario_name"] for s in data["sessions"]]
        assert "Recent Test 2" in scenario_names

    def test_recent_sessions_limit(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test that recent sessions are limited to 10 most recent."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        # Clear recent
        client.delete("/api/settings/presets/recent")

        # Add 15 sessions
        for i in range(15):
            session_data = {
                "scenario_path": sample_scenario_path,
                "scenario_name": f"Recent Session {i}",
                "negotiators": [],
            }
            client.post("/api/settings/presets/recent", json=session_data)

        # Get recent - should only have 10
        response = client.get("/api/settings/presets/recent")
        data = response.json()
        assert len(data["sessions"]) <= 10

    def test_clear_recent_sessions(self, client: TestClient):
        """Test clearing all recent sessions."""
        response = client.delete("/api/settings/presets/recent")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify empty
        response = client.get("/api/settings/presets/recent")
        data = response.json()
        assert len(data["sessions"]) == 0


class TestTournamentPresetsAPI:
    """Tests for /api/settings/presets/tournaments endpoints."""

    def test_get_tournament_presets_empty(self, client: TestClient):
        """Test getting tournament presets when none exist."""
        response = client.get("/api/settings/presets/tournaments")
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert isinstance(data["presets"], list)

    def test_save_tournament_preset(
        self,
        client: TestClient,
        sample_scenario_paths: list[str],
        native_negotiator_types: list[str],
    ):
        """Test saving a tournament preset."""
        if not sample_scenario_paths:
            pytest.skip("No sample scenarios available")

        preset_data = {
            "name": "Test Tournament Preset",
            "scenario_paths": sample_scenario_paths[:2],
            "competitor_types": native_negotiator_types[:2],
            "competitor_configs": {},
            "n_repetitions": 3,
            "rotate_ufuns": True,
            "self_play": False,
            "mechanism_type": "SAOMechanism",
            "n_steps": 100,
            "final_score_metric": "advantage",
            "final_score_stat": "mean",
        }

        response = client.post("/api/settings/presets/tournaments", json=preset_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Tournament Preset"
        assert len(data["scenario_paths"]) == 2
        assert data["n_repetitions"] == 3
        assert data["self_play"] is False

    def test_get_tournament_presets_after_save(
        self,
        client: TestClient,
        sample_scenario_paths: list[str],
        native_negotiator_types: list[str],
    ):
        """Test that saved tournament presets appear in the list."""
        if not sample_scenario_paths:
            pytest.skip("No sample scenarios available")

        # Save a preset
        preset_data = {
            "name": "Test Tournament 2",
            "scenario_paths": sample_scenario_paths[:1],
            "competitor_types": native_negotiator_types[:2],
        }
        client.post("/api/settings/presets/tournaments", json=preset_data)

        # Get presets
        response = client.get("/api/settings/presets/tournaments")
        assert response.status_code == 200
        data = response.json()
        preset_names = [p["name"] for p in data["presets"]]
        assert "Test Tournament 2" in preset_names

    def test_delete_tournament_preset(
        self,
        client: TestClient,
        sample_scenario_paths: list[str],
        native_negotiator_types: list[str],
    ):
        """Test deleting a tournament preset."""
        if not sample_scenario_paths:
            pytest.skip("No sample scenarios available")

        # Save a preset
        preset_data = {
            "name": "Tournament To Delete",
            "scenario_paths": sample_scenario_paths[:1],
            "competitor_types": native_negotiator_types[:1],
        }
        client.post("/api/settings/presets/tournaments", json=preset_data)

        # Delete it
        response = client.delete(
            "/api/settings/presets/tournaments/Tournament To Delete"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify it's gone
        response = client.get("/api/settings/presets/tournaments")
        preset_names = [p["name"] for p in response.json()["presets"]]
        assert "Tournament To Delete" not in preset_names

    def test_tournament_preset_all_fields(
        self,
        client: TestClient,
        sample_scenario_paths: list[str],
        native_negotiator_types: list[str],
    ):
        """Test saving a tournament preset with all fields populated."""
        if not sample_scenario_paths:
            pytest.skip("No sample scenarios available")

        preset_data = {
            "name": "Complete Tournament Preset",
            "scenario_paths": sample_scenario_paths[:2],
            "competitor_types": native_negotiator_types[:2],
            "competitor_configs": {},
            "n_repetitions": 5,
            "rotate_ufuns": True,
            "self_play": True,
            "mechanism_type": "SAOMechanism",
            "n_steps_min": 50,
            "n_steps_max": 200,
            "time_limit": 60.0,
            "step_time_limit": 1.0,
            "negotiator_time_limit": 30.0,
            "final_score_metric": "utility",
            "final_score_stat": "median",
            "randomize_runs": True,
            "sort_runs": False,
            "id_reveals_type": True,
            "name_reveals_type": False,
            "save_stats": True,
            "save_scenario_figs": True,
        }

        response = client.post("/api/settings/presets/tournaments", json=preset_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Complete Tournament Preset"
        assert data["n_steps_min"] == 50
        assert data["n_steps_max"] == 200
        assert data["randomize_runs"] is True
        assert data["id_reveals_type"] is True
