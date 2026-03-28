"""Tests for the dependency graph builder and traversal."""

import pytest

from prompt_flags.core.dependency_graph import (
    DependencyGraph,
    Edge,
    EdgeKind,
    Node,
    NodeKind,
    build_from_registry,
)
from prompt_flags.core.models import (
    Bucket,
    Flag,
    OrderingConstraint,
    Prompt,
    Section,
)
from prompt_flags.core.registry import PromptRegistry


def _make_registry() -> PromptRegistry:
    """Build a test registry with 2 buckets, flags, and sections."""
    registry = PromptRegistry()
    registry.add_flag(Flag(name="cot", default=True, description="Chain of thought"))
    registry.add_flag(Flag(name="examples", default=False, description="Show examples"))

    section_identity = Section(id="identity", content="You are a helper.", priority=1)
    section_reasoning = Section(
        id="reasoning", content="Think step by step.", flag="cot", priority=2
    )
    section_examples = Section(
        id="examples", content="Here are examples.", flag="examples", priority=3
    )

    prompt_coding = Prompt(
        name="coding_guide",
        sections=[section_identity, section_reasoning, section_examples],
        flags={"cot": False},
    )
    prompt_review = Prompt(
        name="review_guide",
        sections=[section_identity, section_reasoning],
        flags={},
    )

    bucket_guides = Bucket(
        name="guides",
        prompts={"coding_guide": prompt_coding, "review_guide": prompt_review},
        flags={"examples": True},
    )
    bucket_tools = Bucket(
        name="tools",
        prompts={"coding_guide": Prompt(name="coding_guide", sections=[section_identity])},
        flags={},
    )

    registry.add_bucket(bucket_guides)
    registry.add_bucket(bucket_tools)
    registry.add_ordering_constraint(
        OrderingConstraint(before="identity", after="reasoning", source="test")
    )
    return registry


class TestDependencyGraphStructure:
    """Tests for graph node and edge creation."""

    def test_node_qualified_id_with_scope(self) -> None:
        node = Node(kind=NodeKind.SECTION, id="reasoning", scope="guides/coding")
        assert node.qualified_id == "guides/coding/reasoning"

    def test_node_qualified_id_without_scope(self) -> None:
        node = Node(kind=NodeKind.FLAG, id="cot")
        assert node.qualified_id == "cot"

    def test_empty_graph(self) -> None:
        graph = DependencyGraph()
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_add_node(self) -> None:
        graph = DependencyGraph()
        node = Node(kind=NodeKind.FLAG, id="cot")
        graph.add_node(node)
        assert (NodeKind.FLAG, "cot") in graph.nodes

    def test_add_edge_adds_both_nodes(self) -> None:
        graph = DependencyGraph()
        src = Node(kind=NodeKind.SECTION, id="s1", scope="b/p")
        tgt = Node(kind=NodeKind.FLAG, id="cot")
        graph.add_edge(Edge(source=src, target=tgt, kind=EdgeKind.SECTION_USES_FLAG))
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1

    def test_get_node(self) -> None:
        graph = DependencyGraph()
        node = Node(kind=NodeKind.FLAG, id="cot")
        graph.add_node(node)
        assert graph.get_node(NodeKind.FLAG, "cot") == node
        assert graph.get_node(NodeKind.FLAG, "nonexistent") is None

    def test_nodes_of_kind(self) -> None:
        graph = DependencyGraph()
        graph.add_node(Node(kind=NodeKind.FLAG, id="a"))
        graph.add_node(Node(kind=NodeKind.FLAG, id="b"))
        graph.add_node(Node(kind=NodeKind.BUCKET, id="x"))
        assert len(graph.nodes_of_kind(NodeKind.FLAG)) == 2
        assert len(graph.nodes_of_kind(NodeKind.BUCKET)) == 1


class TestBuildFromRegistry:
    """Tests for building graphs from a PromptRegistry."""

    def test_build_creates_flag_nodes(self) -> None:
        registry = _make_registry()
        graph = build_from_registry(registry)
        flag_nodes = graph.nodes_of_kind(NodeKind.FLAG)
        flag_names = {n.id for n in flag_nodes}
        assert flag_names == {"cot", "examples"}

    def test_build_creates_bucket_nodes(self) -> None:
        registry = _make_registry()
        graph = build_from_registry(registry)
        bucket_nodes = graph.nodes_of_kind(NodeKind.BUCKET)
        bucket_names = {n.id for n in bucket_nodes}
        assert bucket_names == {"guides", "tools"}

    def test_build_creates_prompt_nodes(self) -> None:
        registry = _make_registry()
        graph = build_from_registry(registry)
        prompt_nodes = graph.nodes_of_kind(NodeKind.PROMPT)
        assert len(prompt_nodes) == 3  # 2 in guides + 1 in tools

    def test_build_creates_section_nodes(self) -> None:
        registry = _make_registry()
        graph = build_from_registry(registry)
        section_nodes = graph.nodes_of_kind(NodeKind.SECTION)
        # coding_guide(3) + review_guide(2) in guides + coding_guide(1) in tools = 6
        assert len(section_nodes) == 6

    def test_section_uses_flag_edges(self) -> None:
        registry = _make_registry()
        graph = build_from_registry(registry)
        uses_flag_edges = [e for e in graph.edges if e.kind == EdgeKind.SECTION_USES_FLAG]
        # reasoning->cot (x2 in guides, x0 in tools) + examples->examples (x1 in guides)
        flag_targets = {e.target.id for e in uses_flag_edges}
        assert "cot" in flag_targets
        assert "examples" in flag_targets

    def test_bucket_overrides_flag_edges(self) -> None:
        registry = _make_registry()
        graph = build_from_registry(registry)
        override_edges = [e for e in graph.edges if e.kind == EdgeKind.BUCKET_OVERRIDES_FLAG]
        # guides overrides "examples"
        assert any(e.source.id == "guides" and e.target.id == "examples" for e in override_edges)

    def test_prompt_overrides_flag_edges(self) -> None:
        registry = _make_registry()
        graph = build_from_registry(registry)
        override_edges = [e for e in graph.edges if e.kind == EdgeKind.PROMPT_OVERRIDES_FLAG]
        # guides/coding_guide overrides "cot"
        assert any(e.source.id == "coding_guide" and e.target.id == "cot" for e in override_edges)

    def test_ordering_constraint_edges(self) -> None:
        registry = _make_registry()
        graph = build_from_registry(registry)
        ordering_edges = [e for e in graph.edges if e.kind == EdgeKind.SECTION_ORDERED_BEFORE]
        assert any(e.source.id == "identity" and e.target.id == "reasoning" for e in ordering_edges)

    def test_build_from_registry_type_error(self) -> None:
        with pytest.raises(TypeError, match="Expected PromptRegistry"):
            build_from_registry("not a registry")


class TestGraphTraversal:
    """Tests for dependency and dependent queries."""

    def test_dependents_of_flag(self) -> None:
        registry = _make_registry()
        graph = build_from_registry(registry)
        cot_node = graph.get_node(NodeKind.FLAG, "cot")
        assert cot_node is not None
        dependents = graph.dependents_of(cot_node)
        dependent_kinds = {n.kind for n in dependents}
        # Sections use it + prompt overrides it
        assert NodeKind.SECTION in dependent_kinds

    def test_dependencies_of_section(self) -> None:
        registry = _make_registry()
        graph = build_from_registry(registry)
        # Find a reasoning section
        reasoning_nodes = [n for n in graph.nodes_of_kind(NodeKind.SECTION) if n.id == "reasoning"]
        assert len(reasoning_nodes) > 0
        deps = graph.dependencies_of(reasoning_nodes[0])
        dep_ids = {n.id for n in deps}
        assert "cot" in dep_ids

    def test_transitive_dependents(self) -> None:
        registry = _make_registry()
        graph = build_from_registry(registry)
        cot_node = graph.get_node(NodeKind.FLAG, "cot")
        assert cot_node is not None
        transitive = graph.transitive_dependents(cot_node)
        # Should include sections, prompts that override it, and buckets above those
        assert len(transitive) > 0

    def test_transitive_dependencies(self) -> None:
        registry = _make_registry()
        graph = build_from_registry(registry)
        prompt_node = graph.get_node(NodeKind.PROMPT, "guides/coding_guide")
        assert prompt_node is not None
        transitive = graph.transitive_dependencies(prompt_node)
        # Should include sections, flags used
        dep_kinds = {n.kind for n in transitive}
        assert NodeKind.SECTION in dep_kinds
        assert NodeKind.FLAG in dep_kinds
