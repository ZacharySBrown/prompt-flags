"""Dependency graph builder for cross-prompt and cross-bucket analysis.

Builds a directed graph from a PromptRegistry, with nodes for flags, sections,
prompts, and buckets, and edges representing their relationships. Supports
queries for impact analysis, reachability, and dependency tracing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from prompt_flags.core.models import Bucket, Flag


class NodeKind(Enum):
    """The kind of entity a graph node represents."""

    FLAG = "flag"
    SECTION = "section"
    PROMPT = "prompt"
    BUCKET = "bucket"


class EdgeKind(Enum):
    """The kind of relationship a graph edge represents."""

    BUCKET_CONTAINS_PROMPT = "bucket_contains_prompt"
    PROMPT_CONTAINS_SECTION = "prompt_contains_section"
    SECTION_USES_FLAG = "section_uses_flag"
    BUCKET_OVERRIDES_FLAG = "bucket_overrides_flag"
    PROMPT_OVERRIDES_FLAG = "prompt_overrides_flag"
    SECTION_ORDERED_BEFORE = "section_ordered_before"
    SECTION_ORDERED_AFTER = "section_ordered_after"


@dataclass(frozen=True)
class Node:
    """A node in the dependency graph.

    Attributes:
        kind: The type of entity this node represents.
        id: Unique identifier (e.g., flag name, section id, prompt name).
        scope: Optional scope qualifier (e.g., bucket name for prompts/sections).
    """

    kind: NodeKind
    id: str
    scope: str = ""

    @property
    def qualified_id(self) -> str:
        """Return a fully qualified identifier for display."""
        if self.scope:
            return f"{self.scope}/{self.id}"
        return self.id


@dataclass(frozen=True)
class Edge:
    """A directed edge in the dependency graph.

    Attributes:
        source: The source node.
        target: The target node.
        kind: The type of relationship.
    """

    source: Node
    target: Node
    kind: EdgeKind


@dataclass
class DependencyGraph:
    """A directed graph of prompt-flags entities and their relationships.

    Built from a PromptRegistry to enable cross-prompt and cross-bucket
    dependency analysis.

    Attributes:
        nodes: All nodes in the graph, keyed by (kind, qualified_id).
        edges: All edges in the graph.
        adjacency: Forward adjacency list (node -> list of edges from that node).
        reverse_adjacency: Reverse adjacency list (node -> list of edges to that node).
    """

    nodes: dict[tuple[NodeKind, str], Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    adjacency: dict[Node, list[Edge]] = field(default_factory=dict)
    reverse_adjacency: dict[Node, list[Edge]] = field(default_factory=dict)

    def add_node(self, node: Node) -> None:
        """Add a node to the graph.

        Args:
            node: The node to add.
        """
        key = (node.kind, node.qualified_id)
        if key not in self.nodes:
            self.nodes[key] = node
            self.adjacency.setdefault(node, [])
            self.reverse_adjacency.setdefault(node, [])

    def add_edge(self, edge: Edge) -> None:
        """Add a directed edge to the graph.

        Args:
            edge: The edge to add.
        """
        self.add_node(edge.source)
        self.add_node(edge.target)
        self.edges.append(edge)
        self.adjacency[edge.source].append(edge)
        self.reverse_adjacency[edge.target].append(edge)

    def get_node(self, kind: NodeKind, qualified_id: str) -> Node | None:
        """Look up a node by kind and qualified ID.

        Args:
            kind: The node kind.
            qualified_id: The fully qualified identifier.

        Returns:
            The node if found, otherwise None.
        """
        return self.nodes.get((kind, qualified_id))

    def nodes_of_kind(self, kind: NodeKind) -> list[Node]:
        """Return all nodes of a given kind.

        Args:
            kind: The node kind to filter by.

        Returns:
            List of matching nodes.
        """
        return [n for n in self.nodes.values() if n.kind == kind]

    def dependents_of(self, node: Node) -> set[Node]:
        """Find all nodes that directly depend on the given node.

        Args:
            node: The node to find dependents for.

        Returns:
            Set of nodes that have edges pointing to this node.
        """
        return {e.source for e in self.reverse_adjacency.get(node, [])}

    def dependencies_of(self, node: Node) -> set[Node]:
        """Find all nodes that the given node directly depends on.

        Args:
            node: The node to find dependencies for.

        Returns:
            Set of nodes that this node has edges pointing to.
        """
        return {e.target for e in self.adjacency.get(node, [])}

    def transitive_dependents(self, node: Node) -> set[Node]:
        """Find all nodes transitively dependent on the given node.

        Args:
            node: The starting node.

        Returns:
            Set of all transitively dependent nodes (excluding the start).
        """
        visited: set[Node] = set()
        stack = [node]
        while stack:
            current = stack.pop()
            for dep in self.dependents_of(current):
                if dep not in visited:
                    visited.add(dep)
                    stack.append(dep)
        return visited

    def transitive_dependencies(self, node: Node) -> set[Node]:
        """Find all nodes transitively depended on by the given node.

        Args:
            node: The starting node.

        Returns:
            Set of all transitive dependencies (excluding the start).
        """
        visited: set[Node] = set()
        stack = [node]
        while stack:
            current = stack.pop()
            for dep in self.dependencies_of(current):
                if dep not in visited:
                    visited.add(dep)
                    stack.append(dep)
        return visited


def build_dependency_graph(
    buckets: dict[str, Bucket],
    flags: dict[str, Flag],
    constraints: list[object] | None = None,
) -> DependencyGraph:
    """Build a DependencyGraph from registry data.

    Args:
        buckets: All registered buckets, keyed by name.
        flags: All registered flags, keyed by name.
        constraints: Optional ordering constraints (OrderingConstraint objects).

    Returns:
        A populated DependencyGraph.
    """
    graph = DependencyGraph()

    # Add flag nodes
    for flag in flags.values():
        graph.add_node(Node(kind=NodeKind.FLAG, id=flag.name))

    # Add bucket, prompt, section nodes and edges
    for bucket in buckets.values():
        bucket_node = Node(kind=NodeKind.BUCKET, id=bucket.name)
        graph.add_node(bucket_node)

        # Bucket-level flag overrides
        for flag_name in bucket.flags:
            flag_node = graph.get_node(NodeKind.FLAG, flag_name)
            if flag_node:
                graph.add_edge(
                    Edge(
                        source=bucket_node,
                        target=flag_node,
                        kind=EdgeKind.BUCKET_OVERRIDES_FLAG,
                    )
                )

        for prompt in bucket.prompts.values():
            prompt_node = Node(kind=NodeKind.PROMPT, id=prompt.name, scope=bucket.name)
            graph.add_node(prompt_node)
            graph.add_edge(
                Edge(
                    source=bucket_node,
                    target=prompt_node,
                    kind=EdgeKind.BUCKET_CONTAINS_PROMPT,
                )
            )

            # Prompt-level flag overrides
            for flag_name in prompt.flags:
                flag_node = graph.get_node(NodeKind.FLAG, flag_name)
                if flag_node:
                    graph.add_edge(
                        Edge(
                            source=prompt_node,
                            target=flag_node,
                            kind=EdgeKind.PROMPT_OVERRIDES_FLAG,
                        )
                    )

            for section in prompt.sections:
                section_node = Node(
                    kind=NodeKind.SECTION,
                    id=section.id,
                    scope=f"{bucket.name}/{prompt.name}",
                )
                graph.add_node(section_node)
                graph.add_edge(
                    Edge(
                        source=prompt_node,
                        target=section_node,
                        kind=EdgeKind.PROMPT_CONTAINS_SECTION,
                    )
                )

                # Section -> flag dependency
                if section.flag:
                    flag_node = graph.get_node(NodeKind.FLAG, section.flag)
                    if flag_node:
                        graph.add_edge(
                            Edge(
                                source=section_node,
                                target=flag_node,
                                kind=EdgeKind.SECTION_USES_FLAG,
                            )
                        )

    # Add ordering constraint edges
    if constraints:
        from prompt_flags.core.models import OrderingConstraint

        for c in constraints:
            if isinstance(c, OrderingConstraint):
                # Find section nodes matching these IDs across all scopes
                before_nodes = [
                    n for n in graph.nodes_of_kind(NodeKind.SECTION) if n.id == c.before
                ]
                after_nodes = [n for n in graph.nodes_of_kind(NodeKind.SECTION) if n.id == c.after]
                for bn in before_nodes:
                    for an in after_nodes:
                        graph.add_edge(
                            Edge(
                                source=bn,
                                target=an,
                                kind=EdgeKind.SECTION_ORDERED_BEFORE,
                            )
                        )

    return graph


def build_from_registry(registry: object) -> DependencyGraph:
    """Build a DependencyGraph from a PromptRegistry instance.

    This is a convenience wrapper that extracts internal state from the registry.

    Args:
        registry: A PromptRegistry instance.

    Returns:
        A populated DependencyGraph.
    """
    from prompt_flags.core.registry import PromptRegistry

    if not isinstance(registry, PromptRegistry):
        raise TypeError(f"Expected PromptRegistry, got {type(registry).__name__}")

    return build_dependency_graph(
        buckets=registry._buckets,
        flags=registry._flags,
        constraints=registry._constraints,
    )
