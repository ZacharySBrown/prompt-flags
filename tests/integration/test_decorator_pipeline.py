"""Integration tests for the decorator API end-to-end.

Tests that decorated classes register, resolve flags, and render correctly
through the full pipeline.
"""

from prompt_flags.api.decorators import (
    bucket,
    get_global_registry,
    prompt,
    section,
)
from prompt_flags.api.functional import render_prompt
from prompt_flags.core.models import Flag
from prompt_flags.rendering.engine import PromptRenderer


class TestDecoratorPipeline:
    """Test the decorator API end-to-end."""

    def test_decorated_class_renders(self) -> None:
        """Define a decorated class, instantiate, render."""

        @bucket("guides")
        @prompt("coding_guide")
        class CodingGuide:
            """A coding guide prompt."""

            @section(id="identity", priority=1)
            def identity(self, ctx: dict) -> str:  # noqa: ARG002
                """Return identity content."""
                return "You are a coding assistant."

            @section(id="task", priority=10)
            def task(self, ctx: dict) -> str:  # noqa: ARG002
                """Return task content."""
                return "Help users write clean code."

        CodingGuide()
        registry = get_global_registry()

        result = render_prompt(registry, "guides", "coding_guide")
        assert "You are a coding assistant." in result
        assert "Help users write clean code." in result

    def test_multiple_decorated_classes(self) -> None:
        """Multiple decorated classes in same registry."""

        @bucket("guides")
        @prompt("guide_a")
        class GuideA:
            """First guide."""

            @section(id="a_intro", priority=1)
            def intro(self, ctx: dict) -> str:  # noqa: ARG002
                """Return intro for guide A."""
                return "Guide A intro."

        @bucket("guides")
        @prompt("guide_b")
        class GuideB:
            """Second guide."""

            @section(id="b_intro", priority=1)
            def intro(self, ctx: dict) -> str:  # noqa: ARG002
                """Return intro for guide B."""
                return "Guide B intro."

        GuideA()
        GuideB()
        registry = get_global_registry()

        result_a = render_prompt(registry, "guides", "guide_a")
        assert "Guide A intro." in result_a

        result_b = render_prompt(registry, "guides", "guide_b")
        assert "Guide B intro." in result_b

    def test_decorated_class_with_flags(self) -> None:
        """Decorated class with flag-gated sections renders correctly."""

        @bucket("b")
        @prompt("p")
        class MyPrompt:
            """A prompt with flagged sections."""

            @section(id="always", priority=1)
            def always(self, ctx: dict) -> str:  # noqa: ARG002
                """Always-visible section."""
                return "Always visible."

            @section(id="optional", flag="show_extra", priority=10)
            def optional(self, ctx: dict) -> str:  # noqa: ARG002
                """Optionally-visible section."""
                return "Extra content."

        MyPrompt()
        registry = get_global_registry()
        registry.add_flag(Flag(name="show_extra", default=False))

        # Flag is off: optional should not appear
        result_off = render_prompt(registry, "b", "p")
        assert "Always visible." in result_off
        assert "Extra content." not in result_off

        # Flag on via runtime override
        result_on = render_prompt(
            registry, "b", "p", flags={"show_extra": True}
        )
        assert "Always visible." in result_on
        assert "Extra content." in result_on

    def test_decorated_classes_in_different_buckets(self) -> None:
        """Decorated classes in different buckets are isolated."""

        @bucket("system")
        @prompt("identity")
        class SystemIdentity:
            """System identity prompt."""

            @section(id="system_id", priority=1)
            def identity(self, ctx: dict) -> str:  # noqa: ARG002
                """Return system identity."""
                return "I am the system."

        @bucket("tools")
        @prompt("tool_use")
        class ToolUse:
            """Tool use prompt."""

            @section(id="tool_intro", priority=1)
            def intro(self, ctx: dict) -> str:  # noqa: ARG002
                """Return tool introduction."""
                return "Use tools carefully."

        SystemIdentity()
        ToolUse()
        registry = get_global_registry()

        system_result = render_prompt(registry, "system", "identity")
        assert "I am the system." in system_result
        assert "Use tools carefully." not in system_result

        tool_result = render_prompt(registry, "tools", "tool_use")
        assert "Use tools carefully." in tool_result
        assert "I am the system." not in tool_result

    def test_decorated_class_section_ordering(self) -> None:
        """Sections in decorated classes respect priority ordering."""

        @bucket("b")
        @prompt("ordered")
        class OrderedPrompt:
            """A prompt with ordered sections."""

            @section(id="last", priority=100)
            def last(self, ctx: dict) -> str:  # noqa: ARG002
                """Last section."""
                return "Last."

            @section(id="first", priority=1)
            def first(self, ctx: dict) -> str:  # noqa: ARG002
                """First section."""
                return "First."

            @section(id="middle", priority=50)
            def middle(self, ctx: dict) -> str:  # noqa: ARG002
                """Middle section."""
                return "Middle."

        OrderedPrompt()
        registry = get_global_registry()
        renderer = PromptRenderer()

        active = registry.get_active_sections("b", "ordered")
        flag_map = registry.resolve_flags("b", "ordered")
        rendered = renderer.render_sections(active, {}, flag_map.results)
        composed = renderer.compose(rendered)

        # Priority ordering: first(1) < middle(50) < last(100)
        assert composed.index("First.") < composed.index("Middle.")
        assert composed.index("Middle.") < composed.index("Last.")
