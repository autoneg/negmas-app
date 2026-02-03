"""Tests for scenario API endpoints.

This module tests the /api/scenarios endpoints to prevent regressions.
"""

import base64
import pytest
from fastapi.testclient import TestClient
from pathlib import Path


@pytest.fixture
def camera_b_scenario():
    """Get CameraB scenario path (from negmas source).

    Tries multiple possible locations where negmas package might be installed.
    """
    possible_paths = [
        # Development paths
        Path.home() / "code/projects/negmas/src/negmas/scenarios/CameraB",
        Path.home() / "code/negmas/src/negmas/scenarios/CameraB",
        # Try to find it in the negmas package
    ]

    for path in possible_paths:
        if path.exists():
            return str(path)

    # Try to find it via negmas package
    try:
        import negmas

        negmas_path = Path(negmas.__file__).parent / "scenarios" / "CameraB"
        if negmas_path.exists():
            return str(negmas_path)
    except Exception:
        pass

    return None


@pytest.fixture
def app_scenario():
    """Get an app scenario path (from ~/negmas/app/scenarios)."""
    # Try to find a scenario in the app directory
    app_scenarios = Path.home() / "negmas/app/scenarios"
    if app_scenarios.exists():
        # Look for ANAC scenarios
        for year_dir in app_scenarios.iterdir():
            if year_dir.is_dir() and "anac" in year_dir.name.lower():
                for scenario_dir in year_dir.iterdir():
                    if scenario_dir.is_dir():
                        return str(scenario_dir)
    return None


def encode_path(path: str) -> str:
    """Encode a path for use in URLs."""
    return base64.urlsafe_b64encode(path.encode()).decode()


class TestScenarioEndpoints:
    """Tests for /api/scenarios endpoints."""

    def test_list_scenarios(self, client: TestClient):
        """Test listing scenarios."""
        response = client.get("/api/scenarios")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        assert isinstance(data["scenarios"], list)

    def test_list_sources(self, client: TestClient):
        """Test listing scenario sources."""
        response = client.get("/api/scenarios/sources")
        assert response.status_code == 200
        data = response.json()
        assert "sources" in data
        assert isinstance(data["sources"], list)
        # Should have at least 'negmas' source
        assert "negmas" in data["sources"] or "app" in data["sources"]

    def test_get_scenario_ufuns_negmas_source(
        self, client: TestClient, camera_b_scenario: str | None
    ):
        """Test getting ufun details for CameraB (negmas source, XML format).

        This test prevents regression of the 500 error:
        'str' object has no attribute 'relative_to'
        """
        if camera_b_scenario is None:
            pytest.skip("CameraB scenario not available")

        scenario_id = encode_path(camera_b_scenario)
        response = client.get(f"/api/scenarios/{scenario_id}/ufuns")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "ufuns" in data
        assert len(data["ufuns"]) == 2

        # Check first ufun has proper structure
        ufun = data["ufuns"][0]
        assert "name" in ufun
        assert "type" in ufun
        assert "string_representation" in ufun
        assert "file_path" in ufun

        # Verify detailed representation includes weights and type
        assert "Type:" in ufun["string_representation"]
        assert (
            "Weights:" in ufun["string_representation"]
            or "Discount:" in ufun["string_representation"]
        )

        # Verify file_path is a relative path (not absolute)
        assert ufun["file_path"] is not None
        assert not ufun["file_path"].startswith("/")
        # File can be XML or YAML depending on scenario format
        assert ufun["file_path"].endswith((".xml", ".yaml", ".yml"))

        # Check files info
        assert "files" in data
        assert data["files"]["domain_file"] is not None
        assert len(data["files"]["utility_files"]) == 2

    def test_get_scenario_ufuns_app_source(
        self, client: TestClient, app_scenario: str | None
    ):
        """Test getting ufun details for app scenario (YAML format).

        This ensures the fix works for both XML and YAML formats.
        """
        if app_scenario is None:
            pytest.skip("App scenario not available")

        scenario_id = encode_path(app_scenario)
        response = client.get(f"/api/scenarios/{scenario_id}/ufuns")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "ufuns" in data
        assert len(data["ufuns"]) >= 2

        # Check ufun structure
        ufun = data["ufuns"][0]
        assert "name" in ufun
        assert "type" in ufun
        assert "string_representation" in ufun

        # Verify detailed representation
        assert "Type:" in ufun["string_representation"]

        # YAML scenarios should have file paths
        if ufun["file_path"] is not None:
            assert not ufun["file_path"].startswith("/")
            assert ufun["file_path"].endswith(".yml") or ufun["file_path"].endswith(
                ".yaml"
            )

    def test_calculate_stats_with_encoded_id(
        self, client: TestClient, camera_b_scenario: str | None
    ):
        """Test calculating stats using base64-encoded scenario ID.

        This prevents regression of the 404 error where the frontend
        was passing raw paths instead of encoded IDs.
        """
        if camera_b_scenario is None:
            pytest.skip("CameraB scenario not available")

        scenario_id = encode_path(camera_b_scenario)
        response = client.post(
            f"/api/scenarios/{scenario_id}/stats/calculate?force=true"
        )

        # Should return 200, not 404
        assert response.status_code == 200
        data = response.json()

        # Should have stats data
        assert "n_outcomes" in data or "opposition" in data

    def test_get_stats_with_encoded_id(
        self, client: TestClient, camera_b_scenario: str | None
    ):
        """Test getting stats using base64-encoded scenario ID."""
        if camera_b_scenario is None:
            pytest.skip("CameraB scenario not available")

        scenario_id = encode_path(camera_b_scenario)

        # First calculate stats
        client.post(f"/api/scenarios/{scenario_id}/stats/calculate?force=true")

        # Then retrieve them
        response = client.get(f"/api/scenarios/{scenario_id}/stats")

        assert response.status_code == 200
        data = response.json()
        assert "has_stats" in data

    def test_get_plot_data_with_encoded_id(
        self, client: TestClient, camera_b_scenario: str | None
    ):
        """Test getting plot data using base64-encoded scenario ID."""
        if camera_b_scenario is None:
            pytest.skip("CameraB scenario not available")

        scenario_id = encode_path(camera_b_scenario)
        response = client.get(
            f"/api/scenarios/{scenario_id}/plot-data?max_samples=1000&force_regenerate=false"
        )

        assert response.status_code == 200
        data = response.json()
        assert "outcome_utilities" in data
        assert "negotiator_names" in data
        assert len(data["negotiator_names"]) == 2

    def test_ufun_representation_types(
        self,
        client: TestClient,
        camera_b_scenario: str | None,
        app_scenario: str | None,
    ):
        """Test that ufun representations show useful information, not just Nash utility.

        Verifies that different ufun types show appropriate details:
        - LinearAdditiveUtilityFunction: shows weights
        - ExpDiscountedUFun: shows discount factor and base ufun
        """
        test_cases = [
            (camera_b_scenario, "ExpDiscountedUFun", ["Discount:", "Weights:"]),
            (app_scenario, "LinearAdditiveUtilityFunction", ["Weights:", "Reserved:"]),
        ]

        for scenario_path, expected_type, expected_fields in test_cases:
            if scenario_path is None:
                continue

            scenario_id = encode_path(scenario_path)
            response = client.get(f"/api/scenarios/{scenario_id}/ufuns")

            assert response.status_code == 200
            data = response.json()

            # Find ufun of expected type
            found = False
            for ufun in data["ufuns"]:
                if expected_type in ufun["type"]:
                    found = True
                    # Check that representation contains expected fields
                    for field in expected_fields:
                        assert field in ufun["string_representation"], (
                            f"Expected '{field}' in representation for {expected_type}, "
                            f"got: {ufun['string_representation']}"
                        )
                    break

            if not found:
                pytest.skip(f"No ufun of type {expected_type} found in {scenario_path}")

    def test_plot_data_includes_reserved_values(
        self, client: TestClient, app_scenario: str | None
    ):
        """Test that plot data includes reserved values for plotting.

        This prevents regression where reserved value lines weren't showing
        in the interactive plot.
        """
        if app_scenario is None:
            pytest.skip("App scenario not available")

        scenario_id = encode_path(app_scenario)
        response = client.get(
            f"/api/scenarios/{scenario_id}/plot-data?max_samples=1000&force_regenerate=false"
        )

        assert response.status_code == 200
        data = response.json()

        # Should have reserved_values field
        assert "reserved_values" in data or "outcome_utilities" in data

        # If reserved_values is present, it should match number of negotiators
        if "reserved_values" in data and data["reserved_values"]:
            assert len(data["reserved_values"]) == len(data["negotiator_names"])

    def test_file_editor_get_content(
        self, client: TestClient, camera_b_scenario: str | None
    ):
        """Test getting file content for editing.

        Verifies that the file editor can load actual file content.
        """
        if camera_b_scenario is None:
            pytest.skip("CameraB scenario not available")

        scenario_id = encode_path(camera_b_scenario)

        # Get ufuns to find a file path
        ufuns_response = client.get(f"/api/scenarios/{scenario_id}/ufuns")
        assert ufuns_response.status_code == 200
        ufuns_data = ufuns_response.json()

        if not ufuns_data["ufuns"] or not ufuns_data["ufuns"][0].get("file_path"):
            pytest.skip("No file path available")

        file_path = ufuns_data["ufuns"][0]["file_path"]

        # Get file content
        response = client.get(f"/api/scenarios/{scenario_id}/files/{file_path}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "content" in data
        assert len(data["content"]) > 0  # Should have actual content
        assert data["file_path"] == file_path

        # For XML files, content should contain XML tags
        if file_path.endswith(".xml"):
            assert "<" in data["content"] and ">" in data["content"]
