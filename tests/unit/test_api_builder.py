"""Tests for the fluent builder API."""

from prompt_flags.api.builder import PromptBuilder
from prompt_flags.core.registry import PromptRegistry


class TestBuilderChaining:
    """Tests that the builder chain creates correct registry state."""

    def test_basic_builder_creates_registry(self) -> None:
        """Builder with minimal config returns a PromptRegistry."""
        registry = (
            PromptBuilder("my_prompt")
            .in_bucket("guides", description="Guide prompts")
            .section("intro", "Hello world.")
            .build()
        )
        assert isinstance(registry, PromptRegistry)

    def test_builder_registers_bucket(self) -> None:
        """Builder registers the bucket with correct name and description."""
        registry = (
            PromptBuilder("my_prompt")
            .in_bucket("guides", description="Guide prompts")
            .section("intro", "Hello world.")
            .build()
        )
        bucket = registry.get_bucket("guides")
        assert bucket.name == "guides"
        assert bucket.description == "Guide prompts"

    def test_builder_registers_prompt(self) -> None:
        """Builder registers the prompt inside the bucket."""
        registry = (
            PromptBuilder("my_prompt")
            .in_bucket("guides")
            .section("intro", "Hello world.")
            .build()
        )
        prompt = registry.get_prompt("guides", "my_prompt")
        assert prompt.name == "my_prompt"

    def test_builder_registers_sections(self) -> None:
        """Builder registers sections with correct content and metadata."""
        registry = (
            PromptBuilder("my_prompt")
            .in_bucket("guides")
            .section("identity", "You are a helper.", priority=1)
            .section("reasoning", "Think step by step.", flag="cot", priority=10)
            .build()
        )
        prompt = registry.get_prompt("guides", "my_prompt")
        assert len(prompt.sections) == 2
        assert prompt.sections[0].id == "identity"
        assert prompt.sections[0].content == "You are a helper."
        assert prompt.sections[0].priority == 1
        assert prompt.sections[1].id == "reasoning"
        assert prompt.sections[1].flag == "cot"

    def test_builder_section_before_after(self) -> None:
        """Builder section() supports before and after constraints."""
        registry = (
            PromptBuilder("p")
            .in_bucket("b")
            .section("a", "A", before=["b"])
            .section("b", "B", after=["a"])
            .build()
        )
        prompt = registry.get_prompt("b", "p")
        assert prompt.sections[0].before == ["b"]
        assert prompt.sections[1].after == ["a"]


class TestBuilderFlags:
    """Tests for flag registration."""

    def test_flag_method_registers_flag(self) -> None:
        """Builder flag() registers a Flag in the registry."""
        registry = (
            PromptBuilder("p")
            .in_bucket("b")
            .section("s", "content", flag="cot")
            .flag("cot", default=True, description="Chain of thought")
            .build()
        )
        # Flag should be resolvable
        results = registry.resolve_flags("b", "p")
        assert results["cot"].value is True

    def test_flag_default_false(self) -> None:
        """Builder flag() with default=False resolves correctly."""
        registry = (
            PromptBuilder("p")
            .in_bucket("b")
            .section("s", "content", flag="json")
            .flag("json", default=False)
            .build()
        )
        results = registry.resolve_flags("b", "p")
        assert results["json"].value is False


class TestBuilderOrdering:
    """Tests for ordering constraints."""

    def test_order_method_adds_constraint(self) -> None:
        """Builder order() creates ordering constraints."""
        registry = (
            PromptBuilder("p")
            .in_bucket("b")
            .section("identity", "I am X.", priority=100)
            .section("reasoning", "Think.", priority=1)
            .order("identity", after="reasoning")
            .build()
        )
        # identity should come before reasoning despite higher priority
        active = registry.get_active_sections("b", "p")
        ids = [s.id for s in active]
        assert ids.index("identity") < ids.index("reasoning")


class TestBuilderBucketFlagOverride:
    """Tests for bucket-level flag overrides."""

    def test_bucket_flag_override(self) -> None:
        """Builder bucket_flag_override() sets bucket-level flag overrides."""
        registry = (
            PromptBuilder("p")
            .in_bucket("b")
            .section("s", "content", flag="cot")
            .flag("cot", default=False)
            .bucket_flag_override("cot", True)
            .build()
        )
        results = registry.resolve_flags("b", "p")
        assert results["cot"].value is True
        assert results["cot"].source == "bucket"


class TestBuilderRender:
    """Tests for the render() convenience method."""

    def test_render_returns_string(self) -> None:
        """render() builds and renders in one step."""
        result = (
            PromptBuilder("p")
            .in_bucket("b")
            .section("greeting", "Hello world.")
            .render()
        )
        assert result == "Hello world."

    def test_render_with_context(self) -> None:
        """render() passes context to Jinja2 templates."""
        result = (
            PromptBuilder("p")
            .in_bucket("b")
            .section("greeting", "Hello {{ name }}.")
            .render(context={"name": "Alice"})
        )
        assert result == "Hello Alice."

    def test_render_with_flags(self) -> None:
        """render() respects flag overrides."""
        result = (
            PromptBuilder("p")
            .in_bucket("b")
            .section("always", "Always here.")
            .section("optional", "Maybe here.", flag="show")
            .flag("show", default=True)
            .render(flags={"show": False})
        )
        assert "Always here." in result
        assert "Maybe here." not in result

    def test_render_multiple_sections_joined(self) -> None:
        """render() joins multiple sections with double newlines."""
        result = (
            PromptBuilder("p")
            .in_bucket("b")
            .section("a", "Section A.")
            .section("b", "Section B.")
            .render()
        )
        assert "Section A." in result
        assert "Section B." in result

    def test_render_end_to_end(self) -> None:
        """Full end-to-end: builder + flags + ordering + render."""
        result = (
            PromptBuilder("coding_guide")
            .in_bucket("guides")
            .section("identity", "You are a {{ role }}.", priority=1)
            .section("reasoning", "Think step by step.", flag="cot", priority=10)
            .section(
                "format", "Respond in {{ fmt }}.", flag="json", priority=20, after=["reasoning"]
            )
            .flag("cot", default=True)
            .flag("json", default=False)
            .order("identity", after="reasoning")
            .render(context={"role": "coding assistant", "fmt": "JSON"}, flags={"json": True})
        )
        assert "You are a coding assistant." in result
        assert "Think step by step." in result
        assert "Respond in JSON." in result


class TestBuilderDefaults:
    """Tests for default behavior."""

    def test_builder_without_bucket_uses_default(self) -> None:
        """Builder without in_bucket() uses 'default' bucket name."""
        registry = (
            PromptBuilder("p")
            .section("s", "content")
            .build()
        )
        bucket = registry.get_bucket("default")
        assert bucket.name == "default"

    def test_builder_returns_self_for_chaining(self) -> None:
        """All builder methods return self for fluent chaining."""
        builder = PromptBuilder("p")
        assert builder.in_bucket("b") is builder
        assert builder.section("s", "c") is builder
        assert builder.flag("f", default=True) is builder
        assert builder.order("a", after="b") is builder
        assert builder.bucket_flag_override("f", True) is builder
