"""Standalone functional API for prompt rendering and composition.

Provides convenience functions that don't require builder or decorator
patterns. These functions operate directly on a PromptRegistry.
"""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from prompt_flags.config.loader import build_registry, load_config
from prompt_flags.core.models import RuntimeOverrides
from prompt_flags.core.registry import PromptRegistry
from prompt_flags.rendering.engine import PromptRenderer


def render_prompt(
    registry: PromptRegistry,
    bucket_name: str,
    prompt_name: str,
    context: Mapping[str, Any] | None = None,
    flags: Mapping[str, bool] | None = None,
) -> str:
    """Render a single prompt with resolved flags and ordered sections.

    Resolves flags for the given scope, filters and orders active
    sections, renders each section via Jinja2, and composes the
    final prompt string.

    Args:
        registry: The PromptRegistry containing the prompt.
        bucket_name: Name of the bucket containing the prompt.
        prompt_name: Name of the prompt to render.
        context: Optional template variables for Jinja2 rendering.
        flags: Optional runtime flag overrides.

    Returns:
        The rendered prompt string.
    """
    renderer = PromptRenderer()
    ctx = dict(context) if context else {}
    runtime_overrides = (
        RuntimeOverrides(flags=dict(flags)) if flags else None
    )

    active_sections = registry.get_active_sections(
        bucket_name, prompt_name, runtime_overrides=runtime_overrides
    )

    flag_map = registry.resolve_flags(
        bucket_name, prompt_name, runtime_overrides=runtime_overrides
    )

    rendered = renderer.render_sections(active_sections, ctx, flag_map.results)
    return renderer.compose(rendered)


def compose(
    registry: PromptRegistry,
    buckets: list[str],
    context: Mapping[str, Any] | None = None,
    flags: Mapping[str, bool] | None = None,
) -> str:
    """Compose prompts across multiple buckets into a single string.

    For each bucket, renders all prompts and joins the results.
    Buckets are processed in the order given.

    Args:
        registry: The PromptRegistry containing the buckets.
        buckets: Ordered list of bucket names to compose.
        context: Optional template variables for Jinja2 rendering.
        flags: Optional runtime flag overrides.

    Returns:
        The composed prompt string with bucket outputs joined by
        double newlines.
    """
    if not buckets:
        return ""

    parts: list[str] = []
    for bucket_name in buckets:
        bucket = registry.get_bucket(bucket_name)
        for prompt_name in bucket.prompts:
            rendered = render_prompt(
                registry, bucket_name, prompt_name,
                context=context, flags=flags,
            )
            if rendered:
                parts.append(rendered)

    return "\n\n".join(parts)


def from_yaml(path: str | Path) -> PromptRegistry:
    """Load a YAML config and return a populated PromptRegistry.

    Convenience wrapper around load_config + build_registry.

    Args:
        path: Path to the YAML config file.

    Returns:
        A PromptRegistry populated from the YAML configuration.

    Raises:
        FileNotFoundError: If the config file does not exist.
        pydantic.ValidationError: If the YAML content fails validation.
    """
    config = load_config(path)
    return build_registry(config)
