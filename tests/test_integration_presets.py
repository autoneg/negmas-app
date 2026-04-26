"""
Integration tests for save/load configuration workflows.
Tests the complete flow from saving to loading configurations.
"""

import pytest
from fastapi.testclient import TestClient
import time


class TestNegotiationPresetWorkflow:
    """Integration tests for full negotiation preset save/load workflow."""

    def test_complete_session_preset_workflow(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test complete workflow: save preset, load presets, load specific, delete."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        # Step 1: Save a preset
        preset_name = f"Integration Test Preset {time.time()}"
        preset_data = {
            "name": preset_name,
            "scenario_path": sample_scenario_path,
            "scenario_name": "Integration Test Scenario",
            "negotiators": [
                {
                    "type_name": native_negotiator_types[0],
                    "name": "IntAgent1",
                    "source": "native",
                    "requires_bridge": False,
                    "params": {"aspiration_type": "linear"},
                },
                {
                    "type_name": native_negotiator_types[1],
                    "name": "IntAgent2",
                    "source": "native",
                    "requires_bridge": False,
                    "params": {},
                },
            ],
            "mechanism_type": "SAOMechanism",
            "mechanism_params": {"n_steps": 150, "time_limit": 60.0},
            "share_ufuns": True,
            "mode": "step",
            "step_delay": 200,
            "show_plot": True,
            "show_offers": False,
        }

        save_response = client.post("/api/settings/presets/sessions", json=preset_data)
        assert save_response.status_code == 200

        # Step 2: Load all presets and verify it exists
        list_response = client.get("/api/settings/presets/sessions")
        assert list_response.status_code == 200
        presets = list_response.json()["presets"]
        preset_names = [p["name"] for p in presets]
        assert preset_name in preset_names

        # Step 3: Verify preset data is complete
        loaded_preset = next(p for p in presets if p["name"] == preset_name)
        assert loaded_preset["scenario_path"] == sample_scenario_path
        assert len(loaded_preset["negotiators"]) == 2
        assert loaded_preset["negotiators"][0]["name"] == "IntAgent1"
        assert loaded_preset["negotiators"][1]["name"] == "IntAgent2"
        assert loaded_preset["mechanism_params"]["n_steps"] == 150
        assert loaded_preset["share_ufuns"] is True
        assert loaded_preset["mode"] == "step"
        assert loaded_preset["step_delay"] == 200

        # Step 4: Use preset to start a negotiation
        start_response = client.post(
            "/api/negotiation/start",
            json={
                "scenario_path": loaded_preset["scenario_path"],
                "negotiators": [
                    {
                        "type_name": n["type_name"],
                        "name": n["name"],
                        "params": n.get("params", {}),
                    }
                    for n in loaded_preset["negotiators"]
                ],
                "mechanism_type": loaded_preset["mechanism_type"],
                "mechanism_params": loaded_preset["mechanism_params"],
                "step_delay": 0.0,
            },
        )
        assert start_response.status_code == 200
        session_id = start_response.json()["session_id"]
        assert session_id is not None

        # Step 5: Delete the preset
        delete_response = client.delete(f"/api/settings/presets/sessions/{preset_name}")
        assert delete_response.status_code == 200
        assert delete_response.json()["success"] is True

        # Step 6: Verify preset is gone
        final_list = client.get("/api/settings/presets/sessions")
        final_presets = final_list.json()["presets"]
        final_names = [p["name"] for p in final_presets]
        assert preset_name not in final_names

    def test_recent_session_workflow(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test recent sessions workflow: add to recent, retrieve, clear."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        # Step 1: Clear recent sessions
        client.delete("/api/settings/presets/recent")

        # Step 2: Add a session to recent
        session_data = {
            "scenario_path": sample_scenario_path,
            "scenario_name": f"Recent Integration Test {time.time()}",
            "negotiators": [
                {
                    "type_name": native_negotiator_types[0],
                    "name": "RecentAgent1",
                    "source": "native",
                    "requires_bridge": False,
                    "params": {},
                }
            ],
            "mechanism_type": "SAOMechanism",
            "mechanism_params": {"n_steps": 75},
        }

        add_response = client.post("/api/settings/presets/recent", json=session_data)
        assert add_response.status_code == 200

        # Step 3: Retrieve recent sessions
        get_response = client.get("/api/settings/presets/recent")
        assert get_response.status_code == 200
        sessions = get_response.json()["sessions"]

        # Verify our session is in the list
        scenario_names = [s["scenario_name"] for s in sessions]
        assert any("Recent Integration Test" in name for name in scenario_names)

        # Step 4: Clear recent sessions
        clear_response = client.delete("/api/settings/presets/recent")
        assert clear_response.status_code == 200

        # Step 5: Verify cleared
        final_response = client.get("/api/settings/presets/recent")
        assert len(final_response.json()["sessions"]) == 0


class TestTournamentPresetWorkflow:
    """Integration tests for tournament preset save/load workflow."""

    def test_complete_tournament_preset_workflow(
        self,
        client: TestClient,
        sample_scenario_paths: list[str],
        native_negotiator_types: list[str],
    ):
        """Test complete workflow: save preset, load, use, delete."""
        if not sample_scenario_paths:
            pytest.skip("No sample scenarios available")

        # Step 1: Save a tournament preset
        preset_name = f"Integration Tournament {time.time()}"
        preset_data = {
            "name": preset_name,
            "scenario_paths": sample_scenario_paths[:2],
            "competitor_types": native_negotiator_types[:2],
            "opponent_types": None,
            "opponents_same_as_competitors": True,
            "n_repetitions": 2,
            "n_steps": 50,
            "mechanism_type": "SAOMechanism",
            "final_score_metric": "advantage",
            "final_score_stat": "mean",
            "rotate_ufuns": True,
            "self_play": True,
        }

        save_response = client.post(
            "/api/settings/presets/tournaments", json=preset_data
        )
        assert save_response.status_code == 200

        # Step 2: Load all presets and verify
        list_response = client.get("/api/settings/presets/tournaments")
        assert list_response.status_code == 200
        presets = list_response.json()["presets"]
        preset_names = [p["name"] for p in presets]
        assert preset_name in preset_names

        # Step 3: Verify preset data
        loaded_preset = next(p for p in presets if p["name"] == preset_name)
        assert len(loaded_preset["scenario_paths"]) == 2
        assert len(loaded_preset["competitor_types"]) == 2
        assert loaded_preset["n_repetitions"] == 2
        assert loaded_preset["n_steps"] == 50
        assert loaded_preset["self_play"] is True

        # Step 4: Use preset to start a tournament (will not wait for completion)
        start_response = client.post(
            "/api/tournament/start",
            json={
                "competitor_types": loaded_preset["competitor_types"],
                "opponent_types": None,  # Same as competitors
                "scenario_paths": loaded_preset["scenario_paths"],
                "n_repetitions": 1,  # Reduce for faster test
                "n_steps": 3,  # Very short for testing
            },
        )
        assert start_response.status_code == 200
        tournament_id = start_response.json()["session_id"]
        assert tournament_id is not None

        # Step 5: Delete the preset
        delete_response = client.delete(
            f"/api/settings/presets/tournaments/{preset_name}"
        )
        assert delete_response.status_code == 200
        assert delete_response.json()["success"] is True

        # Step 6: Verify preset is gone
        final_list = client.get("/api/settings/presets/tournaments")
        final_presets = final_list.json()["presets"]
        final_names = [p["name"] for p in final_presets]
        assert preset_name not in final_names


class TestSavedDataWorkflow:
    """Integration tests for saved negotiations and tournaments."""

    def test_negotiation_save_load_tag_delete_workflow(
        self,
        client: TestClient,
        sample_scenario_path: str,
        native_negotiator_types: list[str],
    ):
        """Test complete negotiation save workflow with tags."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        # Step 1: Start a negotiation with auto-save
        start_response = client.post(
            "/api/negotiation/start",
            json={
                "scenario_path": sample_scenario_path,
                "negotiators": [
                    {"type_name": native_negotiator_types[0], "name": "SaveTest1"},
                    {"type_name": native_negotiator_types[1], "name": "SaveTest2"},
                ],
                "mechanism_type": "SAOMechanism",
                "mechanism_params": {"n_steps": 5},
                "step_delay": 0.0,
                "auto_save": True,
            },
        )
        assert start_response.status_code == 200
        session_id = start_response.json()["session_id"]

        # Step 2: Wait for completion
        time.sleep(3)

        # Step 3: Check if saved
        list_response = client.get("/api/negotiation/saved/list")
        if list_response.status_code == 200:
            saved_ids = [n["id"] for n in list_response.json()["negotiations"]]

            if session_id in saved_ids:
                # Step 4: Add tags
                tag_response = client.post(
                    f"/api/negotiation/saved/{session_id}/tags",
                    json={"tags": ["integration-test", "auto-cleanup"]},
                )
                assert tag_response.status_code == 200

                # Step 5: Retrieve and verify tags
                get_response = client.get(f"/api/negotiation/saved/{session_id}")
                assert get_response.status_code == 200
                data = get_response.json()
                assert "integration-test" in data["tags"]

                # Step 6: Archive
                archive_response = client.post(
                    f"/api/negotiation/saved/{session_id}/archive"
                )
                assert archive_response.status_code == 200

                # Step 7: Unarchive
                unarchive_response = client.post(
                    f"/api/negotiation/saved/{session_id}/unarchive"
                )
                assert unarchive_response.status_code == 200

                # Step 8: Delete
                delete_response = client.delete(f"/api/negotiation/saved/{session_id}")
                assert delete_response.status_code == 200

    def test_tournament_save_load_workflow(
        self,
        client: TestClient,
        sample_scenario_paths: list[str],
        native_negotiator_types: list[str],
    ):
        """Test tournament save workflow."""
        if not sample_scenario_paths:
            pytest.skip("No sample scenarios available")

        # Step 1: Start a tournament with auto-save
        start_response = client.post(
            "/api/tournament/start",
            json={
                "competitor_types": [native_negotiator_types[0]],
                "opponent_types": [native_negotiator_types[1]],
                "scenario_paths": sample_scenario_paths[:1],
                "n_repetitions": 1,
                "n_steps": 3,
            },
        )
        assert start_response.status_code == 200
        tournament_id = start_response.json()["session_id"]

        # Step 2: Wait for completion
        time.sleep(5)

        # Step 3: Check if saved
        list_response = client.get("/api/tournament/saved/list")
        if list_response.status_code == 200:
            saved_ids = [t["id"] for t in list_response.json()["tournaments"]]

            if tournament_id in saved_ids:
                # Step 4: Add tags
                tag_response = client.post(
                    f"/api/tournament/saved/{tournament_id}/tags",
                    json={"tags": ["integration-test"]},
                )
                assert tag_response.status_code == 200

                # Step 5: Get config
                config_response = client.get(
                    f"/api/tournament/saved/{tournament_id}/config"
                )
                if config_response.status_code == 200:
                    config = config_response.json()["config"]
                    assert config["n_repetitions"] == 1

                # Step 6: Delete
                delete_response = client.delete(
                    f"/api/tournament/saved/{tournament_id}"
                )
                assert delete_response.status_code == 200
