"""Tests for plugin Protocol interfaces.

Verifies that Protocol classes support structural subtyping via
runtime_checkable isinstance checks, and that concrete implementations
work correctly.
"""

from __future__ import annotations

from typing import Any

from prompt_flags.core.models import RenderedSection
from prompt_flags.plugins.protocols import (
    FlagSource,
    PromptComposer,
    PromptLoader,
    PromptRenderer,
)

# ---------------------------------------------------------------------------
# Conforming stub implementations
# ---------------------------------------------------------------------------


class StubLoader:
    """Minimal class satisfying PromptLoader protocol."""

    def load(self, name: str, bucket: str | None = None) -> str:
        return f"template:{name}"

    def list_templates(self, bucket: str | None = None) -> list[str]:
        return ["a", "b"]


class StubRenderer:
    """Minimal class satisfying PromptRenderer protocol."""

    def render(self, template: str, context: dict[str, Any]) -> str:
        return template.format(**context)


class StubComposer:
    """Minimal class satisfying PromptComposer protocol."""

    def compose(self, sections: list[RenderedSection]) -> str:
        return "\n".join(s.content for s in sections)


class StubFlagSource:
    """Minimal class satisfying FlagSource protocol."""

    def __init__(self, flags: dict[str, bool] | None = None) -> None:
        """Initialize with optional flag mappings."""
        self._flags = flags or {}

    def get_flag(self, name: str, context: dict[str, Any]) -> bool | None:
        return self._flags.get(name)

    def get_all_flags(self, context: dict[str, Any]) -> dict[str, bool]:
        return dict(self._flags)


# ---------------------------------------------------------------------------
# Non-conforming stubs (missing methods)
# ---------------------------------------------------------------------------


class BadLoader:
    """Missing list_templates method."""

    def load(self, name: str, bucket: str | None = None) -> str:
        return name


class BadRenderer:
    """Missing render method entirely."""

    pass


class BadComposer:
    """Missing compose method entirely."""

    def assemble(self, sections: list[RenderedSection]) -> str:
        return ""


class BadFlagSource:
    """Only has get_flag, missing get_all_flags."""

    def get_flag(self, name: str, context: dict[str, Any]) -> bool | None:
        return None


# ---------------------------------------------------------------------------
# PromptLoader protocol tests
# ---------------------------------------------------------------------------


class TestPromptLoaderProtocol:
    """Tests for the PromptLoader protocol."""

    def test_conforming_class_satisfies_protocol(self) -> None:
        assert isinstance(StubLoader(), PromptLoader)

    def test_non_conforming_class_fails_protocol(self) -> None:
        assert not isinstance(BadLoader(), PromptLoader)

    def test_load_returns_string(self) -> None:
        loader = StubLoader()
        result = loader.load("greeting")
        assert result == "template:greeting"

    def test_load_with_bucket(self) -> None:
        loader = StubLoader()
        result = loader.load("greeting", bucket="system")
        assert result == "template:greeting"

    def test_list_templates_returns_list(self) -> None:
        loader = StubLoader()
        result = loader.list_templates()
        assert result == ["a", "b"]

    def test_list_templates_with_bucket(self) -> None:
        loader = StubLoader()
        result = loader.list_templates(bucket="system")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# PromptRenderer protocol tests
# ---------------------------------------------------------------------------


class TestPromptRendererProtocol:
    """Tests for the PromptRenderer protocol."""

    def test_conforming_class_satisfies_protocol(self) -> None:
        assert isinstance(StubRenderer(), PromptRenderer)

    def test_non_conforming_class_fails_protocol(self) -> None:
        assert not isinstance(BadRenderer(), PromptRenderer)

    def test_render_interpolates_context(self) -> None:
        renderer = StubRenderer()
        result = renderer.render("Hello {name}", {"name": "world"})
        assert result == "Hello world"

    def test_render_empty_context(self) -> None:
        renderer = StubRenderer()
        result = renderer.render("static text", {})
        assert result == "static text"


# ---------------------------------------------------------------------------
# PromptComposer protocol tests
# ---------------------------------------------------------------------------


class TestPromptComposerProtocol:
    """Tests for the PromptComposer protocol."""

    def test_conforming_class_satisfies_protocol(self) -> None:
        assert isinstance(StubComposer(), PromptComposer)

    def test_non_conforming_class_fails_protocol(self) -> None:
        assert not isinstance(BadComposer(), PromptComposer)

    def test_compose_joins_sections(self) -> None:
        composer = StubComposer()
        sections = [
            RenderedSection(id="a", content="Hello"),
            RenderedSection(id="b", content="World"),
        ]
        result = composer.compose(sections)
        assert result == "Hello\nWorld"

    def test_compose_empty_list(self) -> None:
        composer = StubComposer()
        result = composer.compose([])
        assert result == ""

    def test_compose_single_section(self) -> None:
        composer = StubComposer()
        sections = [RenderedSection(id="only", content="Solo")]
        result = composer.compose(sections)
        assert result == "Solo"


# ---------------------------------------------------------------------------
# FlagSource protocol tests
# ---------------------------------------------------------------------------


class TestFlagSourceProtocol:
    """Tests for the FlagSource protocol."""

    def test_conforming_class_satisfies_protocol(self) -> None:
        assert isinstance(StubFlagSource(), FlagSource)

    def test_non_conforming_class_fails_protocol(self) -> None:
        assert not isinstance(BadFlagSource(), FlagSource)

    def test_get_flag_returns_value(self) -> None:
        source = StubFlagSource({"dark_mode": True})
        assert source.get_flag("dark_mode", {}) is True

    def test_get_flag_returns_none_for_unknown(self) -> None:
        source = StubFlagSource()
        assert source.get_flag("missing", {}) is None

    def test_get_all_flags_returns_dict(self) -> None:
        source = StubFlagSource({"a": True, "b": False})
        result = source.get_all_flags({})
        assert result == {"a": True, "b": False}

    def test_get_all_flags_empty(self) -> None:
        source = StubFlagSource()
        result = source.get_all_flags({})
        assert result == {}
