"""Detect contradictory or suspicious flag override patterns.

Identifies cases where flag overrides at different scopes create
potentially confusing or contradictory behavior.

Usage:
    uv run python -m tools.analyzers.conflict_detector <config.yaml>
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

from prompt_flags.core.registry import PromptRegistry


@dataclass(frozen=True)
class FlagConflict:
    """A detected flag override conflict or anomaly.

    Attributes:
        flag_name: The flag involved.
        kind: The type of conflict detected.
        description: Human-readable description of the conflict.
        bucket_name: The bucket scope, if applicable.
        prompt_name: The prompt scope, if applicable.
    """

    flag_name: str
    kind: str
    description: str
    bucket_name: str = ""
    prompt_name: str = ""


@dataclass
class ConflictReport:
    """Results of conflict detection.

    Attributes:
        conflicts: All detected conflicts.
    """

    conflicts: list[FlagConflict] = field(default_factory=list)


def detect_conflicts(registry: PromptRegistry) -> ConflictReport:
    """Detect contradictory or suspicious flag override patterns.

    Checks for:
    - Prompt overrides that match the bucket override (redundant)
    - Bucket overrides that match the global default (redundant)
    - All prompts in a bucket overriding the same flag to the same value
      (should be a bucket-level override instead)
    - Flag overrides for undefined flags

    Args:
        registry: The populated prompt registry.

    Returns:
        A ConflictReport with all detected conflicts.
    """
    report = ConflictReport()
    flags = registry._flags
    buckets = registry._buckets

    for flag_name, flag_def in flags.items():
        for bucket in buckets.values():
            bucket_val = bucket.flags.get(flag_name)

            # Redundant bucket override matching global default
            if bucket_val is not None and bucket_val == flag_def.default:
                report.conflicts.append(
                    FlagConflict(
                        flag_name=flag_name,
                        kind="redundant_bucket_override",
                        description=(
                            f"Bucket '{bucket.name}' overrides '{flag_name}' to"
                            f" {bucket_val}, which matches the global default"
                        ),
                        bucket_name=bucket.name,
                    )
                )

            # Effective value at the bucket level
            effective_bucket = bucket_val if bucket_val is not None else flag_def.default

            # Check prompt-level overrides
            prompt_overrides: dict[bool, list[str]] = {}
            for prompt in bucket.prompts.values():
                prompt_val = prompt.flags.get(flag_name)

                if prompt_val is not None:
                    # Redundant prompt override matching effective bucket value
                    if prompt_val == effective_bucket:
                        report.conflicts.append(
                            FlagConflict(
                                flag_name=flag_name,
                                kind="redundant_prompt_override",
                                description=(
                                    f"Prompt '{prompt.name}' in bucket '{bucket.name}'"
                                    f" overrides '{flag_name}' to {prompt_val},"
                                    f" which matches the effective bucket value"
                                ),
                                bucket_name=bucket.name,
                                prompt_name=prompt.name,
                            )
                        )

                    prompt_overrides.setdefault(prompt_val, []).append(prompt.name)

            # All prompts override to the same value → should be bucket-level
            if len(bucket.prompts) > 1 and len(prompt_overrides) == 1:
                val, prompt_names = next(iter(prompt_overrides.items()))
                if len(prompt_names) == len(bucket.prompts):
                    report.conflicts.append(
                        FlagConflict(
                            flag_name=flag_name,
                            kind="should_be_bucket_override",
                            description=(
                                f"All {len(prompt_names)} prompts in bucket"
                                f" '{bucket.name}' override '{flag_name}' to {val}"
                                f" — consider a bucket-level override instead"
                            ),
                            bucket_name=bucket.name,
                        )
                    )

    # Check for overrides referencing undefined flags
    for bucket in buckets.values():
        for flag_name in bucket.flags:
            if flag_name not in flags:
                report.conflicts.append(
                    FlagConflict(
                        flag_name=flag_name,
                        kind="undefined_flag_override",
                        description=(
                            f"Bucket '{bucket.name}' overrides undefined flag '{flag_name}'"
                        ),
                        bucket_name=bucket.name,
                    )
                )
        for prompt in bucket.prompts.values():
            for flag_name in prompt.flags:
                if flag_name not in flags:
                    report.conflicts.append(
                        FlagConflict(
                            flag_name=flag_name,
                            kind="undefined_flag_override",
                            description=(
                                f"Prompt '{prompt.name}' in bucket '{bucket.name}'"
                                f" overrides undefined flag '{flag_name}'"
                            ),
                            bucket_name=bucket.name,
                            prompt_name=prompt.name,
                        )
                    )

    return report


def format_conflict_report(report: ConflictReport) -> str:
    """Format a ConflictReport as a human-readable string.

    Args:
        report: The conflict detection results.

    Returns:
        A formatted string report.
    """
    if not report.conflicts:
        return "No conflicts detected — flag overrides are clean."

    lines: list[str] = [
        f"Flag Conflict Report ({len(report.conflicts)} issues)",
        "=" * 50,
    ]

    by_kind: dict[str, list[FlagConflict]] = {}
    for c in report.conflicts:
        by_kind.setdefault(c.kind, []).append(c)

    kind_labels = {
        "redundant_bucket_override": "Redundant Bucket Overrides",
        "redundant_prompt_override": "Redundant Prompt Overrides",
        "should_be_bucket_override": "Should Be Bucket-Level Overrides",
        "undefined_flag_override": "Undefined Flag References",
    }

    for kind, conflicts in by_kind.items():
        label = kind_labels.get(kind, kind)
        lines.append(f"\n{label} ({len(conflicts)}):")
        lines.append("-" * 50)
        for c in conflicts:
            lines.append(f"  - {c.description}")

    return "\n".join(lines)


if __name__ == "__main__":
    from prompt_flags.config.loader import build_registry, load_config

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m tools.analyzers.conflict_detector <config.yaml>")

    config = load_config(sys.argv[1])
    registry = build_registry(config)
    report = detect_conflicts(registry)
    raise SystemExit(format_conflict_report(report))
