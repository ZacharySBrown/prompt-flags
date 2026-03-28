"""Analyze the impact of a flag across all prompts and buckets.

Reports which sections, prompts, and buckets are affected when a flag
is toggled, including the override tier at each scope.

Usage:
    uv run python -m tools.analyzers.flag_impact <config.yaml> <flag_name>
"""

from __future__ import annotations

import sys

from prompt_flags.core.dependency_graph import (
    EdgeKind,
    NodeKind,
    build_from_registry,
)
from prompt_flags.core.registry import PromptRegistry


def flag_impact(registry: PromptRegistry, flag_name: str) -> dict[str, list[dict[str, str]]]:
    """Analyze what a flag affects across the entire registry.

    Args:
        registry: The populated prompt registry.
        flag_name: The flag to analyze.

    Returns:
        A dict with keys "sections", "prompts", "buckets", each containing
        a list of dicts with "id", "scope", and "relationship" info.

    Raises:
        KeyError: If the flag is not defined in the registry.
    """
    if flag_name not in registry._flags:
        raise KeyError(f"Flag not defined: {flag_name!r}")

    graph = build_from_registry(registry)
    flag_node = graph.get_node(NodeKind.FLAG, flag_name)
    if flag_node is None:
        return {"sections": [], "prompts": [], "buckets": []}

    sections: list[dict[str, str]] = []
    prompts: list[dict[str, str]] = []
    buckets: list[dict[str, str]] = []

    for edge in graph.reverse_adjacency.get(flag_node, []):
        source = edge.source
        if source.kind == NodeKind.SECTION and edge.kind == EdgeKind.SECTION_USES_FLAG:
            sections.append(
                {
                    "id": source.id,
                    "scope": source.scope,
                    "relationship": "controlled_by",
                }
            )
        elif source.kind == NodeKind.PROMPT and edge.kind == EdgeKind.PROMPT_OVERRIDES_FLAG:
            prompts.append(
                {
                    "id": source.id,
                    "scope": source.scope,
                    "relationship": "overrides",
                }
            )
        elif source.kind == NodeKind.BUCKET and edge.kind == EdgeKind.BUCKET_OVERRIDES_FLAG:
            buckets.append(
                {
                    "id": source.id,
                    "scope": source.scope,
                    "relationship": "overrides",
                }
            )

    return {"sections": sections, "prompts": prompts, "buckets": buckets}


def format_impact_report(flag_name: str, impact: dict[str, list[dict[str, str]]]) -> str:
    """Format flag impact results as a human-readable report.

    Args:
        flag_name: The flag that was analyzed.
        impact: The impact data from flag_impact().

    Returns:
        A formatted string report.
    """
    lines: list[str] = [f"Flag Impact Report: {flag_name}", "=" * 50]

    sections = impact["sections"]
    if sections:
        lines.append(f"\nSections controlled by '{flag_name}' ({len(sections)}):")
        for s in sections:
            lines.append(f"  - {s['id']} (scope: {s['scope']})")
    else:
        lines.append(f"\nNo sections are controlled by '{flag_name}'.")

    prompts_list = impact["prompts"]
    if prompts_list:
        lines.append(f"\nPrompts that override '{flag_name}' ({len(prompts_list)}):")
        for p in prompts_list:
            lines.append(f"  - {p['id']} (bucket: {p['scope']})")

    buckets_list = impact["buckets"]
    if buckets_list:
        lines.append(f"\nBuckets that override '{flag_name}' ({len(buckets_list)}):")
        for b in buckets_list:
            lines.append(f"  - {b['id']}")

    total = len(sections) + len(prompts_list) + len(buckets_list)
    lines.append(f"\nTotal affected entities: {total}")
    return "\n".join(lines)


if __name__ == "__main__":
    from prompt_flags.config.loader import build_registry, load_config

    if len(sys.argv) != 3:
        raise SystemExit("Usage: python -m tools.analyzers.flag_impact <config.yaml> <flag_name>")

    config = load_config(sys.argv[1])
    registry = build_registry(config)
    impact = flag_impact(registry, sys.argv[2])
    raise SystemExit(format_impact_report(sys.argv[2], impact))
