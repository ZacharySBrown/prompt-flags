"""Detect flags that are defined but never referenced by any section.

Usage:
    uv run python -m tools.analyzers.unused_flags <config.yaml>
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from prompt_flags.core.dependency_graph import EdgeKind, NodeKind, build_from_registry
from prompt_flags.core.registry import PromptRegistry


@dataclass(frozen=True)
class UnusedFlag:
    """A flag that is defined but not referenced by any section.

    Attributes:
        name: The flag name.
        default: The flag's default value.
        has_overrides: Whether any bucket/prompt overrides exist for this flag.
    """

    name: str
    default: bool
    has_overrides: bool


def find_unused_flags(registry: PromptRegistry) -> list[UnusedFlag]:
    """Find flags that no section references.

    A flag is "unused" if no section has it in its `flag` field, even if
    buckets or prompts declare overrides for it.

    Args:
        registry: The populated prompt registry.

    Returns:
        List of UnusedFlag entries.
    """
    graph = build_from_registry(registry)
    unused: list[UnusedFlag] = []

    for flag_node in graph.nodes_of_kind(NodeKind.FLAG):
        reverse_edges = graph.reverse_adjacency.get(flag_node, [])
        has_section_ref = any(e.kind == EdgeKind.SECTION_USES_FLAG for e in reverse_edges)
        if not has_section_ref:
            has_overrides = any(
                e.kind in (EdgeKind.BUCKET_OVERRIDES_FLAG, EdgeKind.PROMPT_OVERRIDES_FLAG)
                for e in reverse_edges
            )
            flag_def = registry._flags[flag_node.id]
            unused.append(
                UnusedFlag(
                    name=flag_node.id,
                    default=flag_def.default,
                    has_overrides=has_overrides,
                )
            )

    return sorted(unused, key=lambda f: f.name)


def format_unused_report(unused: list[UnusedFlag]) -> str:
    """Format unused flags as a human-readable report.

    Args:
        unused: List of unused flags.

    Returns:
        A formatted string report.
    """
    if not unused:
        return "No unused flags found — all defined flags are referenced by at least one section."

    lines: list[str] = [
        f"Unused Flags ({len(unused)})",
        "=" * 50,
    ]
    for f in unused:
        override_note = " (has overrides)" if f.has_overrides else ""
        lines.append(f"  - {f.name} (default={f.default}){override_note}")

    lines.append("\nThese flags are defined but no section references them via the 'flag' field.")
    return "\n".join(lines)


if __name__ == "__main__":
    from prompt_flags.config.loader import build_registry, load_config

    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m tools.analyzers.unused_flags <config.yaml>")

    config = load_config(sys.argv[1])
    registry = build_registry(config)
    unused = find_unused_flags(registry)
    raise SystemExit(format_unused_report(unused))
