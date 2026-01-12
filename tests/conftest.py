"""Pytest fixtures for negmas-app tests."""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from negmas_app.main import app


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_scenario_path():
    """Get path to a sample scenario for testing."""
    # Use a small scenario from the bundled scenarios
    base_path = Path(__file__).parent.parent / "scenarios"
    # Try anac2011/Laptop - a simple 2-party scenario
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


@pytest.fixture
def native_negotiator_types():
    """Get some native negotiator type names for testing."""
    return [
        "negmas.sao.AspirationNegotiator",
        "negmas.sao.NaiveTitForTatNegotiator",
        "negmas.sao.RandomNegotiator",
    ]
