"""Root-level pytest fixtures shared across all test directories."""

from pathlib import Path

import pytest

from prompt_flags.api.decorators import reset_global_registry
from prompt_flags.api.functional import from_yaml
from prompt_flags.core.registry import PromptRegistry
from prompt_flags.rendering.engine import PromptRenderer

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def sample_config_path() -> Path:
    """Path to the sample_config.yaml fixture."""
    return FIXTURES_DIR / "sample_config.yaml"


@pytest.fixture()
def multi_bucket_config_path() -> Path:
    """Path to the multi_bucket_config.yaml fixture."""
    return FIXTURES_DIR / "multi_bucket_config.yaml"


@pytest.fixture()
def sample_registry(sample_config_path: Path) -> PromptRegistry:
    """A pre-loaded PromptRegistry from sample_config.yaml."""
    return from_yaml(sample_config_path)


@pytest.fixture()
def multi_bucket_registry(multi_bucket_config_path: Path) -> PromptRegistry:
    """A pre-loaded PromptRegistry from multi_bucket_config.yaml."""
    return from_yaml(multi_bucket_config_path)


@pytest.fixture()
def renderer() -> PromptRenderer:
    """A clean PromptRenderer instance."""
    return PromptRenderer()


@pytest.fixture(autouse=True)
def _reset_decorator_registry() -> None:
    """Reset the global decorator registry between tests."""
    reset_global_registry()
