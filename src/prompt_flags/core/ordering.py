"""Section ordering via topological sort with priority tiebreaking.

Uses graphlib.TopologicalSorter to resolve ordering constraints between
sections. Within each topological level, sections are sorted by priority
(lower values come first).
"""

from graphlib import CycleError, TopologicalSorter

from prompt_flags.core.models import OrderingConstraint, Section


class OrderingCycleError(Exception):
    """Raised when section ordering constraints form a cycle.

    Attributes:
        cycle_detail: Description of the cycle from graphlib.
    """

    def __init__(self, cycle_detail: str) -> None:
        """Initialize with cycle detail information.

        Args:
            cycle_detail: A description of the cycle detected.
        """
        self.cycle_detail = cycle_detail
        super().__init__(f"Cycle detected in section ordering: {cycle_detail}")


def order_sections(
    sections: list[Section],
    constraints: list[OrderingConstraint],
) -> list[Section]:
    """Order sections using topological sort with priority tiebreaking.

    Builds a dependency graph from explicit constraints and per-section
    before/after declarations, then sorts topologically. Within each
    topological level, sections are ordered by priority (lower = earlier).

    Constraints referencing sections not in the input list are silently skipped.

    Args:
        sections: The sections to order.
        constraints: Explicit ordering constraints between section IDs.

    Returns:
        The sections in resolved order.

    Raises:
        OrderingCycleError: If the constraints form a cycle.
    """
    if not sections:
        return []

    sections_by_id: dict[str, Section] = {s.id: s for s in sections}
    active_ids = set(sections_by_id.keys())

    # Build dependency graph: section_id -> set of predecessor IDs
    graph: dict[str, set[str]] = {sid: set() for sid in active_ids}

    # Add explicit constraints
    for constraint in constraints:
        if constraint.before in active_ids and constraint.after in active_ids:
            graph[constraint.after].add(constraint.before)

    # Add per-section before/after declarations
    for section in sections:
        for before_id in section.before:
            if before_id in active_ids:
                # This section should come before before_id
                graph[before_id].add(section.id)
        for after_id in section.after:
            if after_id in active_ids:
                # This section should come after after_id
                graph[section.id].add(after_id)

    # Run topological sort with priority tiebreaking
    sorter = TopologicalSorter(graph)
    try:
        sorter.prepare()
    except CycleError as e:
        raise OrderingCycleError(str(e)) from e

    result: list[str] = []
    while sorter.is_active():
        ready = list(sorter.get_ready())
        # Tiebreak by priority within each topological level
        ready.sort(key=lambda sid: sections_by_id[sid].priority)
        result.extend(ready)
        sorter.done(*ready)

    return [sections_by_id[sid] for sid in result]
