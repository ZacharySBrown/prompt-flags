"""Plugin manager for discovery, registration, and hook execution.

Wraps pluggy's PluginManager with a typed API for the prompt_flags
hook lifecycle. Handles plugin discovery via entry points and
graceful degradation when pluggy is not installed.

Requires the ``plugins`` extra: ``pip install prompt_flags[plugins]``.
"""

from __future__ import annotations

import importlib.metadata
from typing import Any

try:
    import pluggy
except ImportError as exc:
    msg = (
        "pluggy is required for the plugin manager. "
        "Install it with: pip install prompt_flags[plugins]"
    )
    raise ImportError(msg) from exc

from prompt_flags.plugins.hookspecs import PromptFlagsHookSpec

_ENTRY_POINT_GROUP = "prompt_flags.plugins"


class PluginManager:
    """Manages plugin discovery, registration, and hook execution.

    Creates a pluggy PluginManager, registers the PromptFlagsHookSpec,
    and provides typed convenience methods for calling each hook.
    """

    def __init__(self) -> None:
        """Initialize with a pluggy PluginManager and register hook specs."""
        self._pm = pluggy.PluginManager("prompt_flags")
        self._pm.add_hookspecs(PromptFlagsHookSpec)

    def register(self, plugin: object, name: str | None = None) -> None:
        """Register a plugin instance.

        Args:
            plugin: The plugin object implementing one or more ``@hookimpl`` methods.
            name: Optional name for the plugin registration.
        """
        self._pm.register(plugin, name=name)

    def discover_entry_points(self) -> list[str]:
        """Discover and load plugins from the entry_points group.

        Scans ``prompt_flags.plugins`` entry points, loads each one,
        instantiates it, and registers it.

        Returns:
            List of discovered plugin names.
        """
        discovered: list[str] = []
        eps = importlib.metadata.entry_points()
        group_eps = eps.select(group=_ENTRY_POINT_GROUP)
        for ep in group_eps:
            plugin_cls = ep.load()
            plugin_instance = plugin_cls()
            self._pm.register(plugin_instance, name=ep.name)
            discovered.append(ep.name)
        return discovered

    def call_pre_load(
        self, template_name: str, bucket: str | None = None
    ) -> str:
        """Call pre_load hooks, returning possibly modified template name.

        Args:
            template_name: The original template name.
            bucket: Optional bucket/namespace.

        Returns:
            The final template name after all hooks have run.
        """
        results: list[str | None] = self._pm.hook.pre_load(
            template_name=template_name, bucket=bucket
        )
        # Results are returned in LIFO order; take the first non-None result
        for result in results:
            if result is not None:
                return result
        return template_name

    def call_post_load(self, template_name: str, raw_content: str) -> str:
        """Call post_load hooks, returning possibly modified content.

        Args:
            template_name: The template name that was loaded.
            raw_content: The raw template content.

        Returns:
            The final content after all hooks have run.
        """
        results: list[str] = self._pm.hook.post_load(
            template_name=template_name, raw_content=raw_content
        )
        # Chain: last result is from the first-registered plugin (LIFO)
        if results:
            return results[-1]
        return raw_content

    def call_pre_render(
        self,
        template: str,
        context: dict[str, Any],
        flags: dict[str, bool],
    ) -> tuple[str, dict[str, Any]]:
        """Call pre_render hooks, returning possibly modified template and context.

        Args:
            template: The template string.
            context: The context variables.
            flags: The resolved flag values.

        Returns:
            Tuple of (template, context) after all hooks have run.
        """
        results: list[tuple[str, dict[str, Any]] | None] = (
            self._pm.hook.pre_render(
                template=template, context=context, flags=flags
            )
        )
        for result in results:
            if result is not None:
                return result
        return (template, context)

    def call_post_render(
        self, rendered_text: str, metadata: dict[str, Any] | None = None
    ) -> str:
        """Call post_render hooks, returning possibly modified text.

        Args:
            rendered_text: The rendered text output.
            metadata: Optional metadata about the rendering.

        Returns:
            The final rendered text after all hooks have run.
        """
        resolved_metadata: dict[str, Any] = metadata if metadata is not None else {}
        results: list[str] = self._pm.hook.post_render(
            rendered_text=rendered_text, metadata=resolved_metadata
        )
        if results:
            return results[-1]
        return rendered_text

    def call_on_flag_resolved(
        self,
        flag_name: str,
        value: bool,
        source: str,
        scope: dict[str, Any] | None = None,
    ) -> None:
        """Call on_flag_resolved hooks for observability.

        Args:
            flag_name: The flag name that was resolved.
            value: The resolved boolean value.
            source: The resolution tier.
            scope: Optional evaluation scope/context.
        """
        resolved_scope: dict[str, Any] = scope if scope is not None else {}
        self._pm.hook.on_flag_resolved(
            flag_name=flag_name, value=value, source=source, scope=resolved_scope
        )
