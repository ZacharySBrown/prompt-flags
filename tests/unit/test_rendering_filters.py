"""Tests for custom Jinja2 filters."""

from prompt_flags.rendering.engine import PromptRenderer
from prompt_flags.rendering.filters import indent_block, strip_empty_lines


class TestStripEmptyLines:
    """Tests for the strip_empty_lines filter."""

    def test_removes_empty_lines(self) -> None:
        text = "Line 1\n\n\nLine 2\n\nLine 3"
        result = strip_empty_lines(text)
        assert result == "Line 1\nLine 2\nLine 3"

    def test_preserves_content_lines(self) -> None:
        text = "Line 1\nLine 2\nLine 3"
        result = strip_empty_lines(text)
        assert result == "Line 1\nLine 2\nLine 3"

    def test_empty_string(self) -> None:
        assert strip_empty_lines("") == ""

    def test_only_empty_lines(self) -> None:
        text = "\n\n\n"
        result = strip_empty_lines(text)
        assert result == ""


class TestIndentBlock:
    """Tests for the indent_block filter."""

    def test_basic_indent(self) -> None:
        text = "Line 1\nLine 2"
        result = indent_block(text, spaces=4)
        assert result == "    Line 1\n    Line 2"

    def test_zero_indent(self) -> None:
        text = "Line 1\nLine 2"
        result = indent_block(text, spaces=0)
        assert result == "Line 1\nLine 2"

    def test_empty_lines_not_indented(self) -> None:
        text = "Line 1\n\nLine 2"
        result = indent_block(text, spaces=2)
        assert result == "  Line 1\n\n  Line 2"

    def test_empty_string(self) -> None:
        assert indent_block("", spaces=4) == ""


class TestFiltersInTemplates:
    """Tests for filters used within Jinja2 templates."""

    def test_strip_empty_lines_filter_in_template(self) -> None:
        renderer = PromptRenderer()
        result = renderer.render_template(
            "{{ text | strip_empty_lines }}",
            context={"text": "A\n\n\nB"},
            flags={},
        )
        assert result == "A\nB"

    def test_indent_block_filter_in_template(self) -> None:
        renderer = PromptRenderer()
        result = renderer.render_template(
            "{{ text | indent_block(4) }}",
            context={"text": "A\nB"},
            flags={},
        )
        assert result == "    A\n    B"
