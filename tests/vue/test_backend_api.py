"""
Backend API tests for Vue.js frontend.

Tests all API endpoints used by the Vue frontend to ensure they return
the correct data format and handle errors properly.
"""

import pytest
from fastapi.testclient import TestClient


class TestScenariosAPI:
    """Tests for /api/scenarios endpoints."""

    def test_list_scenarios(self, client: TestClient):
        """Test listing available scenarios."""
        response = client.get("/api/scenarios/list")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        assert isinstance(data["scenarios"], list)

    def test_get_scenario_details(self, client: TestClient, sample_scenario_path: str):
        """Test getting scenario details."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        response = client.get(f"/api/scenarios/details?path={sample_scenario_path}")
        assert response.status_code == 200
        data = response.json()
        assert "path" in data
        assert "n_outcomes" in data
        assert "outcome_space" in data

    def test_get_scenario_stats(self, client: TestClient, sample_scenario_path: str):
        """Test getting scenario statistics."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        response = client.get(f"/api/scenarios/stats?path={sample_scenario_path}")
        assert response.status_code == 200
        data = response.json()
        assert "pareto_front" in data or "error" in data

    def test_get_scenario_plot_data(
        self, client: TestClient, sample_scenario_path: str
    ):
        """Test getting scenario plot data."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        response = client.get(f"/api/scenarios/plot-data?path={sample_scenario_path}")
        assert response.status_code == 200
        data = response.json()
        # Should have data for 2D or 3D plots
        assert isinstance(data, dict)


class TestNegotiatorsAPI:
    """Tests for /api/negotiators endpoints."""

    def test_list_negotiators(self, client: TestClient):
        """Test listing available negotiators."""
        response = client.get("/api/negotiators/list")
        assert response.status_code == 200
        data = response.json()
        assert "negotiators" in data
        assert isinstance(data["negotiators"], list)
        if data["negotiators"]:
            negotiator = data["negotiators"][0]
            assert "type_name" in negotiator
            assert "module" in negotiator
            assert "package" in negotiator

    def test_get_negotiator_params(
        self, client: TestClient, native_negotiator_types: list[str]
    ):
        """Test getting negotiator parameters via inspection."""
        if not native_negotiator_types:
            pytest.skip("No negotiators available")

        type_name = native_negotiator_types[0]
        response = client.get(f"/api/negotiators/params?type_name={type_name}")
        assert response.status_code == 200
        data = response.json()
        assert "parameters" in data
        assert isinstance(data["parameters"], list)

    def test_list_virtual_negotiators(self, client: TestClient):
        """Test listing virtual negotiators."""
        response = client.get("/api/negotiators/virtual/list")
        assert response.status_code == 200
        data = response.json()
        assert "virtual_negotiators" in data
        assert isinstance(data["virtual_negotiators"], list)


class TestNegotiationAPI:
    """Tests for /api/negotiation endpoints."""

    def test_list_sessions(self, client: TestClient):
        """Test listing negotiation sessions."""
        response = client.get("/api/negotiation/sessions/list")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_start_negotiation(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test starting a negotiation."""
        if sample_scenario_path is None or len(native_negotiator_types) < 2:
            pytest.skip("Missing test requirements")

        response = client.post(
            "/api/negotiation/start",
            json={
                "scenario_path": sample_scenario_path,
                "negotiators": [
                    {"type_name": native_negotiator_types[0], "name": "Agent1"},
                    {"type_name": native_negotiator_types[1], "name": "Agent2"},
                ],
                "mechanism_type": "SAOMechanism",
                "mechanism_params": {"n_steps": 10},
                "step_delay": 0.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "stream_url" in data

    def test_get_session_status(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test getting session status."""
        if sample_scenario_path is None or len(native_negotiator_types) < 2:
            pytest.skip("Missing test requirements")

        # Start a negotiation first
        start_response = client.post(
            "/api/negotiation/start",
            json={
                "scenario_path": sample_scenario_path,
                "negotiators": [
                    {"type_name": native_negotiator_types[0], "name": "Agent1"},
                    {"type_name": native_negotiator_types[1], "name": "Agent2"},
                ],
                "mechanism_type": "SAOMechanism",
                "mechanism_params": {"n_steps": 5},
                "step_delay": 0.0,
            },
        )
        session_id = start_response.json()["session_id"]

        # Get status
        response = client.get(f"/api/negotiation/sessions/{session_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "current_step" in data


class TestTournamentAPI:
    """Tests for /api/tournament endpoints."""

    def test_list_tournaments(self, client: TestClient):
        """Test listing tournaments."""
        response = client.get("/api/tournament/list")
        assert response.status_code == 200
        data = response.json()
        assert "tournaments" in data
        assert isinstance(data["tournaments"], list)

    def test_start_tournament(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test starting a tournament."""
        if sample_scenario_path is None or len(native_negotiator_types) < 2:
            pytest.skip("Missing test requirements")

        response = client.post(
            "/api/tournament/start",
            json={
                "name": "Test Tournament",
                "competitors": [
                    {"type_name": native_negotiator_types[0], "name": "Agent1"}
                ],
                "opponents": [
                    {"type_name": native_negotiator_types[1], "name": "Agent2"}
                ],
                "scenarios": [sample_scenario_path],
                "n_repetitions": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "tournament_id" in data
        assert "stream_url" in data


class TestSettingsAPI:
    """Tests for /api/settings endpoints."""

    def test_get_settings(self, client: TestClient):
        """Test getting current settings."""
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        assert "general" in data
        assert "negotiation" in data
        assert "genius_bridge" in data
        assert "paths" in data
        assert "performance" in data

    def test_update_settings(self, client: TestClient):
        """Test updating settings."""
        # Get current settings
        current = client.get("/api/settings").json()

        # Toggle dark mode
        current["general"]["dark_mode"] = not current["general"]["dark_mode"]

        # Update
        response = client.put("/api/settings", json=current)
        assert response.status_code == 200

        # Verify update
        updated = client.get("/api/settings").json()
        assert updated["general"]["dark_mode"] == current["general"]["dark_mode"]

    def test_reset_settings(self, client: TestClient):
        """Test resetting settings to defaults."""
        response = client.post("/api/settings/reset")
        assert response.status_code == 200

        # Verify defaults are applied
        settings = client.get("/api/settings").json()
        assert settings["general"]["dark_mode"] == False
        assert settings["negotiation"]["default_max_steps"] == 100
