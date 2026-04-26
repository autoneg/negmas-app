"""Tests for the session manager service."""

import pytest
from negmas_app.models.negotiator import NegotiatorConfig
from negmas_app.models.session import SessionStatus
from negmas_app.services.session_manager import SessionManager


class TestSessionCreation:
    """Test session creation functionality."""

    def test_create_session_basic(self, sample_scenario_path):
        """Should create a session with basic parameters."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        manager = SessionManager()
        configs = [
            NegotiatorConfig(type_name="negmas.sao.AspirationNegotiator", name="Neg1"),
            NegotiatorConfig(type_name="negmas.sao.RandomNegotiator", name="Neg2"),
        ]

        session = manager.create_session(
            scenario_path=sample_scenario_path,
            negotiator_configs=configs,
        )

        assert session is not None
        assert session.id is not None
        assert session.status == SessionStatus.PENDING
        assert session.scenario_path == sample_scenario_path

    def test_create_session_with_mechanism_params(self, sample_scenario_path):
        """Should create a session with mechanism parameters."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        manager = SessionManager()
        configs = [
            NegotiatorConfig(type_name="negmas.sao.AspirationNegotiator", name="Neg1"),
            NegotiatorConfig(type_name="negmas.sao.RandomNegotiator", name="Neg2"),
        ]

        session = manager.create_session(
            scenario_path=sample_scenario_path,
            negotiator_configs=configs,
            mechanism_type="SAOMechanism",
            mechanism_params={"n_steps": 50, "time_limit": 10.0},
        )

        assert session.n_steps == 50
        assert session.time_limit == 10.0

    def test_create_session_with_auto_save(self, sample_scenario_path):
        """Should create a session with auto_save option."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        manager = SessionManager()
        configs = [
            NegotiatorConfig(type_name="negmas.sao.AspirationNegotiator", name="Neg1"),
            NegotiatorConfig(type_name="negmas.sao.RandomNegotiator", name="Neg2"),
        ]

        session = manager.create_session(
            scenario_path=sample_scenario_path,
            negotiator_configs=configs,
            auto_save=False,
        )

        assert manager._auto_save[session.id] is False


class TestSessionManagement:
    """Test session retrieval and management."""

    def test_get_session_existing(self, sample_scenario_path):
        """Should retrieve an existing session."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        manager = SessionManager()
        configs = [
            NegotiatorConfig(type_name="negmas.sao.AspirationNegotiator", name="Neg1"),
            NegotiatorConfig(type_name="negmas.sao.RandomNegotiator", name="Neg2"),
        ]

        created = manager.create_session(sample_scenario_path, configs)
        retrieved = manager.get_session(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_session_nonexistent(self):
        """Should return None for nonexistent session."""
        manager = SessionManager()
        session = manager.get_session("nonexistent-id")
        assert session is None

    def test_get_configs(self, sample_scenario_path):
        """Should retrieve negotiator configs for a session."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        manager = SessionManager()
        configs = [
            NegotiatorConfig(type_name="negmas.sao.AspirationNegotiator", name="Neg1"),
            NegotiatorConfig(type_name="negmas.sao.RandomNegotiator", name="Neg2"),
        ]

        session = manager.create_session(sample_scenario_path, configs)
        retrieved_configs = manager.get_configs(session.id)

        assert retrieved_configs is not None
        assert len(retrieved_configs) == 2
        assert retrieved_configs[0].type_name == "negmas.sao.AspirationNegotiator"


class TestSessionControl:
    """Test session pause/resume/cancel functionality."""

    def test_pause_resume_session(self, sample_scenario_path):
        """Should pause and resume a session."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        manager = SessionManager()
        configs = [
            NegotiatorConfig(type_name="negmas.sao.AspirationNegotiator", name="Neg1"),
            NegotiatorConfig(type_name="negmas.sao.RandomNegotiator", name="Neg2"),
        ]

        session = manager.create_session(sample_scenario_path, configs)

        # Initially not paused
        assert manager.is_paused(session.id) is False

        # Pause
        assert manager.pause_session(session.id) is True
        assert manager.is_paused(session.id) is True

        # Resume
        assert manager.resume_session(session.id) is True
        assert manager.is_paused(session.id) is False

    def test_cancel_session(self, sample_scenario_path):
        """Should set cancel flag for a session."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        manager = SessionManager()
        configs = [
            NegotiatorConfig(type_name="negmas.sao.AspirationNegotiator", name="Neg1"),
            NegotiatorConfig(type_name="negmas.sao.RandomNegotiator", name="Neg2"),
        ]

        session = manager.create_session(sample_scenario_path, configs)

        assert manager.cancel_session(session.id) is True
        assert manager._cancel_flags[session.id] is True

    def test_control_nonexistent_session(self):
        """Control operations should return False for nonexistent sessions."""
        manager = SessionManager()

        assert manager.cancel_session("nonexistent") is False
        assert manager.pause_session("nonexistent") is False
        assert manager.resume_session("nonexistent") is False


class TestSessionStreamRun:
    """Test running sessions with streaming."""

    @pytest.mark.asyncio
    async def test_run_session_basic(self, sample_scenario_path):
        """Should run a complete negotiation session."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        manager = SessionManager()
        configs = [
            NegotiatorConfig(type_name="negmas.sao.AspirationNegotiator", name="Neg1"),
            NegotiatorConfig(type_name="negmas.sao.AspirationNegotiator", name="Neg2"),
        ]

        session = manager.create_session(
            scenario_path=sample_scenario_path,
            negotiator_configs=configs,
            mechanism_params={"n_steps": 20},  # Short for testing
            auto_save=False,  # Don't save during tests
        )

        events = []
        async for event in manager.run_session_stream(
            session.id,
            configs,
            step_delay=0.0,  # No delay for tests
        ):
            events.append(event)

        # Should have init event, offers, and final session
        assert len(events) > 0

        # Last event should be the session
        final_session = events[-1]
        assert final_session.status in [SessionStatus.COMPLETED, SessionStatus.FAILED]

    @pytest.mark.asyncio
    async def test_run_session_with_cancel(self, sample_scenario_path):
        """Should handle cancellation during run."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        manager = SessionManager()
        configs = [
            NegotiatorConfig(type_name="negmas.sao.AspirationNegotiator", name="Neg1"),
            NegotiatorConfig(type_name="negmas.sao.AspirationNegotiator", name="Neg2"),
        ]

        session = manager.create_session(
            scenario_path=sample_scenario_path,
            negotiator_configs=configs,
            mechanism_params={"n_steps": 100},
            auto_save=False,
        )

        # Set cancel flag before starting
        manager._cancel_flags[session.id] = True

        events = []
        async for event in manager.run_session_stream(
            session.id,
            configs,
            step_delay=0.0,
        ):
            events.append(event)

        # Should end quickly due to cancel
        final_session = events[-1]
        assert final_session.status == SessionStatus.CANCELLED
