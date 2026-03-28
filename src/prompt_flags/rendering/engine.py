"""Jinja2 rendering engine with feature flag integration.

Sets up a Jinja2 Environment configured for prompt text rendering,
registers global functions for feature flag checks and environment
variable access, and provides the rendering pipeline.
"""

import os
from typing import Any

from jinja2 import Environment, StrictUndefined
from jinja2.ext import Extension

from prompt_flags.core.models import FlagResult, RenderedSection, Section
from prompt_flags.rendering.filters import collapse_blank_lines, indent_block, strip_empty_lines


class PromptRenderer:
    """Renders prompt templates with feature flag integration.

    Configures a Jinja2 Environment for prompt text (not HTML), registers
    global functions for feature flag checking and env var access, and
    provides methods for template rendering, section rendering, and
    composition.

    Attributes:
        env: The Jinja2 Environment used for rendering.
    """

    def __init__(
        self,
        template_dirs: dict[str, str] | None = None,
        extensions: list[type[Extension]] | None = None,
    ) -> None:
        """Set up Jinja2 environment.

        Args:
            template_dirs: Mapping of bucket names to template directories.
            extensions: Optional list of Jinja2 Extension classes to load.
        """
        self._flags: dict[str, FlagResult] = {}

        ext_list = [ext.__module__ + "." + ext.__qualname__ for ext in (extensions or [])]

        self.env = Environment(
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
            undefined=StrictUndefined,
            extensions=ext_list,
        )

        # Register global functions
        self.env.globals["feature_enabled"] = self._feature_enabled  # pyright: ignore[reportArgumentType]
        self.env.globals["env"] = self._env_var  # pyright: ignore[reportArgumentType]

        # Register custom filters
        self.env.filters["strip_empty_lines"] = strip_empty_lines
        self.env.filters["indent_block"] = indent_block

    def _feature_enabled(self, flag_name: str) -> bool:
        """Check if a feature flag is enabled in the current rendering context.

        Args:
            flag_name: The name of the feature flag to check.

        Returns:
            True if the flag is enabled, False if disabled or not found.
        """
        flag_result = self._flags.get(flag_name)
        if flag_result is None:
            return False
        return flag_result.value

    @staticmethod
    def _env_var(var_name: str, default: str = "") -> str:
        """Read an environment variable with a fallback default.

        Args:
            var_name: The environment variable name.
            default: Fallback value if the variable is not set.

        Returns:
            The environment variable value, or the default.
        """
        return os.environ.get(var_name, default)

    def render_template(
        self,
        template_source: str,
        context: dict[str, Any],
        flags: dict[str, FlagResult],
    ) -> str:
        """Render a template string with context and resolved flags.

        Args:
            template_source: The Jinja2 template string.
            context: Template variables for rendering.
            flags: Resolved feature flags for conditional sections.

        Returns:
            The rendered template string with whitespace normalized.
        """
        self._flags = flags
        try:
            template = self.env.from_string(template_source)
            rendered = template.render(**context)
            return collapse_blank_lines(rendered)
        finally:
            self._flags = {}

    def render_sections(
        self,
        sections: list[Section],
        context: dict[str, Any],
        flags: dict[str, FlagResult],
    ) -> list[RenderedSection]:
        """Render a list of sections, skipping disabled ones.

        Sections whose associated flag is disabled are excluded from the
        output. Sections without a flag are always included.

        Args:
            sections: The sections to render.
            context: Template variables for rendering.
            flags: Resolved feature flags.

        Returns:
            List of rendered sections (disabled sections omitted).
        """
        rendered: list[RenderedSection] = []
        for section in sections:
            # Check if this section's flag is enabled
            if section.flag is not None:
                flag_result = flags.get(section.flag)
                if flag_result is None or not flag_result.value:
                    continue

            # Render the section content
            content = section.content or ""
            rendered_content = self.render_template(content, context, flags)

            rendered.append(
                RenderedSection(
                    id=section.id,
                    content=rendered_content,
                    flag=section.flag,
                )
            )
        return rendered

    def compose(self, rendered_sections: list[RenderedSection]) -> str:
        """Join rendered sections into a final prompt string.

        Args:
            rendered_sections: The rendered sections to compose.

        Returns:
            The final prompt string with sections joined by double newlines.
        """
        if not rendered_sections:
            return ""
        if len(rendered_sections) == 1:
            return rendered_sections[0].content
        return "\n\n".join(section.content for section in rendered_sections)
