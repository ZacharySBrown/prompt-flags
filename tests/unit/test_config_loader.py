"""Tests for config loader — YAML loading and registry building.

Tests cover YAML file loading, Pydantic validation of loaded data,
conversion to core domain models, and error handling.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from prompt_flags.config.loader import build_registry, load_config
from prompt_flags.config.schema import GlobalConfig
from prompt_flags.core.models import Bucket, Prompt

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SAMPLE_CONFIG = FIXTURES_DIR / "sample_config.yaml"
INVALID_CONFIG = FIXTURES_DIR / "invalid_config.yaml"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_yaml(self) -> None:
        """load_config returns a GlobalConfig from a valid YAML file."""
        config = load_config(SAMPLE_CONFIG)
        assert isinstance(config, GlobalConfig)
        assert config.version == "1.0"

    def test_load_valid_yaml_buckets(self) -> None:
        """load_config parses buckets correctly."""
        config = load_config(SAMPLE_CONFIG)
        assert "guides" in config.buckets
        assert "tool_prompts" in config.buckets
        assert config.buckets["guides"].description == "Step-by-step reasoning guides"

    def test_load_valid_yaml_flags(self) -> None:
        """load_config parses flags correctly."""
        config = load_config(SAMPLE_CONFIG)
        assert "chain_of_thought" in config.flags
        assert config.flags["chain_of_thought"].default is True
        assert "few_shot_examples" in config.flags
        assert config.flags["few_shot_examples"].default is False

    def test_load_valid_yaml_ordering(self) -> None:
        """load_config parses ordering constraints."""
        config = load_config(SAMPLE_CONFIG)
        assert len(config.ordering) == 2
        assert config.ordering[0].before == "system_identity"
        assert config.ordering[0].after == "task_description"

    def test_load_valid_yaml_env_vars(self) -> None:
        """load_config parses env_vars."""
        config = load_config(SAMPLE_CONFIG)
        assert "MODEL_NAME" in config.env_vars
        assert config.env_vars["MODEL_NAME"].default == "gpt-4"
        assert config.env_vars["TEMPERATURE"].type == "float"

    def test_load_valid_yaml_prompts(self) -> None:
        """load_config parses prompts within buckets."""
        config = load_config(SAMPLE_CONFIG)
        guides = config.buckets["guides"]
        assert "coding_guide" in guides.prompts
        cg = guides.prompts["coding_guide"]
        assert cg.template == "coding_guide.j2"
        assert len(cg.sections) == 3

    def test_load_valid_yaml_sections(self) -> None:
        """load_config parses sections within prompts."""
        config = load_config(SAMPLE_CONFIG)
        sections = config.buckets["guides"].prompts["coding_guide"].sections
        assert sections[0].id == "reasoning_steps"
        assert sections[0].flag == "chain_of_thought"
        assert sections[0].priority == 10

    def test_load_invalid_yaml_rejects_extra_fields(self) -> None:
        """load_config raises ValidationError for YAML with extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            load_config(INVALID_CONFIG)

    def test_load_nonexistent_file(self) -> None:
        """load_config raises FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            load_config(Path("/nonexistent/path.yaml"))

    def test_load_string_path(self) -> None:
        """load_config accepts a string path."""
        config = load_config(str(SAMPLE_CONFIG))
        assert isinstance(config, GlobalConfig)


class TestBuildRegistry:
    """Tests for build_registry function."""

    def test_build_registry_returns_registry(self) -> None:
        """build_registry returns a PromptRegistry."""
        from prompt_flags.core.registry import PromptRegistry

        config = load_config(SAMPLE_CONFIG)
        registry = build_registry(config)
        assert isinstance(registry, PromptRegistry)

    def test_build_registry_has_buckets(self) -> None:
        """build_registry populates buckets in the registry."""
        config = load_config(SAMPLE_CONFIG)
        registry = build_registry(config)
        bucket = registry.get_bucket("guides")
        assert isinstance(bucket, Bucket)
        assert bucket.name == "guides"
        assert bucket.description == "Step-by-step reasoning guides"

    def test_build_registry_has_flags(self) -> None:
        """build_registry populates flags in the registry."""
        config = load_config(SAMPLE_CONFIG)
        registry = build_registry(config)
        # Access flags via resolve to verify they exist
        flag_map = registry.resolve_flags("guides", "coding_guide")
        assert "chain_of_thought" in flag_map

    def test_build_registry_has_prompts(self) -> None:
        """build_registry populates prompts within buckets."""
        config = load_config(SAMPLE_CONFIG)
        registry = build_registry(config)
        prompt = registry.get_prompt("guides", "coding_guide")
        assert isinstance(prompt, Prompt)
        assert prompt.name == "coding_guide"

    def test_build_registry_has_sections(self) -> None:
        """build_registry populates sections within prompts."""
        config = load_config(SAMPLE_CONFIG)
        registry = build_registry(config)
        prompt = registry.get_prompt("guides", "coding_guide")
        assert len(prompt.sections) == 3
        assert prompt.sections[0].id == "reasoning_steps"

    def test_build_registry_has_ordering_constraints(self) -> None:
        """build_registry populates global ordering constraints."""
        config = load_config(SAMPLE_CONFIG)
        registry = build_registry(config)
        # Ordering constraints are internal; verify via _constraints
        assert len(registry._constraints) >= 2  # global + bucket ordering

    def test_build_registry_bucket_flags(self) -> None:
        """build_registry converts bucket flag overrides correctly."""
        config = load_config(SAMPLE_CONFIG)
        registry = build_registry(config)
        bucket = registry.get_bucket("guides")
        assert bucket.flags.get("chain_of_thought") is True
        assert bucket.flags.get("few_shot_examples") is True

    def test_build_registry_prompt_flags(self) -> None:
        """build_registry converts prompt flag overrides correctly."""
        config = load_config(SAMPLE_CONFIG)
        registry = build_registry(config)
        prompt = registry.get_prompt("guides", "analysis_guide")
        assert prompt.flags.get("verbose_instructions") is False

    def test_build_registry_flag_resolution(self) -> None:
        """build_registry produces a registry that resolves flags correctly."""
        config = load_config(SAMPLE_CONFIG)
        registry = build_registry(config)
        # chain_of_thought: global default=True, bucket override=True
        result = registry.resolve_flags("guides", "coding_guide")
        assert result["chain_of_thought"].value is True
        # verbose_instructions: global default=False, prompt override=False
        result2 = registry.resolve_flags("guides", "analysis_guide")
        assert result2["verbose_instructions"].value is False

    def test_build_registry_disabled_bucket(self) -> None:
        """build_registry includes disabled buckets (enabled is metadata)."""
        from prompt_flags.config.schema import BucketDef, FlagDef

        config = GlobalConfig(
            flags={"f": FlagDef(default=True)},
            buckets={"disabled_b": BucketDef(enabled=False)},
        )
        registry = build_registry(config)
        bucket = registry.get_bucket("disabled_b")
        assert bucket.enabled is False
