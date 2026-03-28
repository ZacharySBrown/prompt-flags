"""Tests for the functional API."""

from pathlib import Path

import pytest

from prompt_flags.api.functional import compose, from_yaml, render_prompt
from prompt_flags.core.models import Bucket, Flag, Prompt, Section
from prompt_flags.core.registry import PromptRegistry

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


class TestRenderPrompt:
    """Tests for render_prompt()."""

    def _make_registry(self) -> PromptRegistry:
        """Create a simple registry for testing."""
        registry = PromptRegistry(strict=False)
        registry.add_flag(Flag(name="cot", default=True))
        registry.add_flag(Flag(name="json", default=False))
        sections = [
            Section(id="intro", content="Hello {{ name }}.", priority=1),
            Section(id="reasoning", content="Think step by step.", flag="cot", priority=10),
            Section(id="format", content="Respond in JSON.", flag="json", priority=20),
        ]
        prompt = Prompt(name="coding_guide", sections=sections)
        bucket = Bucket(name="guides", prompts={"coding_guide": prompt})
        registry.add_bucket(bucket)
        return registry

    def test_render_prompt_basic(self) -> None:
        """render_prompt() renders a prompt with context."""
        registry = self._make_registry()
        result = render_prompt(
            registry, "guides", "coding_guide",
            context={"name": "Alice"},
        )
        assert "Hello Alice." in result
        assert "Think step by step." in result
        # json flag is off by default
        assert "Respond in JSON." not in result

    def test_render_prompt_with_flags(self) -> None:
        """render_prompt() respects flag overrides."""
        registry = self._make_registry()
        result = render_prompt(
            registry, "guides", "coding_guide",
            context={"name": "Bob"},
            flags={"cot": False, "json": True},
        )
        assert "Hello Bob." in result
        assert "Think step by step." not in result
        assert "Respond in JSON." in result

    def test_render_prompt_no_context(self) -> None:
        """render_prompt() works with no context if template doesn't need it."""
        registry = PromptRegistry(strict=False)
        sections = [Section(id="s", content="Static content.")]
        prompt = Prompt(name="p", sections=sections)
        bucket = Bucket(name="b", prompts={"p": prompt})
        registry.add_bucket(bucket)
        result = render_prompt(registry, "b", "p")
        assert result == "Static content."


class TestCompose:
    """Tests for compose()."""

    def _make_registry(self) -> PromptRegistry:
        """Create a registry with multiple buckets."""
        registry = PromptRegistry(strict=False)

        # Bucket 1: guides
        sections1 = [Section(id="guide_intro", content="Guide intro.")]
        prompt1 = Prompt(name="p1", sections=sections1)
        bucket1 = Bucket(name="guides", prompts={"p1": prompt1})
        registry.add_bucket(bucket1)

        # Bucket 2: tools
        sections2 = [Section(id="tool_intro", content="Tool intro.")]
        prompt2 = Prompt(name="p1", sections=sections2)
        bucket2 = Bucket(name="tools", prompts={"p1": prompt2})
        registry.add_bucket(bucket2)

        return registry

    def test_compose_joins_buckets(self) -> None:
        """compose() joins prompts across multiple buckets."""
        registry = self._make_registry()
        result = compose(registry, ["guides", "tools"])
        assert "Guide intro." in result
        assert "Tool intro." in result

    def test_compose_single_bucket(self) -> None:
        """compose() works with a single bucket."""
        registry = self._make_registry()
        result = compose(registry, ["guides"])
        assert "Guide intro." in result
        assert "Tool intro." not in result

    def test_compose_empty_buckets(self) -> None:
        """compose() returns empty string for empty bucket list."""
        registry = self._make_registry()
        result = compose(registry, [])
        assert result == ""

    def test_compose_with_flags(self) -> None:
        """compose() passes flags through to rendering."""
        registry = PromptRegistry(strict=False)
        registry.add_flag(Flag(name="show", default=True))
        sections = [
            Section(id="always", content="Always."),
            Section(id="optional", content="Optional.", flag="show"),
        ]
        prompt = Prompt(name="p", sections=sections)
        bucket = Bucket(name="b", prompts={"p": prompt})
        registry.add_bucket(bucket)

        result = compose(registry, ["b"], flags={"show": False})
        assert "Always." in result
        assert "Optional." not in result


class TestFromYaml:
    """Tests for from_yaml()."""

    def test_from_yaml_loads_config(self) -> None:
        """from_yaml() loads a YAML file and returns a PromptRegistry."""
        path = FIXTURES_DIR / "sample_config.yaml"
        registry = from_yaml(path)
        assert isinstance(registry, PromptRegistry)

    def test_from_yaml_has_buckets(self) -> None:
        """from_yaml() registry contains buckets from the YAML file."""
        path = FIXTURES_DIR / "sample_config.yaml"
        registry = from_yaml(path)
        bucket = registry.get_bucket("guides")
        assert bucket.name == "guides"

    def test_from_yaml_has_flags(self) -> None:
        """from_yaml() registry contains flags from the YAML file."""
        path = FIXTURES_DIR / "sample_config.yaml"
        registry = from_yaml(path)
        results = registry.resolve_flags("guides", "coding_guide")
        assert results["chain_of_thought"].value is True

    def test_from_yaml_missing_file_raises(self) -> None:
        """from_yaml() raises FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            from_yaml("/nonexistent/path.yaml")

    def test_from_yaml_string_path(self) -> None:
        """from_yaml() accepts string paths."""
        path = str(FIXTURES_DIR / "sample_config.yaml")
        registry = from_yaml(path)
        assert isinstance(registry, PromptRegistry)
