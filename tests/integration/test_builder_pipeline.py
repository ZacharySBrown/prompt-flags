"""Integration tests for the fluent builder API end-to-end.

Tests the full lifecycle: build -> resolve flags -> order -> render -> compose.
"""

from prompt_flags.api.builder import PromptBuilder


class TestBuilderPipeline:
    """Test the fluent builder API end-to-end."""

    def test_builder_render(self) -> None:
        """Build a prompt with builder API and render it."""
        result = (
            PromptBuilder("assistant")
            .in_bucket("system")
            .section("identity", "You are a helpful coding assistant.")
            .section("task", "Answer programming questions clearly.")
            .render()
        )
        assert "You are a helpful coding assistant." in result
        assert "Answer programming questions clearly." in result

    def test_builder_with_flag_overrides(self) -> None:
        """Builder prompt with runtime flag overrides."""
        # Default: cot=True, json=False
        builder = (
            PromptBuilder("guide")
            .in_bucket("guides")
            .section("intro", "Welcome.")
            .section("reasoning", "Think step by step.", flag="cot")
            .section("format", "Respond in JSON.", flag="json")
            .flag("cot", default=True)
            .flag("json", default=False)
        )

        # Without overrides: cot on, json off
        result = builder.render()
        assert "Think step by step." in result
        assert "Respond in JSON." not in result

        # With overrides: cot off, json on
        result_overridden = builder.render(flags={"cot": False, "json": True})
        assert "Think step by step." not in result_overridden
        assert "Respond in JSON." in result_overridden
        # Intro is always present (no flag)
        assert "Welcome." in result_overridden

    def test_builder_section_ordering(self) -> None:
        """Verify builder respects ordering constraints."""
        result = (
            PromptBuilder("ordered")
            .in_bucket("b")
            .section("conclusion", "That is all.", priority=100)
            .section("intro", "Hello.", priority=1)
            .section("middle", "Here is the main point.", priority=50)
            .order("intro", after="middle")
            .order("middle", after="conclusion")
            .render()
        )
        # Ordering should be: intro -> middle -> conclusion
        intro_pos = result.index("Hello.")
        middle_pos = result.index("Here is the main point.")
        conclusion_pos = result.index("That is all.")
        assert intro_pos < middle_pos < conclusion_pos

    def test_builder_with_jinja2_templates(self) -> None:
        """Builder sections with Jinja2 template syntax."""
        result = (
            PromptBuilder("templated")
            .in_bucket("b")
            .section("greeting", "Hello {{ name }}, you are a {{ role }}.")
            .section("task", "Please {{ action }} the following.")
            .render(context={"name": "Alice", "role": "engineer", "action": "review"})
        )
        assert "Hello Alice, you are a engineer." in result
        assert "Please review the following." in result

    def test_builder_with_bucket_flag_override(self) -> None:
        """Builder bucket-level flag override affects rendering."""
        result = (
            PromptBuilder("p")
            .in_bucket("b")
            .section("always", "Always here.")
            .section("optional", "Bucket says yes.", flag="feature")
            .flag("feature", default=False)
            .bucket_flag_override("feature", True)
            .render()
        )
        # Bucket override makes feature=True even though default is False
        assert "Bucket says yes." in result

    def test_builder_multiple_flags_interact(self) -> None:
        """Multiple flags controlling different sections work independently."""
        builder = (
            PromptBuilder("multi")
            .in_bucket("b")
            .section("base", "Base content.")
            .section("a", "Section A.", flag="flag_a")
            .section("b", "Section B.", flag="flag_b")
            .section("c", "Section C.", flag="flag_c")
            .flag("flag_a", default=True)
            .flag("flag_b", default=False)
            .flag("flag_c", default=True)
        )

        result = builder.render()
        assert "Base content." in result
        assert "Section A." in result
        assert "Section B." not in result
        assert "Section C." in result

    def test_builder_ordering_with_flags(self) -> None:
        """Ordering constraints only apply to active (flag-enabled) sections."""
        result = (
            PromptBuilder("p")
            .in_bucket("b")
            .section("first", "First.", priority=1)
            .section("middle", "Middle.", flag="show_middle", priority=50)
            .section("last", "Last.", priority=100)
            .flag("show_middle", default=True)
            .order("first", after="middle")
            .order("middle", after="last")
            .render()
        )
        assert result.index("First.") < result.index("Middle.")
        assert result.index("Middle.") < result.index("Last.")

        # Now disable middle -- first and last should still render in order
        result2 = (
            PromptBuilder("p")
            .in_bucket("b")
            .section("first", "First.", priority=1)
            .section("middle", "Middle.", flag="show_middle", priority=50)
            .section("last", "Last.", priority=100)
            .flag("show_middle", default=True)
            .order("first", after="middle")
            .order("middle", after="last")
            .render(flags={"show_middle": False})
        )
        assert "Middle." not in result2
        assert "First." in result2
        assert "Last." in result2
