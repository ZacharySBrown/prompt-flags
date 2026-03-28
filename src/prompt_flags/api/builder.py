"""Fluent builder API for constructing prompts programmatically.

Provides a chainable builder that accumulates sections, flags, ordering
constraints, and bucket configuration, then produces a fully configured
PromptRegistry on build().
"""

from collections.abc import Mapping
from typing import Any

from prompt_flags.core.models import (
    Bucket,
    Flag,
    OrderingConstraint,
    Prompt,
    RenderedSection,
    RuntimeOverrides,
    Section,
)
from prompt_flags.core.registry import PromptRegistry
from prompt_flags.rendering.engine import PromptRenderer


class PromptBuilder:
    """Fluent builder for constructing prompts programmatically.

    Accumulates sections, flags, ordering constraints, and bucket
    configuration via a chainable API. Call build() to produce a
    PromptRegistry, or render() to build and render in one step.

    Example::

        result = (
            PromptBuilder("coding_guide")
            .in_bucket("guides")
            .section("identity", "You are a helper.", priority=1)
            .flag("cot", default=True)
            .render(context={"role": "assistant"})
        )
    """

    def __init__(self, name: str) -> None:
        """Initialize the builder with a prompt name.

        Args:
            name: The name for the prompt being built.
        """
        self._name = name
        self._bucket_name = "default"
        self._bucket_description = ""
        self._sections: list[Section] = []
        self._flags: list[Flag] = []
        self._constraints: list[OrderingConstraint] = []
        self._bucket_flag_overrides: dict[str, bool | None] = {}

    def in_bucket(
        self, bucket_name: str, description: str = ""
    ) -> "PromptBuilder":
        """Set the bucket for the prompt.

        Args:
            bucket_name: Name of the bucket to place the prompt in.
            description: Optional description for the bucket.

        Returns:
            Self for chaining.
        """
        self._bucket_name = bucket_name
        self._bucket_description = description
        return self

    def section(
        self,
        id: str,
        content: str,
        *,
        flag: str | None = None,
        priority: int = 100,
        before: list[str] | None = None,
        after: list[str] | None = None,
    ) -> "PromptBuilder":
        """Add a section to the prompt.

        Args:
            id: Unique identifier for the section.
            content: Inline text content for the section.
            flag: Optional feature flag controlling this section.
            priority: Ordering priority (lower = earlier). Default 100.
            before: Section IDs this section should appear before.
            after: Section IDs this section should appear after.

        Returns:
            Self for chaining.
        """
        self._sections.append(
            Section(
                id=id,
                content=content,
                flag=flag,
                priority=priority,
                before=before or [],
                after=after or [],
            )
        )
        return self

    def flag(
        self, name: str, *, default: bool, description: str = ""
    ) -> "PromptBuilder":
        """Define a feature flag.

        Args:
            name: Unique flag name.
            default: Default boolean value when no override is set.
            description: Optional description of what this flag controls.

        Returns:
            Self for chaining.
        """
        self._flags.append(
            Flag(name=name, default=default, description=description)
        )
        return self

    def order(self, before: str, *, after: str) -> "PromptBuilder":
        """Add an ordering constraint between two sections.

        Args:
            before: ID of the section that should come first.
            after: ID of the section that should come second.

        Returns:
            Self for chaining.
        """
        self._constraints.append(
            OrderingConstraint(before=before, after=after, source="builder")
        )
        return self

    def bucket_flag_override(
        self, flag_name: str, value: bool
    ) -> "PromptBuilder":
        """Set a bucket-level flag override.

        Args:
            flag_name: The flag to override at the bucket level.
            value: The override value.

        Returns:
            Self for chaining.
        """
        self._bucket_flag_overrides[flag_name] = value
        return self

    def build(self) -> PromptRegistry:
        """Build and return a configured PromptRegistry.

        Creates a PromptRegistry containing a single bucket with a single
        prompt, all registered flags, and ordering constraints.

        Returns:
            A fully configured PromptRegistry.
        """
        registry = PromptRegistry(strict=False)

        for f in self._flags:
            registry.add_flag(f)

        prompt = Prompt(name=self._name, sections=self._sections)
        bucket = Bucket(
            name=self._bucket_name,
            description=self._bucket_description,
            prompts={self._name: prompt},
            flags=self._bucket_flag_overrides,
        )
        registry.add_bucket(bucket)

        for constraint in self._constraints:
            registry.add_ordering_constraint(constraint)

        return registry

    def render(
        self,
        context: Mapping[str, Any] | None = None,
        flags: Mapping[str, bool] | None = None,
    ) -> str:
        """Build the registry and render the prompt in one step.

        Convenience method that calls build(), resolves flags, orders
        sections, renders them, and composes the result.

        Args:
            context: Template variables for Jinja2 rendering.
            flags: Runtime flag overrides.

        Returns:
            The rendered prompt string.
        """
        registry = self.build()
        renderer = PromptRenderer()
        ctx = dict(context) if context else {}

        runtime_overrides = (
            RuntimeOverrides(flags=dict(flags)) if flags else None
        )

        active_sections = registry.get_active_sections(
            self._bucket_name, self._name, runtime_overrides=runtime_overrides
        )

        flag_map = registry.resolve_flags(
            self._bucket_name,
            self._name,
            runtime_overrides=runtime_overrides,
        )

        rendered: list[RenderedSection] = renderer.render_sections(
            active_sections, ctx, flag_map.results
        )

        return renderer.compose(rendered)
