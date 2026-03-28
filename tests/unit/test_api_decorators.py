"""Tests for the decorator-based API."""

import pytest

from prompt_flags.api.decorators import (
    bucket,
    get_global_registry,
    prompt,
    reset_global_registry,
    section,
)


@pytest.fixture(autouse=True)
def _clean_registry() -> None:
    """Reset the global registry before each test."""
    reset_global_registry()


class TestDecoratorRegistration:
    """Tests that decorators register classes and sections correctly."""

    def test_decorated_class_instantiation_registers_sections(self) -> None:
        """Instantiating a decorated class registers its sections."""

        @bucket("guides")
        @prompt("coding_guide")
        class CodingGuide:
            @section(id="identity", priority=1)
            def identity(self, ctx: dict) -> str:
                return f"You are {ctx['role']}."

        CodingGuide()
        registry = get_global_registry()
        p = registry.get_prompt("guides", "coding_guide")
        assert len(p.sections) == 1
        assert p.sections[0].id == "identity"

    def test_section_with_flag(self) -> None:
        """Section decorator passes flag metadata."""

        @bucket("b")
        @prompt("p")
        class MyPrompt:
            @section(id="reasoning", flag="cot", priority=10)
            def reasoning(self, ctx: dict) -> str:
                return "Think step by step."

        MyPrompt()
        registry = get_global_registry()
        p = registry.get_prompt("b", "p")
        assert p.sections[0].flag == "cot"
        assert p.sections[0].priority == 10

    def test_section_with_before_after(self) -> None:
        """Section decorator supports before/after constraints."""

        @bucket("b")
        @prompt("p")
        class MyPrompt:
            @section(id="a", before=["b"])
            def first(self, ctx: dict) -> str:
                return "A"

            @section(id="b", after=["a"])
            def second(self, ctx: dict) -> str:
                return "B"

        MyPrompt()
        registry = get_global_registry()
        p = registry.get_prompt("b", "p")
        assert p.sections[0].before == ["b"]
        assert p.sections[1].after == ["a"]


class TestSectionMethodCalling:
    """Tests that section methods are called with context."""

    def test_section_method_called_with_context(self) -> None:
        """Decorated methods are called with context to produce content."""

        @bucket("b")
        @prompt("p")
        class MyPrompt:
            @section(id="greeting", priority=1)
            def greeting(self, ctx: dict) -> str:
                return f"Hello {ctx['name']}!"

        instance = MyPrompt()
        # The method itself should still be callable
        result = instance.greeting({"name": "Alice"})
        assert result == "Hello Alice!"

    def test_section_content_from_method(self) -> None:
        """Sections registered from methods use empty-context call for content."""

        @bucket("b")
        @prompt("p")
        class MyPrompt:
            @section(id="static", priority=1)
            def static_section(self, ctx: dict) -> str:
                return "Static content."

        MyPrompt()
        registry = get_global_registry()
        p = registry.get_prompt("b", "p")
        assert p.sections[0].content == "Static content."


class TestGlobalRegistry:
    """Tests for global registry management."""

    def test_get_global_registry_returns_registry(self) -> None:
        """get_global_registry() returns a PromptRegistry."""
        from prompt_flags.core.registry import PromptRegistry

        registry = get_global_registry()
        assert isinstance(registry, PromptRegistry)

    def test_reset_clears_registry(self) -> None:
        """reset_global_registry() clears all registered entities."""

        @bucket("b")
        @prompt("p")
        class MyPrompt:
            @section(id="s")
            def s(self, ctx: dict) -> str:
                return "content"

        MyPrompt()
        reset_global_registry()
        registry = get_global_registry()
        with pytest.raises(KeyError):
            registry.get_bucket("b")

    def test_multiple_classes_register_independently(self) -> None:
        """Multiple decorated classes register into the same global registry."""

        @bucket("b")
        @prompt("p1")
        class Prompt1:
            @section(id="s1")
            def s1(self, ctx: dict) -> str:
                return "content1"

        @bucket("b")
        @prompt("p2")
        class Prompt2:
            @section(id="s2")
            def s2(self, ctx: dict) -> str:
                return "content2"

        Prompt1()
        Prompt2()
        registry = get_global_registry()
        p1 = registry.get_prompt("b", "p1")
        p2 = registry.get_prompt("b", "p2")
        assert p1.sections[0].id == "s1"
        assert p2.sections[0].id == "s2"

    def test_multiple_classes_in_different_buckets(self) -> None:
        """Decorated classes can register into different buckets."""

        @bucket("guides")
        @prompt("p1")
        class Guide:
            @section(id="s1")
            def s1(self, ctx: dict) -> str:
                return "guide content"

        @bucket("tools")
        @prompt("p2")
        class Tool:
            @section(id="s2")
            def s2(self, ctx: dict) -> str:
                return "tool content"

        Guide()
        Tool()
        registry = get_global_registry()
        assert registry.get_bucket("guides").name == "guides"
        assert registry.get_bucket("tools").name == "tools"
