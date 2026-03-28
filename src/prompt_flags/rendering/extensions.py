"""Custom Jinja2 extension providing {% feature %} block tag.

This is the Tier 3 (opt-in) approach from the spec. The extension
provides ``{% feature "flag_name" %}...{% endfeature %}`` syntax
for conditionally including template blocks based on feature flags.
"""

from collections.abc import Callable
from typing import Any, cast

from jinja2 import nodes
from jinja2.ext import Extension
from jinja2.parser import Parser


class FeatureFlagExtension(Extension):
    """Jinja2 extension adding {% feature "flag_name" %}...{% endfeature %} syntax.

    When the named feature flag is enabled (via the ``feature_enabled``
    global function), the block body is rendered. Otherwise, it produces
    no output.

    Example::

        {% feature "chain_of_thought" %}
        Think step by step before answering.
        {% endfeature %}
    """

    tags = {"feature"}

    def parse(self, parser: Parser) -> nodes.CallBlock:
        """Parse the {% feature %} tag.

        Args:
            parser: The Jinja2 template parser.

        Returns:
            A CallBlock node that delegates to _check_feature at render time.
        """
        lineno = next(parser.stream).lineno

        # Parse the flag name argument (a string constant)
        flag_name = parser.parse_expression()

        # Parse the body until {% endfeature %}
        body = parser.parse_statements(
            ("name:endfeature",),
            drop_needle=True,  # pyright: ignore[reportArgumentType]
        )

        # Create a CallBlock that calls _check_feature with the flag name
        call_block = nodes.CallBlock(
            self.call_method("_check_feature", [flag_name]),
            [],
            [],
            body,
        ).set_lineno(lineno)
        return call_block  # pyright: ignore[reportReturnType]

    def _check_feature(self, flag_name: str, caller: Any) -> str:
        """Check if a feature is enabled and render the block if so.

        Args:
            flag_name: The name of the feature flag to check.
            caller: Callable that renders the block body.

        Returns:
            The rendered block body if the flag is enabled, empty string otherwise.
        """
        # Access the feature_enabled function from the environment globals
        globals_dict = cast(dict[str, Any], self.environment.globals)
        feature_enabled = cast(Callable[[str], bool] | None, globals_dict.get("feature_enabled"))
        if feature_enabled and feature_enabled(flag_name):
            return caller()
        return ""
