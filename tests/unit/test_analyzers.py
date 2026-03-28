"""Tests for the dependency analysis tools."""

import pytest
from tools.analyzers.conflict_detector import detect_conflicts
from tools.analyzers.dependency_trace import trace_prompt_dependencies
from tools.analyzers.flag_impact import flag_impact
from tools.analyzers.gap_analysis import gap_analysis
from tools.analyzers.unused_flags import find_unused_flags

from prompt_flags.core.models import (
    Bucket,
    Flag,
    Prompt,
    Section,
)
from prompt_flags.core.registry import PromptRegistry


def _make_registry() -> PromptRegistry:
    """Build a registry for analyzer tests."""
    registry = PromptRegistry()
    registry.add_flag(Flag(name="cot", default=True))
    registry.add_flag(Flag(name="examples", default=False))
    registry.add_flag(Flag(name="unused_flag", default=True))

    section_identity = Section(id="identity", content="You are a helper.")
    section_reasoning = Section(id="reasoning", content="Think step by step.", flag="cot")
    section_examples = Section(id="examples_sec", content="Examples here.", flag="examples")

    prompt_a = Prompt(
        name="prompt_a",
        sections=[section_identity, section_reasoning, section_examples],
        flags={"cot": False},
    )
    prompt_b = Prompt(
        name="prompt_b",
        sections=[section_identity, section_reasoning],
        flags={},
    )

    bucket = Bucket(
        name="guides",
        prompts={"prompt_a": prompt_a, "prompt_b": prompt_b},
        flags={"examples": True},
    )
    registry.add_bucket(bucket)
    return registry


class TestFlagImpact:
    """Tests for the flag impact analyzer."""

    def test_sections_controlled_by_flag(self) -> None:
        registry = _make_registry()
        result = flag_impact(registry, "cot")
        section_ids = [s["id"] for s in result["sections"]]
        assert "reasoning" in section_ids

    def test_prompts_overriding_flag(self) -> None:
        registry = _make_registry()
        result = flag_impact(registry, "cot")
        prompt_ids = [p["id"] for p in result["prompts"]]
        assert "prompt_a" in prompt_ids

    def test_buckets_overriding_flag(self) -> None:
        registry = _make_registry()
        result = flag_impact(registry, "examples")
        bucket_ids = [b["id"] for b in result["buckets"]]
        assert "guides" in bucket_ids

    def test_unknown_flag_raises(self) -> None:
        registry = _make_registry()
        with pytest.raises(KeyError, match="not defined"):
            flag_impact(registry, "nonexistent")

    def test_unused_flag_has_no_sections(self) -> None:
        registry = _make_registry()
        result = flag_impact(registry, "unused_flag")
        assert len(result["sections"]) == 0


class TestGapAnalysis:
    """Tests for the flag override gap analyzer."""

    def test_reports_bucket_gaps(self) -> None:
        registry = _make_registry()
        report = gap_analysis(registry)
        bucket_gaps = [g for g in report.gaps if g.level == "bucket"]
        # guides bucket doesn't override "cot" or "unused_flag" at bucket level
        gap_flags = {g.flag_name for g in bucket_gaps}
        assert "cot" in gap_flags
        assert "unused_flag" in gap_flags

    def test_reports_prompt_gaps(self) -> None:
        registry = _make_registry()
        report = gap_analysis(registry)
        prompt_gaps = [g for g in report.gaps if g.level == "prompt"]
        # prompt_b doesn't override "cot" at prompt level
        assert any(g.prompt_name == "prompt_b" and g.flag_name == "cot" for g in prompt_gaps)

    def test_no_gap_for_explicit_override(self) -> None:
        registry = _make_registry()
        report = gap_analysis(registry)
        bucket_gaps = [g for g in report.gaps if g.level == "bucket"]
        # guides bucket explicitly overrides "examples", so no bucket-level gap for it
        assert not any(g.flag_name == "examples" and g.bucket_name == "guides" for g in bucket_gaps)

    def test_coverage_stats(self) -> None:
        registry = _make_registry()
        report = gap_analysis(registry)
        assert "cot" in report.coverage
        assert "examples" in report.coverage
        # examples has 100% bucket coverage (1 bucket, 1 override)
        assert report.coverage["examples"]["bucket_coverage_pct"] == 100.0

    def test_inherited_value_tracked(self) -> None:
        registry = _make_registry()
        report = gap_analysis(registry)
        prompt_gaps = [
            g
            for g in report.gaps
            if g.level == "prompt" and g.flag_name == "cot" and g.prompt_name == "prompt_b"
        ]
        assert len(prompt_gaps) == 1
        # prompt_b inherits cot=True from global default (no bucket override)
        assert prompt_gaps[0].resolved_value is True
        assert prompt_gaps[0].resolved_source == "global"

    def test_full_coverage_no_gaps(self) -> None:
        """A registry where every scope has an override produces no gaps."""
        registry = PromptRegistry()
        registry.add_flag(Flag(name="f", default=True))
        prompt = Prompt(name="p", sections=[], flags={"f": False})
        bucket = Bucket(name="b", prompts={"p": prompt}, flags={"f": True})
        registry.add_bucket(bucket)
        report = gap_analysis(registry)
        assert len(report.gaps) == 0


class TestUnusedFlags:
    """Tests for the unused flags detector."""

    def test_finds_unused_flag(self) -> None:
        registry = _make_registry()
        unused = find_unused_flags(registry)
        unused_names = [f.name for f in unused]
        assert "unused_flag" in unused_names

    def test_used_flags_not_reported(self) -> None:
        registry = _make_registry()
        unused = find_unused_flags(registry)
        unused_names = [f.name for f in unused]
        assert "cot" not in unused_names
        assert "examples" not in unused_names

    def test_has_overrides_tracked(self) -> None:
        """A flag with overrides but no section refs is still unused."""
        registry = PromptRegistry()
        registry.add_flag(Flag(name="f", default=True))
        prompt = Prompt(name="p", sections=[], flags={"f": False})
        bucket = Bucket(name="b", prompts={"p": prompt})
        registry.add_bucket(bucket)
        unused = find_unused_flags(registry)
        assert len(unused) == 1
        assert unused[0].has_overrides is True

    def test_no_unused_flags(self) -> None:
        registry = PromptRegistry()
        registry.add_flag(Flag(name="f", default=True))
        section = Section(id="s", content="text", flag="f")
        prompt = Prompt(name="p", sections=[section])
        bucket = Bucket(name="b", prompts={"p": prompt})
        registry.add_bucket(bucket)
        unused = find_unused_flags(registry)
        assert len(unused) == 0


class TestDependencyTrace:
    """Tests for the dependency trace tool."""

    def test_trace_lists_sections(self) -> None:
        registry = _make_registry()
        trace = trace_prompt_dependencies(registry, "guides", "prompt_a")
        section_ids = [s["id"] for s in trace.sections]
        assert "identity" in section_ids
        assert "reasoning" in section_ids
        assert "examples_sec" in section_ids

    def test_trace_lists_flags_used(self) -> None:
        registry = _make_registry()
        trace = trace_prompt_dependencies(registry, "guides", "prompt_a")
        assert "cot" in trace.flags_used
        assert "examples" in trace.flags_used

    def test_trace_lists_prompt_overrides(self) -> None:
        registry = _make_registry()
        trace = trace_prompt_dependencies(registry, "guides", "prompt_a")
        assert "cot" in trace.flags_overridden

    def test_trace_lists_bucket_overrides(self) -> None:
        registry = _make_registry()
        trace = trace_prompt_dependencies(registry, "guides", "prompt_a")
        assert "examples" in trace.bucket_flag_overrides

    def test_trace_invalid_prompt_raises(self) -> None:
        registry = _make_registry()
        with pytest.raises(KeyError):
            trace_prompt_dependencies(registry, "guides", "nonexistent")

    def test_trace_prompt_with_no_flags(self) -> None:
        registry = PromptRegistry()
        registry.add_flag(Flag(name="f", default=True))
        section = Section(id="s", content="text")
        prompt = Prompt(name="p", sections=[section])
        bucket = Bucket(name="b", prompts={"p": prompt})
        registry.add_bucket(bucket)
        trace = trace_prompt_dependencies(registry, "b", "p")
        assert len(trace.flags_used) == 0
        assert len(trace.flags_overridden) == 0


class TestConflictDetector:
    """Tests for the flag conflict detector."""

    def test_detects_redundant_bucket_override(self) -> None:
        """Bucket override matching global default is redundant."""
        registry = PromptRegistry()
        registry.add_flag(Flag(name="f", default=True))
        prompt = Prompt(name="p", sections=[])
        bucket = Bucket(name="b", prompts={"p": prompt}, flags={"f": True})
        registry.add_bucket(bucket)
        report = detect_conflicts(registry)
        redundant = [c for c in report.conflicts if c.kind == "redundant_bucket_override"]
        assert len(redundant) == 1

    def test_detects_redundant_prompt_override(self) -> None:
        """Prompt override matching effective bucket value is redundant."""
        registry = PromptRegistry()
        registry.add_flag(Flag(name="f", default=True))
        prompt = Prompt(name="p", sections=[], flags={"f": True})
        bucket = Bucket(name="b", prompts={"p": prompt})
        registry.add_bucket(bucket)
        report = detect_conflicts(registry)
        redundant = [c for c in report.conflicts if c.kind == "redundant_prompt_override"]
        assert len(redundant) == 1

    def test_detects_should_be_bucket_override(self) -> None:
        """All prompts overriding same flag to same value should be bucket-level."""
        registry = PromptRegistry()
        registry.add_flag(Flag(name="f", default=True))
        p1 = Prompt(name="p1", sections=[], flags={"f": False})
        p2 = Prompt(name="p2", sections=[], flags={"f": False})
        bucket = Bucket(name="b", prompts={"p1": p1, "p2": p2})
        registry.add_bucket(bucket)
        report = detect_conflicts(registry)
        bucket_conflicts = [c for c in report.conflicts if c.kind == "should_be_bucket_override"]
        assert len(bucket_conflicts) == 1

    def test_detects_undefined_flag_override_in_bucket(self) -> None:
        registry = PromptRegistry()
        prompt = Prompt(name="p", sections=[])
        bucket = Bucket(name="b", prompts={"p": prompt}, flags={"nonexistent": True})
        registry.add_bucket(bucket)
        report = detect_conflicts(registry)
        undef = [c for c in report.conflicts if c.kind == "undefined_flag_override"]
        assert len(undef) == 1

    def test_detects_undefined_flag_override_in_prompt(self) -> None:
        registry = PromptRegistry()
        prompt = Prompt(name="p", sections=[], flags={"nonexistent": True})
        bucket = Bucket(name="b", prompts={"p": prompt})
        registry.add_bucket(bucket)
        report = detect_conflicts(registry)
        undef = [c for c in report.conflicts if c.kind == "undefined_flag_override"]
        assert len(undef) == 1

    def test_no_conflicts_clean_config(self) -> None:
        """A well-structured config should produce no conflicts."""
        registry = PromptRegistry()
        registry.add_flag(Flag(name="f", default=True))
        section = Section(id="s", content="text", flag="f")
        prompt = Prompt(name="p", sections=[section], flags={"f": False})
        bucket = Bucket(name="b", prompts={"p": prompt})
        registry.add_bucket(bucket)
        report = detect_conflicts(registry)
        assert len(report.conflicts) == 0
