"""Tests for config schema validation models.

Tests cover Pydantic v2 config models that validate YAML input,
including field validation, extra field rejection, and cross-reference checks.
"""

import pytest
from pydantic import ValidationError

from prompt_flags.config.schema import (
    BucketDef,
    EnvVarDef,
    FlagDef,
    FlagOverrideDef,
    GlobalConfig,
    OrderingDef,
    PromptDef,
    SectionDef,
)


class TestEnvVarDef:
    """Tests for EnvVarDef config model."""

    def test_defaults(self) -> None:
        """EnvVarDef has sensible defaults."""
        env = EnvVarDef()
        assert env.default is None
        assert env.type == "str"

    def test_custom_values(self) -> None:
        """EnvVarDef accepts custom values."""
        env = EnvVarDef(default="0.7", type="float")
        assert env.default == "0.7"
        assert env.type == "float"

    def test_extra_fields_rejected(self) -> None:
        """EnvVarDef rejects extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            EnvVarDef(default="x", unknown_field="bad")  # type: ignore[call-arg]


class TestOrderingDef:
    """Tests for OrderingDef config model."""

    def test_valid(self) -> None:
        """OrderingDef accepts before/after pair."""
        o = OrderingDef(before="a", after="b")
        assert o.before == "a"
        assert o.after == "b"

    def test_missing_fields(self) -> None:
        """OrderingDef requires both before and after."""
        with pytest.raises(ValidationError):
            OrderingDef(before="a")  # type: ignore[call-arg]

    def test_extra_fields_rejected(self) -> None:
        """OrderingDef rejects extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            OrderingDef(before="a", after="b", weight=5)  # type: ignore[call-arg]


class TestFlagDef:
    """Tests for FlagDef config model."""

    def test_valid(self) -> None:
        """FlagDef accepts default and description."""
        f = FlagDef(default=True, description="test flag")
        assert f.default is True
        assert f.description == "test flag"

    def test_default_description(self) -> None:
        """FlagDef has empty string default for description."""
        f = FlagDef(default=False)
        assert f.description == ""

    def test_missing_default(self) -> None:
        """FlagDef requires default."""
        with pytest.raises(ValidationError):
            FlagDef()  # type: ignore[call-arg]

    def test_extra_fields_rejected(self) -> None:
        """FlagDef rejects extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            FlagDef(default=True, typo="bad")  # type: ignore[call-arg]


class TestFlagOverrideDef:
    """Tests for FlagOverrideDef config model."""

    def test_enabled_true(self) -> None:
        """FlagOverrideDef accepts enabled=True."""
        o = FlagOverrideDef(enabled=True)
        assert o.enabled is True

    def test_enabled_false(self) -> None:
        """FlagOverrideDef accepts enabled=False."""
        o = FlagOverrideDef(enabled=False)
        assert o.enabled is False

    def test_enabled_none_default(self) -> None:
        """FlagOverrideDef defaults to enabled=None (inherit)."""
        o = FlagOverrideDef()
        assert o.enabled is None

    def test_extra_fields_rejected(self) -> None:
        """FlagOverrideDef rejects extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            FlagOverrideDef(enabled=True, extra="bad")  # type: ignore[call-arg]


class TestSectionDef:
    """Tests for SectionDef config model."""

    def test_minimal(self) -> None:
        """SectionDef works with just an id."""
        s = SectionDef(id="my_section")
        assert s.id == "my_section"
        assert s.flag is None
        assert s.priority == 100
        assert s.before == []
        assert s.after == []
        assert s.content is None
        assert s.template is None

    def test_full(self) -> None:
        """SectionDef accepts all fields."""
        s = SectionDef(
            id="reasoning",
            flag="chain_of_thought",
            priority=10,
            before=["output"],
            after=["intro"],
            content="Think step by step.",
        )
        assert s.flag == "chain_of_thought"
        assert s.priority == 10
        assert s.before == ["output"]
        assert s.after == ["intro"]
        assert s.content == "Think step by step."

    def test_extra_fields_rejected(self) -> None:
        """SectionDef rejects extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            SectionDef(id="x", unknown="bad")  # type: ignore[call-arg]


class TestPromptDef:
    """Tests for PromptDef config model."""

    def test_minimal(self) -> None:
        """PromptDef works with no optional fields."""
        p = PromptDef()
        assert p.template is None
        assert p.template_path is None
        assert p.sections == []
        assert p.flags == {}

    def test_with_sections_and_flags(self) -> None:
        """PromptDef accepts sections and flag overrides."""
        p = PromptDef(
            template="coding_guide.j2",
            sections=[SectionDef(id="intro")],
            flags={"verbose": FlagOverrideDef(enabled=False)},
        )
        assert p.template == "coding_guide.j2"
        assert len(p.sections) == 1
        assert p.flags["verbose"].enabled is False

    def test_extra_fields_rejected(self) -> None:
        """PromptDef rejects extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            PromptDef(template="x.j2", bad_field=True)  # type: ignore[call-arg]


class TestBucketDef:
    """Tests for BucketDef config model."""

    def test_defaults(self) -> None:
        """BucketDef has sensible defaults."""
        b = BucketDef()
        assert b.description == ""
        assert b.template_dir is None
        assert b.enabled is True
        assert b.flags == {}
        assert b.prompts == {}
        assert b.ordering == []

    def test_full(self) -> None:
        """BucketDef accepts all fields."""
        b = BucketDef(
            description="Test bucket",
            template_dir="prompts/test",
            enabled=True,
            flags={"cot": FlagOverrideDef(enabled=True)},
            prompts={"my_prompt": PromptDef(template="t.j2")},
            ordering=[OrderingDef(before="a", after="b")],
        )
        assert b.description == "Test bucket"
        assert b.template_dir == "prompts/test"
        assert len(b.flags) == 1
        assert len(b.prompts) == 1
        assert len(b.ordering) == 1

    def test_extra_fields_rejected(self) -> None:
        """BucketDef rejects extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            BucketDef(typo_field="bad")  # type: ignore[call-arg]


class TestGlobalConfig:
    """Tests for GlobalConfig root config model."""

    def test_defaults(self) -> None:
        """GlobalConfig has sensible defaults."""
        c = GlobalConfig()
        assert c.version == "1.0"
        assert c.buckets == {}
        assert c.flags == {}
        assert c.ordering == []
        assert c.env_vars == {}

    def test_valid_config(self) -> None:
        """GlobalConfig accepts a valid full configuration."""
        c = GlobalConfig(
            version="1.0",
            flags={"cot": FlagDef(default=True, description="Chain of thought")},
            buckets={
                "guides": BucketDef(
                    description="Guides",
                    prompts={
                        "coding": PromptDef(
                            template="coding.j2",
                            sections=[SectionDef(id="intro", flag="cot")],
                        ),
                    },
                ),
            },
        )
        assert "cot" in c.flags
        assert "guides" in c.buckets

    def test_extra_fields_rejected(self) -> None:
        """GlobalConfig rejects extra fields."""
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            GlobalConfig(version="1.0", unknown_key="bad")  # type: ignore[call-arg]

    def test_cross_reference_validation_valid(self) -> None:
        """GlobalConfig passes when section flags reference declared flags."""
        # Should not raise
        GlobalConfig(
            flags={"cot": FlagDef(default=True)},
            buckets={
                "b": BucketDef(
                    prompts={
                        "p": PromptDef(
                            sections=[SectionDef(id="s", flag="cot")],
                        ),
                    },
                ),
            },
        )

    def test_cross_reference_validation_invalid(self) -> None:
        """GlobalConfig fails when section flags reference undeclared flags."""
        with pytest.raises(ValidationError, match="undeclared_flag"):
            GlobalConfig(
                flags={"cot": FlagDef(default=True)},
                buckets={
                    "b": BucketDef(
                        prompts={
                            "p": PromptDef(
                                sections=[
                                    SectionDef(id="s", flag="undeclared_flag"),
                                ],
                            ),
                        },
                    ),
                },
            )

    def test_cross_reference_no_flag_ok(self) -> None:
        """GlobalConfig passes when sections have no flag reference."""
        GlobalConfig(
            flags={},
            buckets={
                "b": BucketDef(
                    prompts={
                        "p": PromptDef(
                            sections=[SectionDef(id="s")],
                        ),
                    },
                ),
            },
        )

    def test_bucket_flag_override_references_valid(self) -> None:
        """GlobalConfig passes when bucket flag overrides reference declared flags."""
        GlobalConfig(
            flags={"cot": FlagDef(default=True)},
            buckets={
                "b": BucketDef(
                    flags={"cot": FlagOverrideDef(enabled=True)},
                ),
            },
        )

    def test_bucket_flag_override_references_invalid(self) -> None:
        """GlobalConfig fails when bucket flag overrides reference undeclared flags."""
        with pytest.raises(ValidationError, match="undeclared_flag"):
            GlobalConfig(
                flags={"cot": FlagDef(default=True)},
                buckets={
                    "b": BucketDef(
                        flags={"undeclared_flag": FlagOverrideDef(enabled=True)},
                    ),
                },
            )

    def test_prompt_flag_override_references_invalid(self) -> None:
        """GlobalConfig fails when prompt flag overrides reference undeclared flags."""
        with pytest.raises(ValidationError, match="bad_flag"):
            GlobalConfig(
                flags={"cot": FlagDef(default=True)},
                buckets={
                    "b": BucketDef(
                        prompts={
                            "p": PromptDef(
                                flags={"bad_flag": FlagOverrideDef(enabled=True)},
                            ),
                        },
                    ),
                },
            )
