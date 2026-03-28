"""Plugin Protocol interfaces for zero-coupling integration.

Defines structural typing protocols that external systems can implement
without depending on prompt_flags internals. All protocols are
runtime_checkable for isinstance() support.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from prompt_flags.core.models import RenderedSection


@runtime_checkable
class PromptLoader(Protocol):
    """Loads raw template content from a storage backend.

    Implementations may read from the filesystem, a database, S3, or any
    other storage system. The ``bucket`` parameter provides optional
    namespace scoping.
    """

    def load(self, name: str, bucket: str | None = None) -> str:
        """Load a template by name.

        Args:
            name: The template identifier.
            bucket: Optional bucket/namespace to scope the lookup.

        Returns:
            The raw template string.
        """
        ...

    def list_templates(self, bucket: str | None = None) -> list[str]:
        """List available template names.

        Args:
            bucket: Optional bucket/namespace to filter by.

        Returns:
            List of template identifiers.
        """
        ...


@runtime_checkable
class PromptRenderer(Protocol):
    """Renders a template string with context variables.

    Implementations may use Jinja2, string.format, Mustache, or any
    other templating engine.
    """

    def render(self, template: str, context: dict[str, Any]) -> str:
        """Render a template with the given context.

        Args:
            template: The raw template string.
            context: Variable mappings for interpolation.

        Returns:
            The rendered string.
        """
        ...


@runtime_checkable
class PromptComposer(Protocol):
    """Assembles multiple rendered sections into a final prompt string.

    Implementations control how sections are joined, separated, or
    formatted into the complete prompt output.
    """

    def compose(self, sections: list[RenderedSection]) -> str:
        """Compose rendered sections into a single prompt.

        Args:
            sections: Ordered list of rendered sections.

        Returns:
            The assembled prompt string.
        """
        ...


@runtime_checkable
class FlagSource(Protocol):
    """Provides flag state from an external system.

    Implementations may integrate with LaunchDarkly, Unleash, Flipt,
    environment variables, or any other feature-flag provider.
    """

    def get_flag(self, name: str, context: dict[str, Any]) -> bool | None:
        """Get a single flag value.

        Args:
            name: The flag identifier.
            context: Evaluation context (user, environment, etc.).

        Returns:
            The flag value, or None if the flag is unknown.
        """
        ...

    def get_all_flags(self, context: dict[str, Any]) -> dict[str, bool]:
        """Get all known flag values.

        Args:
            context: Evaluation context (user, environment, etc.).

        Returns:
            Mapping of flag names to their boolean values.
        """
        ...
