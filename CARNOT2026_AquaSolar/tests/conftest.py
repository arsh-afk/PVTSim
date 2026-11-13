"""Test configuration and fixtures."""

from __future__ import annotations

import pytest
from pathlib import Path


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def inputs_dir(project_root):
    """Return the inputs directory."""
    return project_root / "inputs"


@pytest.fixture
def params_dir(inputs_dir):
    """Return the parameters directory."""
    return inputs_dir / "parameters"


@pytest.fixture
def tables_dir(inputs_dir):
    """Return the tables directory."""
    return inputs_dir / "tables"


@pytest.fixture
def timeseries_dir(inputs_dir):
    """Return the timeseries directory."""
    return inputs_dir / "timeseries"
