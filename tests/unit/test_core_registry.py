"""Tests for the prompt registry."""

import pytest

from prompt_flags.core.models import (
    Bucket,
    Flag,
    OrderingConstraint,
    Prompt,
    RuntimeOverrides,
    Section,
)
from prompt_flags.core.registry import PromptRegistry
from prompt_flags.core.resolver import UndefinedFlagError


class TestRegistryAddAndGet:
    """Tests for adding and retrieving entities."""

    def test_add_and_get_bucket(self) -> None:
        registry = PromptRegistry()
        bucket = Bucket(name="guides")
        registry.add_bucket(bucket)
        assert registry.get_bucket("guides").name == "guides"

    def test_get_missing_bucket_raises(self) -> None:
        registry = PromptRegistry()
        with pytest.raises(KeyError):
            registry.get_bucket("nonexistent")

    def test_add_and_get_flag(self) -> None:
        registry = PromptRegistry()
        flag = Flag(name="cot", default=True)
        registry.add_flag(flag)
        # Flags are used internally; verify via resolve
        prompt = Prompt(name="p")
        bucket_with_prompt = Bucket(name="b", prompts={"p": prompt})
        registry.add_bucket(bucket_with_prompt)
        results = registry.resolve_flags("b", "p")
        assert results["cot"].value is True

    def test_get_prompt(self) -> None:
        prompt = Prompt(name="coding_guide")
        bucket = Bucket(name="guides", prompts={"coding_guide": prompt})
        registry = PromptRegistry()
        registry.add_bucket(bucket)
        assert registry.get_prompt("guides", "coding_guide").name == "coding_guide"

    def test_get_missing_prompt_raises(self) -> None:
        bucket = Bucket(name="guides")
        registry = PromptRegistry()
        registry.add_bucket(bucket)
        with pytest.raises(KeyError):
            registry.get_prompt("guides", "nonexistent")

    def test_add_ordering_constraint(self) -> None:
        registry = PromptRegistry()
        constraint = OrderingConstraint(before="a", after="b")
        registry.add_ordering_constraint(constraint)
        # Verify by getting active sections with ordering
        sections = [
            Section(id="a", content="A"),
            Section(id="b", content="B"),
        ]
        prompt = Prompt(name="p", sections=sections)
        bucket = Bucket(name="bk", prompts={"p": prompt})
        registry.add_bucket(bucket)
        ordered = registry.get_active_sections("bk", "p")
        assert [s.id for s in ordered] == ["a", "b"]


class TestRegistryResolveFlags:
    """Tests for flag resolution through the registry."""

    def test_resolve_flags_global_default(self) -> None:
        registry = PromptRegistry()
        registry.add_flag(Flag(name="cot", default=True))
        prompt = Prompt(name="p")
        bucket = Bucket(name="b", prompts={"p": prompt})
        registry.add_bucket(bucket)
        results = registry.resolve_flags("b", "p")
        assert results["cot"].value is True

    def test_resolve_flags_bucket_override(self) -> None:
        registry = PromptRegistry()
        registry.add_flag(Flag(name="cot", default=True))
        prompt = Prompt(name="p")
        bucket = Bucket(name="b", prompts={"p": prompt}, flags={"cot": False})
        registry.add_bucket(bucket)
        results = registry.resolve_flags("b", "p")
        assert results["cot"].value is False

    def test_resolve_flags_prompt_override(self) -> None:
        registry = PromptRegistry()
        registry.add_flag(Flag(name="cot", default=True))
        prompt = Prompt(name="p", flags={"cot": False})
        bucket = Bucket(name="b", prompts={"p": prompt})
        registry.add_bucket(bucket)
        results = registry.resolve_flags("b", "p")
        assert results["cot"].value is False

    def test_resolve_flags_runtime_override(self) -> None:
        registry = PromptRegistry()
        registry.add_flag(Flag(name="cot", default=True))
        prompt = Prompt(name="p")
        bucket = Bucket(name="b", prompts={"p": prompt})
        registry.add_bucket(bucket)
        overrides = RuntimeOverrides(flags={"cot": False})
        results = registry.resolve_flags("b", "p", runtime_overrides=overrides)
        assert results["cot"].value is False
        assert results["cot"].source == "runtime"


class TestRegistryActiveSections:
    """Tests for get_active_sections."""

    def test_all_sections_active_when_no_flags(self) -> None:
        registry = PromptRegistry()
        sections = [Section(id="a", content="A"), Section(id="b", content="B")]
        prompt = Prompt(name="p", sections=sections)
        bucket = Bucket(name="bk", prompts={"p": prompt})
        registry.add_bucket(bucket)
        active = registry.get_active_sections("bk", "p")
        assert len(active) == 2

    def test_section_excluded_when_flag_false(self) -> None:
        registry = PromptRegistry()
        registry.add_flag(Flag(name="cot", default=False))
        sections = [
            Section(id="a", content="A"),
            Section(id="b", content="B", flag="cot"),
        ]
        prompt = Prompt(name="p", sections=sections)
        bucket = Bucket(name="bk", prompts={"p": prompt})
        registry.add_bucket(bucket)
        active = registry.get_active_sections("bk", "p")
        assert len(active) == 1
        assert active[0].id == "a"

    def test_section_included_when_flag_true(self) -> None:
        registry = PromptRegistry()
        registry.add_flag(Flag(name="cot", default=True))
        sections = [
            Section(id="a", content="A"),
            Section(id="b", content="B", flag="cot"),
        ]
        prompt = Prompt(name="p", sections=sections)
        bucket = Bucket(name="bk", prompts={"p": prompt})
        registry.add_bucket(bucket)
        active = registry.get_active_sections("bk", "p")
        assert len(active) == 2

    def test_active_sections_are_ordered(self) -> None:
        registry = PromptRegistry()
        registry.add_ordering_constraint(OrderingConstraint(before="b", after="a"))
        sections = [
            Section(id="a", content="A", priority=1),
            Section(id="b", content="B", priority=100),
        ]
        prompt = Prompt(name="p", sections=sections)
        bucket = Bucket(name="bk", prompts={"p": prompt})
        registry.add_bucket(bucket)
        active = registry.get_active_sections("bk", "p")
        assert [s.id for s in active] == ["b", "a"]

    def test_runtime_override_excludes_section(self) -> None:
        registry = PromptRegistry()
        registry.add_flag(Flag(name="cot", default=True))
        sections = [
            Section(id="a", content="A"),
            Section(id="b", content="B", flag="cot"),
        ]
        prompt = Prompt(name="p", sections=sections)
        bucket = Bucket(name="bk", prompts={"p": prompt})
        registry.add_bucket(bucket)
        overrides = RuntimeOverrides(flags={"cot": False})
        active = registry.get_active_sections("bk", "p", runtime_overrides=overrides)
        assert len(active) == 1
        assert active[0].id == "a"

    def test_strict_mode_raises_for_undefined_flag(self) -> None:
        registry = PromptRegistry(strict=True)
        sections = [Section(id="a", content="A", flag="undefined_flag")]
        prompt = Prompt(name="p", sections=sections)
        bucket = Bucket(name="bk", prompts={"p": prompt})
        registry.add_bucket(bucket)
        with pytest.raises(UndefinedFlagError):
            registry.get_active_sections("bk", "p")

    def test_non_strict_mode_defaults_undefined_flag_to_false(self) -> None:
        registry = PromptRegistry(strict=False)
        sections = [Section(id="a", content="A", flag="undefined_flag")]
        prompt = Prompt(name="p", sections=sections)
        bucket = Bucket(name="bk", prompts={"p": prompt})
        registry.add_bucket(bucket)
        active = registry.get_active_sections("bk", "p")
        assert len(active) == 0
