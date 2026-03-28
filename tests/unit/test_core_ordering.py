"""Tests for section ordering."""

import pytest

from prompt_flags.core.models import OrderingConstraint, Section
from prompt_flags.core.ordering import OrderingCycleError, order_sections


class TestOrderSections:
    """Tests for the order_sections function."""

    def test_empty_sections(self) -> None:
        result = order_sections([], [])
        assert result == []

    def test_single_section(self) -> None:
        sections = [Section(id="a", content="A")]
        result = order_sections(sections, [])
        assert len(result) == 1
        assert result[0].id == "a"

    def test_priority_ordering(self) -> None:
        sections = [
            Section(id="c", content="C", priority=30),
            Section(id="a", content="A", priority=10),
            Section(id="b", content="B", priority=20),
        ]
        result = order_sections(sections, [])
        assert [s.id for s in result] == ["a", "b", "c"]

    def test_constraint_ordering(self) -> None:
        sections = [
            Section(id="a", content="A", priority=100),
            Section(id="b", content="B", priority=100),
        ]
        constraints = [OrderingConstraint(before="b", after="a")]
        result = order_sections(sections, constraints)
        assert [s.id for s in result] == ["b", "a"]

    def test_constraint_overrides_priority(self) -> None:
        """Constraints should take precedence over priority values."""
        sections = [
            Section(id="a", content="A", priority=1),
            Section(id="b", content="B", priority=100),
        ]
        # b must come before a, even though a has lower priority
        constraints = [OrderingConstraint(before="b", after="a")]
        result = order_sections(sections, constraints)
        assert [s.id for s in result] == ["b", "a"]

    def test_section_before_declaration(self) -> None:
        """Test the before field on sections."""
        sections = [
            Section(id="a", content="A", priority=100),
            Section(id="b", content="B", priority=100, before=["a"]),
        ]
        result = order_sections(sections, [])
        # b declares it should come before a
        assert [s.id for s in result] == ["b", "a"]

    def test_section_after_declaration(self) -> None:
        """Test the after field on sections."""
        sections = [
            Section(id="a", content="A", priority=100, after=["b"]),
            Section(id="b", content="B", priority=100),
        ]
        result = order_sections(sections, [])
        # a declares it should come after b
        assert [s.id for s in result] == ["b", "a"]

    def test_cycle_detection(self) -> None:
        sections = [
            Section(id="a", content="A"),
            Section(id="b", content="B"),
        ]
        constraints = [
            OrderingConstraint(before="a", after="b"),
            OrderingConstraint(before="b", after="a"),
        ]
        with pytest.raises(OrderingCycleError):
            order_sections(sections, constraints)

    def test_constraint_referencing_missing_section_ignored(self) -> None:
        """Constraints referencing non-existent sections are silently skipped."""
        sections = [Section(id="a", content="A")]
        constraints = [OrderingConstraint(before="missing", after="a")]
        result = order_sections(sections, constraints)
        assert [s.id for s in result] == ["a"]

    def test_complex_ordering(self) -> None:
        """Test a multi-node graph with mixed constraints and priorities."""
        sections = [
            Section(id="identity", content="I", priority=1),
            Section(id="task", content="T", priority=50),
            Section(id="constraints", content="C", priority=50),
            Section(id="output", content="O", priority=99),
        ]
        constraints = [
            OrderingConstraint(before="identity", after="task"),
            OrderingConstraint(before="task", after="constraints"),
            OrderingConstraint(before="constraints", after="output"),
        ]
        result = order_sections(sections, constraints)
        assert [s.id for s in result] == ["identity", "task", "constraints", "output"]

    def test_priority_tiebreaking_within_level(self) -> None:
        """Sections with no constraints between them use priority for ordering."""
        sections = [
            Section(id="z", content="Z", priority=30),
            Section(id="y", content="Y", priority=10),
            Section(id="x", content="X", priority=20),
            Section(id="root", content="R", priority=1),
        ]
        # root must come first, then x, y, z have no constraints between them
        constraints = [
            OrderingConstraint(before="root", after="x"),
            OrderingConstraint(before="root", after="y"),
            OrderingConstraint(before="root", after="z"),
        ]
        result = order_sections(sections, constraints)
        assert result[0].id == "root"
        # y(10), x(20), z(30) ordered by priority
        assert [s.id for s in result[1:]] == ["y", "x", "z"]
