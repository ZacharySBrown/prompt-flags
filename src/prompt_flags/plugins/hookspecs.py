"""Pluggy hook specifications for the prompt_flags plugin system.

Defines the lifecycle hooks that plugins can implement to intercept
and modify template loading, rendering, and flag resolution.

Requires the ``plugins`` extra: ``pip install prompt_flags[plugins]``.
"""

from __future__ import annotations

from typing import Any

try:
    import pluggy
except ImportError as exc:
    msg = (
        "pluggy is required for the plugin hook system. "
        "Install it with: pip install prompt_flags[plugins]"
    )
    raise ImportError(msg) from exc

hookspec = pluggy.HookspecMarker("prompt_flags")
hookimpl = pluggy.HookimplMarker("prompt_flags")


class PromptFlagsHookSpec:
    """Hook specifications for the prompt_flags plugin system.

    Each method defines a hook that plugins can implement via the
    ``@hookimpl`` decorator. Hooks are called by the PluginManager
    at the appropriate point in the template lifecycle.
    """

    @hookspec
    def pre_load(self, template_name: str, bucket: str | None) -> str | None:
        """Called before template loading.

        Args:
            template_name: The name of the template being loaded.
            bucket: Optional bucket/namespace for the template.

        Returns:
            A modified template name, or None to proceed with the original.
        """

    @hookspec
    def post_load(self, template_name: str, raw_content: str) -> str:  # noqa: D102
        """Called after loading raw template content.

        Args:
            template_name: The name of the template that was loaded.
            raw_content: The raw template content.

        Returns:
            The possibly modified content.
        """
        ...  # pragma: no cover

    @hookspec
    def pre_render(
        self,
        template: str,
        context: dict[str, Any],
        flags: dict[str, bool],
    ) -> tuple[str, dict[str, Any]] | None:
        """Called before rendering a template.

        Args:
            template: The template string to render.
            context: The context variables for rendering.
            flags: The resolved flag values.

        Returns:
            A tuple of (modified_template, modified_context), or None.
        """

    @hookspec
    def post_render(self, rendered_text: str, metadata: dict[str, Any]) -> str:
        """Called after rendering a template.

        Args:
            rendered_text: The rendered text output.
            metadata: Metadata about the rendering (e.g., token counts).

        Returns:
            The possibly modified rendered text.
        """
        ...  # pragma: no cover

    @hookspec
    def on_flag_resolved(
        self,
        flag_name: str,
        value: bool,
        source: str,
        scope: dict[str, Any],
    ) -> None:
        """Called after each flag resolution for observability.

        Args:
            flag_name: The name of the flag that was resolved.
            value: The resolved boolean value.
            source: The resolution tier that provided the value.
            scope: The evaluation scope/context.
        """
