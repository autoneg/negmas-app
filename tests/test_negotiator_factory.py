"""Tests for the negotiator factory service."""

import pytest
from negmas.negotiators import Negotiator

from negmas_app.models.negotiator import NegotiatorConfig
from negmas_app.services.negotiator_factory import (
    NegotiatorFactory,
    NEGOTIATOR_REGISTRY,
    _get_class_for_type,
)


class TestNegotiatorDiscovery:
    """Test negotiator discovery functionality."""

    def test_registry_not_empty(self):
        """Registry should have negotiators after module load."""
        assert len(NEGOTIATOR_REGISTRY) > 0

    def test_native_negotiators_discovered(self):
        """Native negmas negotiators should be in registry."""
        # Check for some common native negotiators
        native_types = [
            "negmas.sao.AspirationNegotiator",
            "negmas.sao.NaiveTitForTatNegotiator",
            "negmas.sao.RandomNegotiator",
        ]
        for type_name in native_types:
            assert type_name in NEGOTIATOR_REGISTRY, (
                f"{type_name} not found in registry"
            )
            entry = NEGOTIATOR_REGISTRY[type_name]
            assert entry.info.source == "native"
            assert entry.info.available is True

    def test_list_available_returns_results(self):
        """list_available should return negotiator infos."""
        results = NegotiatorFactory.list_available()
        assert len(results) > 0
        for info in results:
            assert info.type_name
            assert info.source

    def test_list_available_filter_by_source(self):
        """list_available should filter by source."""
        native = NegotiatorFactory.list_available(source="native")
        assert len(native) > 0
        for info in native:
            assert info.source == "native"

    def test_list_available_search(self):
        """list_available should filter by search string."""
        results = NegotiatorFactory.list_available(search="aspiration")
        assert len(results) > 0
        for info in results:
            assert (
                "aspiration" in info.name.lower()
                or "aspiration" in info.description.lower()
            )

    def test_get_info_existing(self):
        """get_info should return info for existing negotiator."""
        info = NegotiatorFactory.get_info("negmas.sao.AspirationNegotiator")
        assert info is not None
        assert info.type_name == "negmas.sao.AspirationNegotiator"
        assert info.source == "native"

    def test_get_info_nonexistent(self):
        """get_info should return None for nonexistent negotiator."""
        info = NegotiatorFactory.get_info("nonexistent.Negotiator")
        assert info is None


class TestNegotiatorCreation:
    """Test negotiator creation functionality."""

    def test_create_native_negotiator(self):
        """Should create native negotiator with defaults."""
        config = NegotiatorConfig(
            type_name="negmas.sao.AspirationNegotiator",
            name="TestNeg",
        )
        negotiator = NegotiatorFactory.create(config)
        assert negotiator is not None
        assert isinstance(negotiator, Negotiator)
        assert negotiator.name == "TestNeg"

    def test_create_with_params(self):
        """Should create negotiator with custom parameters."""
        config = NegotiatorConfig(
            type_name="negmas.sao.AspirationNegotiator",
            name="CustomNeg",
            params={"aspiration_type": "linear"},
        )
        negotiator = NegotiatorFactory.create(config)
        assert negotiator is not None
        assert negotiator.name == "CustomNeg"

    def test_create_unknown_type_raises(self):
        """Should raise ValueError for unknown negotiator type."""
        config = NegotiatorConfig(
            type_name="nonexistent.Negotiator",
            name="Test",
        )
        with pytest.raises(ValueError) as exc_info:
            NegotiatorFactory.create(config)
        assert "Unknown negotiator type" in str(exc_info.value)

    def test_create_for_scenario(self, sample_scenario_path):
        """Should create negotiators for a scenario."""
        if sample_scenario_path is None:
            pytest.skip("No sample scenario available")

        from negmas_app.services.scenario_loader import ScenarioLoader

        loader = ScenarioLoader()
        scenario = loader.load_scenario(sample_scenario_path)
        if scenario is None:
            pytest.skip("Could not load scenario")

        configs = [
            NegotiatorConfig(type_name="negmas.sao.AspirationNegotiator", name="Neg1"),
            NegotiatorConfig(type_name="negmas.sao.RandomNegotiator", name="Neg2"),
        ]

        # Adjust configs to match number of ufuns
        configs = configs[: len(scenario.ufuns)]

        negotiators = NegotiatorFactory.create_for_scenario(configs, scenario)
        assert len(negotiators) == len(scenario.ufuns)
        for neg in negotiators:
            assert isinstance(neg, Negotiator)


class TestGetClassForType:
    """Test the _get_class_for_type helper function."""

    def test_get_registered_class(self):
        """Should return class for registered type."""
        cls = _get_class_for_type("negmas.sao.AspirationNegotiator")
        assert cls is not None
        assert issubclass(cls, Negotiator)

    def test_get_dynamic_import_class(self):
        """Should dynamically import unregistered class."""
        # This type should be importable even if not pre-registered
        cls = _get_class_for_type("negmas.sao.SAONegotiator")
        assert cls is not None

    def test_get_nonexistent_class(self):
        """Should return None for nonexistent class."""
        cls = _get_class_for_type("nonexistent.module.Class")
        assert cls is None


class TestNegotiatorSources:
    """Test negotiator source management."""

    def test_get_available_sources(self):
        """Should return list of available sources."""
        sources = NegotiatorFactory.get_available_sources()
        assert len(sources) > 0

        # Native should always be available
        native = next((s for s in sources if s.id == "native"), None)
        assert native is not None
        assert native.builtin is True

    def test_is_source_available_native(self):
        """Native source should always be available."""
        assert NegotiatorFactory.is_source_available("native") is True

    def test_is_source_available_unknown(self):
        """Unknown source should not be available."""
        assert NegotiatorFactory.is_source_available("unknown_source") is False

    def test_refresh_registry(self):
        """refresh_registry should repopulate registry."""
        initial_count = len(NEGOTIATOR_REGISTRY)
        NegotiatorFactory.refresh_registry()
        assert len(NEGOTIATOR_REGISTRY) >= initial_count
