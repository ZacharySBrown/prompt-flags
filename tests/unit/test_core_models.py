"""Tests for core domain models."""

import pytest
from pydantic import ValidationError

from prompt_flags.core.models import (
    Bucket,
    Flag,
    FlagOverrides,
    FlagResult,
    OrderingConstraint,
    Prompt,
    RenderedSection,
    Section,
)


class TestSection:
    """Tests for the Section model."""

    def test_minimal_section(self) -> None:
        s = Section(id="intro")
        assert s.id == "intro"
        assert s.content is None
        assert s.template_path is None
        assert s.flag is None
        assert s.priority == 100
        assert s.before == []
        assert s.after == []

    def test_full_section(self) -> None:
        s = Section(
            id="reasoning",
            content="Think step by step.",
            flag="chain_of_thought",
            priority=10,
            before=["output"],
            after=["identity"],
        )
        assert s.id == "reasoning"
        assert s.content == "Think step by step."
        assert s.flag == "chain_of_thought"
        assert s.priority == 10
        assert s.before == ["output"]
        assert s.after == ["identity"]

    def test_section_with_template_path(self) -> None:
        s = Section(id="intro", template_path="templates/intro.j2")
        assert s.template_path == "templates/intro.j2"

    def test_section_is_frozen(self) -> None:
        s = Section(id="intro")
        with pytest.raises(ValidationError):
            s.id = "changed"  # type: ignore[misc]

    def test_section_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            Section(id="intro", unknown_field="bad")  # type: ignore[call-arg]


class TestPrompt:
    """Tests for the Prompt model."""

    def test_minimal_prompt(self) -> None:
        p = Prompt(name="coding_guide")
        assert p.name == "coding_guide"
        assert p.template is None
        assert p.template_path is None
        assert p.sections == []
        assert p.flags == {}

    def test_prompt_with_sections(self) -> None:
        s = Section(id="intro", content="Hello")
        p = Prompt(name="guide", sections=[s])
        assert len(p.sections) == 1
        assert p.sections[0].id == "intro"

    def test_prompt_with_flags(self) -> None:
        p = Prompt(name="guide", flags={"cot": True, "json": None})
        assert p.flags["cot"] is True
        assert p.flags["json"] is None

    def test_prompt_is_frozen(self) -> None:
        p = Prompt(name="guide")
        with pytest.raises(ValidationError):
            p.name = "changed"  # type: ignore[misc]

    def test_prompt_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            Prompt(name="guide", bad="field")  # type: ignore[call-arg]


class TestBucket:
    """Tests for the Bucket model."""

    def test_minimal_bucket(self) -> None:
        b = Bucket(name="guides")
        assert b.name == "guides"
        assert b.description == ""
        assert b.template_dir is None
        assert b.enabled is True
        assert b.prompts == {}
        assert b.flags == {}

    def test_full_bucket(self) -> None:
        p = Prompt(name="coding_guide")
        b = Bucket(
            name="guides",
            description="Step-by-step guides",
            template_dir="prompts/guides",
            enabled=True,
            prompts={"coding_guide": p},
            flags={"cot": True},
        )
        assert b.description == "Step-by-step guides"
        assert "coding_guide" in b.prompts
        assert b.flags["cot"] is True

    def test_bucket_is_frozen(self) -> None:
        b = Bucket(name="guides")
        with pytest.raises(ValidationError):
            b.name = "changed"  # type: ignore[misc]

    def test_bucket_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError):
            Bucket(name="guides", unknown="bad")  # type: ignore[call-arg]


class TestFlag:
    """Tests for the Flag model."""

    def test_flag_defaults(self) -> None:
        f = Flag(name="cot", default=True)
        assert f.name == "cot"
        assert f.default is True
        assert f.description == ""

    def test_flag_with_description(self) -> None:
        f = Flag(name="cot", default=True, description="Chain of thought")
        assert f.description == "Chain of thought"

    def test_flag_is_frozen(self) -> None:
        f = Flag(name="cot", default=True)
        with pytest.raises(ValidationError):
            f.default = False  # type: ignore[misc]


class TestFlagOverrides:
    """Tests for the FlagOverrides model."""

    def test_empty_overrides(self) -> None:
        fo = FlagOverrides()
        assert fo.global_value is None
        assert fo.bucket_overrides == {}
        assert fo.prompt_overrides == {}

    def test_full_overrides(self) -> None:
        fo = FlagOverrides(
            global_value=True,
            bucket_overrides={"guides": False},
            prompt_overrides={"guides": {"coding": True}},
        )
        assert fo.global_value is True
        assert fo.bucket_overrides["guides"] is False
        assert fo.prompt_overrides["guides"]["coding"] is True


class TestOrderingConstraint:
    """Tests for the OrderingConstraint model."""

    def test_minimal_constraint(self) -> None:
        c = OrderingConstraint(before="a", after="b")
        assert c.before == "a"
        assert c.after == "b"
        assert c.source == ""

    def test_constraint_with_source(self) -> None:
        c = OrderingConstraint(before="a", after="b", source="global")
        assert c.source == "global"


class TestFlagResult:
    """Tests for the FlagResult model."""

    def test_flag_result(self) -> None:
        r = FlagResult(name="cot", value=True, source="bucket:guides")
        assert r.name == "cot"
        assert r.value is True
        assert r.source == "bucket:guides"


class TestRenderedSection:
    """Tests for the RenderedSection model."""

    def test_rendered_section(self) -> None:
        rs = RenderedSection(id="intro", content="Hello world")
        assert rs.id == "intro"
        assert rs.content == "Hello world"
        assert rs.flag is None

    def test_rendered_section_with_flag(self) -> None:
        rs = RenderedSection(id="intro", content="Hello", flag="cot")
        assert rs.flag == "cot"
