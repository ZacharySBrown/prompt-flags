"""Gap analysis: find prompts/buckets missing flag overrides.

Identifies where flags are defined globally but have no specific override
at the bucket or prompt level, helping teams ensure intentional flag
coverage across all scopes.

Usage:
    uv run python -m tools.analyzers.gap_analysis <config.yaml>
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

from prompt_flags.core.registry import PromptRegistry


@dataclass(frozen=True)
class FlagGap:
    """A missing flag override at a specific scope.

    Attributes:
        flag_name: The flag that lacks an override.
        bucket_name: The bucket scope.
        prompt_name: The prompt scope, if applicable.
        level: Whether the gap is at "bucket" or "prompt" level.
        resolved_value: What the flag resolves to (inherited from parent).
        resolved_source: Which tier provides the current value.
    """

    flag_name: str
    bucket_name: str
    prompt_name: str = ""
    level: str = "bucket"
    resolved_value: bool = False
    resolved_source: str = "global"


@dataclass
class GapReport:
    """Complete gap analysis results.

    Attributes:
        gaps: All identified gaps.
        total_flags: Total number of defined flags.
        total_buckets: Total number of buckets.
        total_prompts: Total number of prompts across all buckets.
        coverage: Per-flag coverage statistics.
    """

    gaps: list[FlagGap] = field(default_factory=list)
    total_flags: int = 0
    total_buckets: int = 0
    total_prompts: int = 0
    coverage: dict[str, dict[str, int | float]] = field(default_factory=dict)


def gap_analysis(registry: PromptRegistry) -> GapReport:
    """Analyze flag override coverage across all buckets and prompts.

    For each flag, checks every bucket and prompt to see whether an explicit
    override exists. Reports gaps where the flag falls through to a parent tier.

    Args:
        registry: The populated prompt registry.

    Returns:
        A GapReport with all identified gaps and coverage stats.
    """
    flags = registry._flags
    buckets = registry._buckets

    total_prompts = sum(len(b.prompts) for b in buckets.values())
    report = GapReport(
        total_flags=len(flags),
        total_buckets=len(buckets),
        total_prompts=total_prompts,
    )

    for flag_name, flag_def in flags.items():
        bucket_overrides = 0
        prompt_overrides = 0
        total_prompt_scopes = 0

        for bucket in buckets.values():
            has_bucket_override = flag_name in bucket.flags and bucket.flags[flag_name] is not None
            if has_bucket_override:
                bucket_overrides += 1
            else:
                report.gaps.append(
                    FlagGap(
                        flag_name=flag_name,
                        bucket_name=bucket.name,
                        level="bucket",
                        resolved_value=flag_def.default,
                        resolved_source="global",
                    )
                )

            for prompt in bucket.prompts.values():
                total_prompt_scopes += 1
                has_prompt_override = (
                    flag_name in prompt.flags and prompt.flags[flag_name] is not None
                )
                if has_prompt_override:
                    prompt_overrides += 1
                else:
                    # Determine what value this prompt inherits
                    if has_bucket_override:
                        resolved_val = bucket.flags[flag_name]  # type: ignore[assignment]
                        resolved_src = "bucket"
                    else:
                        resolved_val = flag_def.default
                        resolved_src = "global"
                    report.gaps.append(
                        FlagGap(
                            flag_name=flag_name,
                            bucket_name=bucket.name,
                            prompt_name=prompt.name,
                            level="prompt",
                            resolved_value=resolved_val,
                            resolved_source=resolved_src,
                        )
                    )

        # Coverage stats for this flag
        bucket_coverage = (bucket_overrides / len(buckets) * 100) if buckets else 0.0
        prompt_coverage = (
            (prompt_overrides / total_prompt_scopes * 100) if total_prompt_scopes else 0.0
        )
        report.coverage[flag_name] = {
            "bucket_overrides": bucket_overrides,
            "prompt_overrides": prompt_overrides,
            "bucket_coverage_pct": round(bucket_coverage, 1),
            "prompt_coverage_pct": round(prompt_coverage, 1),
        }

    return report


def format_gap_report(report: GapReport) -> str:
    """Format a GapReport as a human-readable string.

    Args:
        report: The gap analysis results.

    Returns:
        A formatted string report.
    """
    lines: list[str] = [
        "Flag Override Gap Analysis",
        "=" * 50,
        f"Flags: {report.total_flags}  |  Buckets: {report.total_buckets}"
        f"  |  Prompts: {report.total_prompts}",
        "",
    ]

    # Coverage summary table
    lines.append("Coverage Summary:")
    lines.append("-" * 50)
    lines.append(f"  {'Flag':<25} {'Bucket %':>10} {'Prompt %':>10}")
    lines.append(f"  {'-' * 25} {'-' * 10} {'-' * 10}")
    for flag_name, stats in sorted(report.coverage.items()):
        lines.append(
            f"  {flag_name:<25} {stats['bucket_coverage_pct']:>9.1f}%"
            f" {stats['prompt_coverage_pct']:>9.1f}%"
        )

    # Bucket-level gaps
    bucket_gaps = [g for g in report.gaps if g.level == "bucket"]
    if bucket_gaps:
        lines.append(f"\nBucket-Level Gaps ({len(bucket_gaps)}):")
        lines.append("-" * 50)
        for gap in sorted(bucket_gaps, key=lambda g: (g.flag_name, g.bucket_name)):
            lines.append(
                f"  [{gap.flag_name}] bucket '{gap.bucket_name}'"
                f" → inherits {gap.resolved_value} from {gap.resolved_source}"
            )

    # Prompt-level gaps
    prompt_gaps = [g for g in report.gaps if g.level == "prompt"]
    if prompt_gaps:
        lines.append(f"\nPrompt-Level Gaps ({len(prompt_gaps)}):")
        lines.append("-" * 50)
        for gap in sorted(prompt_gaps, key=lambda g: (g.flag_name, g.bucket_name, g.prompt_name)):
            lines.append(
                f"  [{gap.flag_name}] prompt '{gap.bucket_name}/{gap.prompt_name}'"
                f" → inherits {gap.resolved_value} from {gap.resolved_source}"
            )

    if not report.gaps:
        lines.append("\nNo gaps found — all flags have explicit overrides at every scope.")

    return "\n".join(lines)


if __name__ == "__main__":
    from prompt_flags.config.loader import build_registry, load_config

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m tools.analyzers.gap_analysis <config.yaml>")

    config = load_config(sys.argv[1])
    registry = build_registry(config)
    report = gap_analysis(registry)
    raise SystemExit(format_gap_report(report))
