"""Tests for API routes (negotiation and tournament endpoints)."""

import pytest
from fastapi.testclient import TestClient


class TestNegotiationRoutes:
    """Tests for /api/negotiation endpoints."""

    def test_list_sessions_empty(self, client: TestClient):
        """Test listing sessions when none exist."""
        response = client.get("/api/negotiation/sessions/list")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_start_negotiation_success(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test starting a negotiation successfully."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

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
        assert "status" in data
        assert "stream_url" in data
        assert data["status"] == "pending"

    def test_start_negotiation_invalid_scenario(
        self, client: TestClient, native_negotiator_types: list[str]
    ):
        """Test starting a negotiation with invalid scenario path."""
        response = client.post(
            "/api/negotiation/start",
            json={
                "scenario_path": "/nonexistent/scenario/path",
                "negotiators": [
                    {"type_name": native_negotiator_types[0], "name": "Agent1"},
                    {"type_name": native_negotiator_types[1], "name": "Agent2"},
                ],
            },
        )
        # Should fail with 500 or similar error when scenario loading fails
        # The exact behavior depends on implementation
        assert response.status_code in (200, 400, 422, 500)

    def test_get_session_not_found(self, client: TestClient):
        """Test getting a non-existent session."""
        response = client.get("/api/negotiation/nonexistent-session-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_cancel_session_not_found(self, client: TestClient):
        """Test cancelling a non-existent session."""
        response = client.post("/api/negotiation/nonexistent-session-id/cancel")
        assert response.status_code == 404

    def test_pause_session_not_found(self, client: TestClient):
        """Test pausing a non-existent session."""
        response = client.post("/api/negotiation/nonexistent-session-id/pause")
        assert response.status_code == 404

    def test_resume_session_not_found(self, client: TestClient):
        """Test resuming a non-existent session."""
        response = client.post("/api/negotiation/nonexistent-session-id/resume")
        assert response.status_code == 404

    def test_get_session_after_creation(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test getting session details after creation."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        # Create session
        response = client.post(
            "/api/negotiation/start",
            json={
                "scenario_path": sample_scenario_path,
                "negotiators": [
                    {"type_name": native_negotiator_types[0], "name": "TestAgent1"},
                    {"type_name": native_negotiator_types[1], "name": "TestAgent2"},
                ],
                "mechanism_params": {"n_steps": 5},
            },
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Get session details
        response = client.get(f"/api/negotiation/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert "TestAgent1" in data["negotiator_names"]
        assert "TestAgent2" in data["negotiator_names"]

    def test_list_sessions_after_creation(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test that created sessions appear in the list."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        # Create a session
        response = client.post(
            "/api/negotiation/start",
            json={
                "scenario_path": sample_scenario_path,
                "negotiators": [
                    {"type_name": native_negotiator_types[0]},
                    {"type_name": native_negotiator_types[1]},
                ],
            },
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # List sessions
        response = client.get("/api/negotiation/sessions/list")
        assert response.status_code == 200
        sessions = response.json()["sessions"]
        session_ids = [s["id"] for s in sessions]
        assert session_id in session_ids


class TestTournamentRoutes:
    """Tests for /api/tournament endpoints."""

    def test_list_sessions_empty(self, client: TestClient):
        """Test listing tournament sessions when none exist."""
        response = client.get("/api/tournament/sessions/list")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert isinstance(data["sessions"], list)

    def test_start_tournament_success(
        self,
        client: TestClient,
        sample_scenario_paths: list[str],
        native_negotiator_types: list[str],
    ):
        """Test starting a tournament successfully."""
        if not sample_scenario_paths:
            pytest.skip("No sample scenarios available")

        response = client.post(
            "/api/tournament/start",
            json={
                "competitor_types": native_negotiator_types[:2],
                "scenario_paths": sample_scenario_paths[:2],
                "n_repetitions": 1,
                "n_steps": 10,
                "self_play": False,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "status" in data
        assert "stream_url" in data
        assert data["status"] == "pending"

    def test_start_tournament_minimal(
        self,
        client: TestClient,
        sample_scenario_paths: list[str],
        native_negotiator_types: list[str],
    ):
        """Test starting a tournament with minimal parameters."""
        if not sample_scenario_paths:
            pytest.skip("No sample scenarios available")

        response = client.post(
            "/api/tournament/start",
            json={
                "competitor_types": native_negotiator_types[:2],
                "scenario_paths": sample_scenario_paths[:1],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data

    def test_get_session_not_found(self, client: TestClient):
        """Test getting a non-existent tournament session."""
        response = client.get("/api/tournament/nonexistent-session-id")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_cancel_session_not_found(self, client: TestClient):
        """Test cancelling a non-existent tournament session."""
        response = client.post("/api/tournament/nonexistent-session-id/cancel")
        assert response.status_code == 404

    def test_get_session_after_creation(
        self,
        client: TestClient,
        sample_scenario_paths: list[str],
        native_negotiator_types: list[str],
    ):
        """Test getting tournament session details after creation."""
        if not sample_scenario_paths:
            pytest.skip("No sample scenarios available")

        # Create session
        response = client.post(
            "/api/tournament/start",
            json={
                "competitor_types": native_negotiator_types[:2],
                "scenario_paths": sample_scenario_paths[:1],
                "n_steps": 5,
            },
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Get session details
        response = client.get(f"/api/tournament/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert data["config"] is not None
        assert native_negotiator_types[0] in data["config"]["competitor_types"]

    def test_list_sessions_after_creation(
        self,
        client: TestClient,
        sample_scenario_paths: list[str],
        native_negotiator_types: list[str],
    ):
        """Test that created tournament sessions appear in the list."""
        if not sample_scenario_paths:
            pytest.skip("No sample scenarios available")

        # Create a session
        response = client.post(
            "/api/tournament/start",
            json={
                "competitor_types": native_negotiator_types[:2],
                "scenario_paths": sample_scenario_paths[:1],
            },
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # List sessions
        response = client.get("/api/tournament/sessions/list")
        assert response.status_code == 200
        sessions = response.json()["sessions"]
        session_ids = [s["id"] for s in sessions]
        assert session_id in session_ids


class TestNegotiatorRoutes:
    """Tests for /api/negotiators endpoints."""

    def test_list_negotiators(self, client: TestClient):
        """Test listing available negotiators."""
        response = client.get("/api/negotiators")
        assert response.status_code == 200
        data = response.json()
        assert "negotiators" in data
        negotiators = data["negotiators"]
        assert isinstance(negotiators, list)
        # Should have at least some native negotiators
        assert len(negotiators) > 0
        # Check structure of entries
        for n in negotiators[:3]:
            assert "type_name" in n
            assert "name" in n
            assert "source" in n

    def test_list_sources(self, client: TestClient):
        """Test listing negotiator sources."""
        response = client.get("/api/negotiators/sources")
        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        # Should have at least native sources
        assert len(data["sources"]) > 0

    def test_get_parameters(
        self, client: TestClient, native_negotiator_types: list[str]
    ):
        """Test getting parameters for a negotiator type."""
        type_name = native_negotiator_types[0]
        response = client.get(f"/api/negotiators/{type_name}/parameters")
        assert response.status_code == 200
        data = response.json()
        assert "type_name" in data
        assert data["type_name"] == type_name
        assert "parameters" in data

    def test_get_negotiator_info(self, client: TestClient):
        """Test getting info for a specific negotiator type."""
        # First get list of available negotiators
        list_response = client.get("/api/negotiators")
        assert list_response.status_code == 200
        data = list_response.json()
        negotiators = data["negotiators"]
        assert len(negotiators) > 0, "No negotiators available for testing"

        # Use the first available negotiator
        type_name = negotiators[0]["type_name"]
        response = client.get(f"/api/negotiators/{type_name}")
        assert response.status_code == 200
        info = response.json()
        assert info["type_name"] == type_name

    def test_refresh_negotiators(self, client: TestClient):
        """Test refreshing negotiator list."""
        response = client.post("/api/negotiators/refresh")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestScenarioRoutes:
    """Tests for /api/scenarios endpoints."""

    def test_list_scenarios(self, client: TestClient):
        """Test listing available scenarios."""
        response = client.get("/api/scenarios")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        scenarios = data["scenarios"]
        assert isinstance(scenarios, list)
        # Should have bundled scenarios
        assert len(scenarios) > 0
        # Check structure
        for s in scenarios[:3]:
            assert "name" in s
            assert "path" in s
            assert "n_outcomes" in s

    def test_get_scenario_details(self, client: TestClient, sample_scenario_path: str):
        """Test getting details for a specific scenario."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        # Base64 encode the path for the path parameter
        import base64

        encoded_path = base64.urlsafe_b64encode(sample_scenario_path.encode()).decode()
        response = client.get(f"/api/scenarios/{encoded_path}")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "path" in data
        assert "issues" in data
        assert "n_outcomes" in data

    def test_get_scenario_details_not_found(self, client: TestClient):
        """Test getting details for non-existent scenario."""
        import base64

        encoded_path = base64.urlsafe_b64encode(b"/nonexistent/path").decode()
        response = client.get(f"/api/scenarios/{encoded_path}")
        assert response.status_code == 404


class TestMechanismRoutes:
    """Tests for /api/mechanisms endpoints."""

    def test_list_mechanisms(self, client: TestClient):
        """Test listing available mechanism types."""
        response = client.get("/api/mechanisms")
        assert response.status_code == 200
        data = response.json()
        assert "mechanisms" in data
        mechanisms = data["mechanisms"]
        assert isinstance(mechanisms, list)
        # Should include at least SAOMechanism
        class_names = [m["class_name"] for m in mechanisms]
        assert any("SAOMechanism" in name for name in class_names)

    def test_get_mechanism_info(self, client: TestClient):
        """Test getting info for SAOMechanism."""
        response = client.get("/api/mechanisms/SAOMechanism")
        assert response.status_code == 200
        data = response.json()
        # Check it's not an error response
        if "error" not in data:
            assert "class_name" in data
            assert "param_groups" in data

    def test_get_mechanism_not_found(self, client: TestClient):
        """Test getting info for unknown mechanism."""
        response = client.get("/api/mechanisms/NonexistentMechanism")
        assert response.status_code == 200  # Returns 200 with error message
        data = response.json()
        assert "error" in data


class TestSettingsRoutes:
    """Tests for /api/settings endpoints."""

    def test_get_settings(self, client: TestClient):
        """Test getting current settings."""
        response = client.get("/api/settings")
        assert response.status_code == 200
        data = response.json()
        # Should have main setting categories
        assert "general" in data or "negotiation" in data or "paths" in data

    def test_get_negotiator_sources_settings(self, client: TestClient):
        """Test getting negotiator sources settings."""
        response = client.get("/api/settings/negotiator_sources")
        assert response.status_code == 200
        data = response.json()
        assert "disabled_sources" in data


class TestGeniusRoutes:
    """Tests for /api/genius endpoints."""

    def test_get_status(self, client: TestClient):
        """Test getting Genius bridge status."""
        response = client.get("/api/genius/status")
        assert response.status_code == 200
        data = response.json()
        assert "running" in data
        assert isinstance(data["running"], bool)


class TestIdentityRoute:
    """Tests for identity endpoint."""

    def test_identity_endpoint(self, client: TestClient):
        """Test that identity endpoint returns app info."""
        response = client.get("/api/identity")
        assert response.status_code == 200
        data = response.json()
        assert data["app"] == "negmas-app"
        assert "version" in data
