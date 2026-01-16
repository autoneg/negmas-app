"""Tests for virtual negotiator endpoints."""

import pytest
from fastapi.testclient import TestClient


class TestVirtualNegotiatorRoutes:
    """Tests for /api/negotiators/virtual endpoints."""

    def test_list_virtual_negotiators_empty(self, client: TestClient):
        """Test listing virtual negotiators when none exist or all are filtered."""
        response = client.get("/api/negotiators/virtual")
        assert response.status_code == 200
        data = response.json()
        assert "virtual_negotiators" in data
        assert "count" in data
        assert isinstance(data["virtual_negotiators"], list)

    def test_create_virtual_negotiator(
        self, client: TestClient, native_negotiator_types: list[str]
    ):
        """Test creating a virtual negotiator."""
        base_type = native_negotiator_types[0]

        response = client.post(
            "/api/negotiators/virtual",
            json={
                "name": "Test Virtual Negotiator",
                "base_type_name": base_type,
                "description": "A test virtual negotiator",
                "params": {"aspiration_type": "linear"},
                "tags": ["test", "automated"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "virtual_negotiator" in data
        assert data["status"] == "created"

        vn = data["virtual_negotiator"]
        assert vn["name"] == "Test Virtual Negotiator"
        assert vn["base_type_name"] == base_type
        assert vn["description"] == "A test virtual negotiator"
        # Should have "virtual" tag auto-added
        assert "virtual" in vn["tags"]
        assert "test" in vn["tags"]
        assert vn["enabled"] is True

        # Cleanup: delete the created negotiator
        client.delete(f"/api/negotiators/virtual/{vn['id']}")

    def test_create_virtual_negotiator_auto_virtual_tag(
        self, client: TestClient, native_negotiator_types: list[str]
    ):
        """Test that 'virtual' tag is automatically added."""
        base_type = native_negotiator_types[0]

        response = client.post(
            "/api/negotiators/virtual",
            json={
                "name": "Test Auto Tag",
                "base_type_name": base_type,
                "tags": ["custom"],
            },
        )
        assert response.status_code == 200
        vn = response.json()["virtual_negotiator"]
        assert "virtual" in vn["tags"]
        assert vn["tags"][0] == "virtual"  # Should be first

        # Cleanup
        client.delete(f"/api/negotiators/virtual/{vn['id']}")

    def test_create_virtual_negotiator_empty_name(
        self, client: TestClient, native_negotiator_types: list[str]
    ):
        """Test creating a virtual negotiator with empty name fails."""
        response = client.post(
            "/api/negotiators/virtual",
            json={
                "name": "",
                "base_type_name": native_negotiator_types[0],
            },
        )
        assert response.status_code == 400

    def test_create_virtual_negotiator_duplicate_name(
        self, client: TestClient, native_negotiator_types: list[str]
    ):
        """Test creating a virtual negotiator with duplicate name fails."""
        base_type = native_negotiator_types[0]
        unique_name = "UniqueTestNegotiator123"

        # Create first
        response = client.post(
            "/api/negotiators/virtual",
            json={"name": unique_name, "base_type_name": base_type},
        )
        assert response.status_code == 200
        vn_id = response.json()["virtual_negotiator"]["id"]

        # Try to create duplicate
        response = client.post(
            "/api/negotiators/virtual",
            json={"name": unique_name, "base_type_name": base_type},
        )
        assert response.status_code == 400

        # Cleanup
        client.delete(f"/api/negotiators/virtual/{vn_id}")

    def test_get_virtual_negotiator(
        self, client: TestClient, native_negotiator_types: list[str]
    ):
        """Test getting a specific virtual negotiator."""
        # Create one first
        response = client.post(
            "/api/negotiators/virtual",
            json={
                "name": "Test Get VN",
                "base_type_name": native_negotiator_types[0],
            },
        )
        assert response.status_code == 200
        vn_id = response.json()["virtual_negotiator"]["id"]

        # Get it
        response = client.get(f"/api/negotiators/virtual/{vn_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["virtual_negotiator"]["id"] == vn_id

        # Cleanup
        client.delete(f"/api/negotiators/virtual/{vn_id}")

    def test_get_virtual_negotiator_not_found(self, client: TestClient):
        """Test getting a non-existent virtual negotiator."""
        response = client.get("/api/negotiators/virtual/nonexistent-id")
        assert response.status_code == 404

    def test_update_virtual_negotiator(
        self, client: TestClient, native_negotiator_types: list[str]
    ):
        """Test updating a virtual negotiator."""
        # Create one first
        response = client.post(
            "/api/negotiators/virtual",
            json={
                "name": "Test Update VN",
                "base_type_name": native_negotiator_types[0],
                "description": "Original",
            },
        )
        assert response.status_code == 200
        vn_id = response.json()["virtual_negotiator"]["id"]

        # Update it
        response = client.put(
            f"/api/negotiators/virtual/{vn_id}",
            json={
                "name": "Updated Name",
                "description": "Updated description",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "updated"
        assert data["virtual_negotiator"]["name"] == "Updated Name"
        assert data["virtual_negotiator"]["description"] == "Updated description"

        # Cleanup
        client.delete(f"/api/negotiators/virtual/{vn_id}")

    def test_delete_virtual_negotiator(
        self, client: TestClient, native_negotiator_types: list[str]
    ):
        """Test deleting a virtual negotiator."""
        # Create one first
        response = client.post(
            "/api/negotiators/virtual",
            json={
                "name": "Test Delete VN",
                "base_type_name": native_negotiator_types[0],
            },
        )
        assert response.status_code == 200
        vn_id = response.json()["virtual_negotiator"]["id"]

        # Delete it
        response = client.delete(f"/api/negotiators/virtual/{vn_id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

        # Verify it's gone
        response = client.get(f"/api/negotiators/virtual/{vn_id}")
        assert response.status_code == 404

    def test_delete_virtual_negotiator_not_found(self, client: TestClient):
        """Test deleting a non-existent virtual negotiator."""
        response = client.delete("/api/negotiators/virtual/nonexistent-id")
        assert response.status_code == 404

    def test_enable_disable_virtual_negotiator(
        self, client: TestClient, native_negotiator_types: list[str]
    ):
        """Test enabling and disabling a virtual negotiator."""
        # Create one first
        response = client.post(
            "/api/negotiators/virtual",
            json={
                "name": "Test Enable Disable VN",
                "base_type_name": native_negotiator_types[0],
            },
        )
        assert response.status_code == 200
        vn = response.json()["virtual_negotiator"]
        vn_id = vn["id"]
        assert vn["enabled"] is True

        # Disable it
        response = client.post(f"/api/negotiators/virtual/{vn_id}/disable")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disabled"
        assert data["virtual_negotiator"]["enabled"] is False

        # Enable it
        response = client.post(f"/api/negotiators/virtual/{vn_id}/enable")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "enabled"
        assert data["virtual_negotiator"]["enabled"] is True

        # Cleanup
        client.delete(f"/api/negotiators/virtual/{vn_id}")

    def test_list_virtual_negotiators_filter_disabled(
        self, client: TestClient, native_negotiator_types: list[str]
    ):
        """Test that disabled virtual negotiators are filtered by default."""
        # Create two negotiators
        response = client.post(
            "/api/negotiators/virtual",
            json={
                "name": "Enabled VN",
                "base_type_name": native_negotiator_types[0],
            },
        )
        assert response.status_code == 200
        enabled_id = response.json()["virtual_negotiator"]["id"]

        response = client.post(
            "/api/negotiators/virtual",
            json={
                "name": "Disabled VN",
                "base_type_name": native_negotiator_types[0],
            },
        )
        assert response.status_code == 200
        disabled_id = response.json()["virtual_negotiator"]["id"]

        # Disable one
        client.post(f"/api/negotiators/virtual/{disabled_id}/disable")

        # List without include_disabled - should not include disabled
        response = client.get("/api/negotiators/virtual")
        assert response.status_code == 200
        vn_ids = [vn["id"] for vn in response.json()["virtual_negotiators"]]
        assert enabled_id in vn_ids
        assert disabled_id not in vn_ids

        # List with include_disabled=true
        response = client.get("/api/negotiators/virtual?include_disabled=true")
        assert response.status_code == 200
        vn_ids = [vn["id"] for vn in response.json()["virtual_negotiators"]]
        assert enabled_id in vn_ids
        assert disabled_id in vn_ids

        # Cleanup
        client.delete(f"/api/negotiators/virtual/{enabled_id}")
        client.delete(f"/api/negotiators/virtual/{disabled_id}")

    def test_list_virtual_negotiators_by_base_type(
        self, client: TestClient, native_negotiator_types: list[str]
    ):
        """Test listing virtual negotiators by base type."""
        base_type = native_negotiator_types[0]

        # Create one
        response = client.post(
            "/api/negotiators/virtual",
            json={
                "name": "Test By Base Type",
                "base_type_name": base_type,
            },
        )
        assert response.status_code == 200
        vn_id = response.json()["virtual_negotiator"]["id"]

        # List by base type
        import urllib.parse

        encoded_type = urllib.parse.quote(base_type, safe="")
        response = client.get(f"/api/negotiators/virtual/by-base/{encoded_type}")
        assert response.status_code == 200
        data = response.json()
        assert data["base_type"] == base_type
        vn_ids = [vn["id"] for vn in data["virtual_negotiators"]]
        assert vn_id in vn_ids

        # Cleanup
        client.delete(f"/api/negotiators/virtual/{vn_id}")

    def test_duplicate_virtual_negotiator(
        self, client: TestClient, native_negotiator_types: list[str]
    ):
        """Test duplicating a virtual negotiator."""
        # Create original
        response = client.post(
            "/api/negotiators/virtual",
            json={
                "name": "Original VN",
                "base_type_name": native_negotiator_types[0],
                "description": "Original description",
                "params": {"test": "value"},
            },
        )
        assert response.status_code == 200
        original_id = response.json()["virtual_negotiator"]["id"]

        # Duplicate
        response = client.post(f"/api/negotiators/virtual/{original_id}/duplicate")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "duplicated"
        duplicate = data["virtual_negotiator"]
        assert duplicate["id"] != original_id
        assert "Copy of Original VN" in duplicate["name"]
        assert duplicate["description"] == "Original description"

        # Cleanup
        client.delete(f"/api/negotiators/virtual/{original_id}")
        client.delete(f"/api/negotiators/virtual/{duplicate['id']}")

    def test_get_virtual_negotiator_tags(
        self, client: TestClient, native_negotiator_types: list[str]
    ):
        """Test getting all tags from virtual negotiators."""
        # Create one with custom tags
        response = client.post(
            "/api/negotiators/virtual",
            json={
                "name": "Test Tags VN",
                "base_type_name": native_negotiator_types[0],
                "tags": ["custom-tag", "another-tag"],
            },
        )
        assert response.status_code == 200
        vn_id = response.json()["virtual_negotiator"]["id"]

        # Get tags
        response = client.get("/api/negotiators/virtual/tags")
        assert response.status_code == 200
        data = response.json()
        assert "tags" in data
        # Should include the tags we added (plus "virtual")
        assert "virtual" in data["tags"]
        assert "custom-tag" in data["tags"]

        # Cleanup
        client.delete(f"/api/negotiators/virtual/{vn_id}")


class TestBasicUIRoutes:
    """Basic tests to ensure the UI routes work."""

    def test_index_loads(self, client: TestClient):
        """Test that the main index page loads successfully."""
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Check that it contains expected Alpine.js markers
        assert "x-data" in response.text
        assert "Alpine" in response.text

    def test_static_css_loads(self, client: TestClient):
        """Test that CSS files are accessible."""
        response = client.get("/static/css/styles.css")
        assert response.status_code == 200
        assert "text/css" in response.headers["content-type"]

    def test_static_js_loads(self, client: TestClient):
        """Test that JS files are accessible."""
        response = client.get("/static/js/layout-manager.js")
        assert response.status_code == 200
        assert "javascript" in response.headers["content-type"]

    def test_api_identity(self, client: TestClient):
        """Test that the API identity endpoint works."""
        response = client.get("/api/identity")
        assert response.status_code == 200
        data = response.json()
        assert data["app"] == "negmas-app"
        assert "version" in data

    def test_negotiators_endpoint(self, client: TestClient):
        """Test that the negotiators endpoint returns data."""
        response = client.get("/api/negotiators")
        assert response.status_code == 200
        data = response.json()
        assert "negotiators" in data
        assert "count" in data
        assert data["count"] > 0

    def test_scenarios_endpoint(self, client: TestClient):
        """Test that the scenarios endpoint returns data."""
        response = client.get("/api/scenarios")
        assert response.status_code == 200
        data = response.json()
        assert "scenarios" in data
        assert len(data["scenarios"]) > 0

    def test_mechanisms_endpoint(self, client: TestClient):
        """Test that the mechanisms endpoint returns data."""
        response = client.get("/api/mechanisms")
        assert response.status_code == 200
        data = response.json()
        assert "mechanisms" in data
        assert len(data["mechanisms"]) > 0
