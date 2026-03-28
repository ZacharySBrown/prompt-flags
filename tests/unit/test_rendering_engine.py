"""Tests for the rendering engine."""

import os
from unittest.mock import patch

import pytest

from prompt_flags.core.models import FlagResult, RenderedSection, Section
from prompt_flags.rendering.engine import PromptRenderer


class TestPromptRendererInit:
    """Tests for PromptRenderer initialization."""

    def test_default_init(self) -> None:
        renderer = PromptRenderer()
        assert renderer.env is not None

    def test_init_with_template_dirs(self, tmp_path: object) -> None:
        renderer = PromptRenderer(template_dirs={"bucket1": str(tmp_path)})
        assert renderer.env is not None

    def test_environment_config(self) -> None:
        renderer = PromptRenderer()
        env = renderer.env
        assert env.autoescape is False
        assert env.trim_blocks is True
        assert env.lstrip_blocks is True
        assert env.keep_trailing_newline is True


class TestFeatureEnabledGlobal:
    """Tests for the feature_enabled() global function in templates."""

    def test_feature_enabled_true(self) -> None:
        renderer = PromptRenderer()
        flags = {"cot": FlagResult(name="cot", value=True, source="global")}
        result = renderer.render_template(
            "{% if feature_enabled('cot') %}enabled{% endif %}",
            context={},
            flags=flags,
        )
        assert result == "enabled"

    def test_feature_enabled_false(self) -> None:
        renderer = PromptRenderer()
        flags = {"cot": FlagResult(name="cot", value=False, source="global")}
        result = renderer.render_template(
            "{% if feature_enabled('cot') %}enabled{% else %}disabled{% endif %}",
            context={},
            flags=flags,
        )
        assert result == "disabled"

    def test_feature_enabled_missing_flag_returns_false(self) -> None:
        renderer = PromptRenderer()
        result = renderer.render_template(
            "{% if feature_enabled('nonexistent') %}yes{% else %}no{% endif %}",
            context={},
            flags={},
        )
        assert result == "no"


class TestEnvGlobal:
    """Tests for the env() global function in templates."""

    def test_env_existing_var(self) -> None:
        renderer = PromptRenderer()
        with patch.dict(os.environ, {"TEST_VAR": "hello"}):
            result = renderer.render_template(
                "{{ env('TEST_VAR') }}",
                context={},
                flags={},
            )
        assert result == "hello"

    def test_env_missing_var_with_default(self) -> None:
        renderer = PromptRenderer()
        result = renderer.render_template(
            "{{ env('NONEXISTENT_VAR_12345', 'fallback') }}",
            context={},
            flags={},
        )
        assert result == "fallback"

    def test_env_missing_var_no_default(self) -> None:
        renderer = PromptRenderer()
        result = renderer.render_template(
            "{{ env('NONEXISTENT_VAR_12345') }}",
            context={},
            flags={},
        )
        assert result == ""


class TestRenderTemplate:
    """Tests for render_template method."""

    def test_simple_context_substitution(self) -> None:
        renderer = PromptRenderer()
        result = renderer.render_template(
            "Hello {{ name }}",
            context={"name": "World"},
            flags={},
        )
        assert result == "Hello World"

    def test_context_with_flags(self) -> None:
        renderer = PromptRenderer()
        flags = {"verbose": FlagResult(name="verbose", value=True, source="global")}
        result = renderer.render_template(
            "{% if feature_enabled('verbose') %}Detailed: {{ msg }}{% endif %}",
            context={"msg": "test"},
            flags=flags,
        )
        assert result == "Detailed: test"

    def test_strict_undefined_raises(self) -> None:
        from jinja2 import UndefinedError

        renderer = PromptRenderer()
        with pytest.raises(UndefinedError):
            renderer.render_template(
                "{{ undefined_var }}",
                context={},
                flags={},
            )


class TestRenderSections:
    """Tests for render_sections method."""

    def test_render_enabled_section(self) -> None:
        renderer = PromptRenderer()
        sections = [
            Section(id="intro", content="Hello {{ name }}", flag="show_intro"),
        ]
        flags = {"show_intro": FlagResult(name="show_intro", value=True, source="global")}
        rendered = renderer.render_sections(sections, {"name": "World"}, flags)
        assert len(rendered) == 1
        assert rendered[0].id == "intro"
        assert rendered[0].content == "Hello World"

    def test_skip_disabled_section(self) -> None:
        renderer = PromptRenderer()
        sections = [
            Section(id="intro", content="Hello", flag="show_intro"),
        ]
        flags = {"show_intro": FlagResult(name="show_intro", value=False, source="global")}
        rendered = renderer.render_sections(sections, {}, flags)
        assert len(rendered) == 0

    def test_section_without_flag_always_rendered(self) -> None:
        renderer = PromptRenderer()
        sections = [
            Section(id="always", content="Always visible"),
        ]
        rendered = renderer.render_sections(sections, {}, {})
        assert len(rendered) == 1
        assert rendered[0].content == "Always visible"

    def test_multiple_sections_mixed_flags(self) -> None:
        renderer = PromptRenderer()
        sections = [
            Section(id="a", content="Section A", flag="flag_a"),
            Section(id="b", content="Section B", flag="flag_b"),
            Section(id="c", content="Section C"),
        ]
        flags = {
            "flag_a": FlagResult(name="flag_a", value=True, source="global"),
            "flag_b": FlagResult(name="flag_b", value=False, source="global"),
        }
        rendered = renderer.render_sections(sections, {}, flags)
        assert len(rendered) == 2
        assert rendered[0].id == "a"
        assert rendered[1].id == "c"

    def test_rendered_section_preserves_flag(self) -> None:
        renderer = PromptRenderer()
        sections = [
            Section(id="s1", content="Text", flag="my_flag"),
        ]
        flags = {"my_flag": FlagResult(name="my_flag", value=True, source="global")}
        rendered = renderer.render_sections(sections, {}, flags)
        assert rendered[0].flag == "my_flag"


class TestCompose:
    """Tests for compose method."""

    def test_compose_joins_sections(self) -> None:
        renderer = PromptRenderer()
        sections = [
            RenderedSection(id="a", content="First"),
            RenderedSection(id="b", content="Second"),
        ]
        result = renderer.compose(sections)
        assert "First" in result
        assert "Second" in result

    def test_compose_empty_list(self) -> None:
        renderer = PromptRenderer()
        result = renderer.compose([])
        assert result == ""

    def test_compose_single_section(self) -> None:
        renderer = PromptRenderer()
        sections = [RenderedSection(id="only", content="Only section")]
        result = renderer.compose(sections)
        assert result == "Only section"


class TestWhitespaceNormalization:
    """Tests for post-processing whitespace normalization."""

    def test_collapse_multiple_blank_lines(self) -> None:
        renderer = PromptRenderer()
        flags = {
            "a": FlagResult(name="a", value=True, source="global"),
            "b": FlagResult(name="b", value=False, source="global"),
            "c": FlagResult(name="c", value=True, source="global"),
        }
        template = (
            "{% if feature_enabled('a') %}Section A{% endif %}\n"
            "\n"
            "\n"
            "\n"
            "{% if feature_enabled('b') %}Section B{% endif %}\n"
            "\n"
            "\n"
            "\n"
            "{% if feature_enabled('c') %}Section C{% endif %}"
        )
        result = renderer.render_template(template, {}, flags)
        # Multiple blank lines should be collapsed to single blank line
        assert "\n\n\n" not in result
        assert "Section A" in result
        assert "Section B" not in result
        assert "Section C" in result
