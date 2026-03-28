"""Trace the full dependency chain for a prompt or section.

Shows all flags, sections, and ordering relationships that a prompt
depends on, transitively.

Usage:
    uv run python -m tools.analyzers.dependency_trace <config.yaml> <bucket> <prompt>
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field

from prompt_flags.core.dependency_graph import (
    EdgeKind,
    NodeKind,
    build_from_registry,
)
from prompt_flags.core.registry import PromptRegistry


@dataclass
class DependencyTrace:
    """Full dependency trace for a prompt.

    Attributes:
        prompt_id: The prompt being traced.
        bucket_id: The bucket containing the prompt.
        sections: Sections contained in the prompt.
        flags_used: Flags referenced by sections.
        flags_overridden: Flags overridden at the prompt level.
        bucket_flag_overrides: Flags overridden at the bucket level.
        ordering_deps: Section ordering dependencies.
    """

    prompt_id: str
    bucket_id: str
    sections: list[dict[str, str]] = field(default_factory=list)
    flags_used: list[str] = field(default_factory=list)
    flags_overridden: list[str] = field(default_factory=list)
    bucket_flag_overrides: list[str] = field(default_factory=list)
    ordering_deps: list[dict[str, str]] = field(default_factory=list)


def trace_prompt_dependencies(
    registry: PromptRegistry, bucket_name: str, prompt_name: str
) -> DependencyTrace:
    """Trace all dependencies for a specific prompt.

    Args:
        registry: The populated prompt registry.
        bucket_name: The bucket containing the prompt.
        prompt_name: The prompt to trace.

    Returns:
        A DependencyTrace with all dependency information.

    Raises:
        KeyError: If the bucket or prompt is not found.
    """
    # Validate existence
    registry.get_prompt(bucket_name, prompt_name)

    graph = build_from_registry(registry)
    prompt_node = graph.get_node(NodeKind.PROMPT, f"{bucket_name}/{prompt_name}")
    if prompt_node is None:
        raise KeyError(f"Prompt node not found: {bucket_name}/{prompt_name}")

    trace = DependencyTrace(prompt_id=prompt_name, bucket_id=bucket_name)

    # Walk prompt's direct edges
    for edge in graph.adjacency.get(prompt_node, []):
        if edge.kind == EdgeKind.PROMPT_CONTAINS_SECTION:
            section_node = edge.target
            flag_info = ""
            for se in graph.adjacency.get(section_node, []):
                if se.kind == EdgeKind.SECTION_USES_FLAG:
                    flag_info = se.target.id
                    if flag_info not in trace.flags_used:
                        trace.flags_used.append(flag_info)
            trace.sections.append(
                {
                    "id": section_node.id,
                    "flag": flag_info,
                }
            )
        elif edge.kind == EdgeKind.PROMPT_OVERRIDES_FLAG:
            trace.flags_overridden.append(edge.target.id)

    # Check bucket-level overrides
    bucket_node = graph.get_node(NodeKind.BUCKET, bucket_name)
    if bucket_node:
        for edge in graph.adjacency.get(bucket_node, []):
            if edge.kind == EdgeKind.BUCKET_OVERRIDES_FLAG:
                trace.bucket_flag_overrides.append(edge.target.id)

    # Find ordering dependencies among this prompt's sections
    section_ids = {s["id"] for s in trace.sections}
    for edge in graph.edges:
        is_ordering = edge.kind in (EdgeKind.SECTION_ORDERED_BEFORE, EdgeKind.SECTION_ORDERED_AFTER)
        if is_ordering and (edge.source.id in section_ids or edge.target.id in section_ids):
            trace.ordering_deps.append(
                {
                    "from": edge.source.id,
                    "to": edge.target.id,
                    "kind": edge.kind.value,
                }
            )

    trace.flags_used.sort()
    trace.flags_overridden.sort()
    trace.bucket_flag_overrides.sort()
    return trace


def format_trace_report(trace: DependencyTrace) -> str:
    """Format a DependencyTrace as a human-readable report.

    Args:
        trace: The dependency trace results.

    Returns:
        A formatted string report.
    """
    lines: list[str] = [
        f"Dependency Trace: {trace.bucket_id}/{trace.prompt_id}",
        "=" * 50,
    ]

    lines.append(f"\nSections ({len(trace.sections)}):")
    for s in trace.sections:
        flag_note = f" [flag: {s['flag']}]" if s["flag"] else " [always on]"
        lines.append(f"  - {s['id']}{flag_note}")

    lines.append(f"\nFlags used by sections ({len(trace.flags_used)}):")
    for f in trace.flags_used:
        lines.append(f"  - {f}")
    if not trace.flags_used:
        lines.append("  (none)")

    lines.append(f"\nPrompt-level flag overrides ({len(trace.flags_overridden)}):")
    for f in trace.flags_overridden:
        lines.append(f"  - {f}")
    if not trace.flags_overridden:
        lines.append("  (none)")

    lines.append(f"\nBucket-level flag overrides ({len(trace.bucket_flag_overrides)}):")
    for f in trace.bucket_flag_overrides:
        lines.append(f"  - {f}")
    if not trace.bucket_flag_overrides:
        lines.append("  (none)")

    if trace.ordering_deps:
        lines.append(f"\nOrdering constraints ({len(trace.ordering_deps)}):")
        for dep in trace.ordering_deps:
            lines.append(f"  - {dep['from']} → {dep['to']} ({dep['kind']})")

    return "\n".join(lines)


if __name__ == "__main__":
    from prompt_flags.config.loader import build_registry, load_config

    if len(sys.argv) != 4:
        raise SystemExit(
            "Usage: python -m tools.analyzers.dependency_trace <config.yaml> <bucket> <prompt>"
        )

    config = load_config(sys.argv[1])
    registry = build_registry(config)
    trace = trace_prompt_dependencies(registry, sys.argv[2], sys.argv[3])
    raise SystemExit(format_trace_report(trace))
