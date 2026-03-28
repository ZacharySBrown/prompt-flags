"""Public API: fluent builder, decorators, and standalone functions."""

from prompt_flags.api.builder import PromptBuilder
from prompt_flags.api.decorators import bucket, prompt, section
from prompt_flags.api.functional import compose, from_yaml, render_prompt

__all__ = [
    "PromptBuilder",
    "bucket",
    "compose",
    "from_yaml",
    "prompt",
    "render_prompt",
    "section",
]
