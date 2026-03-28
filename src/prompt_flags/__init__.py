"""PromptFlags: Feature flags for prompt engineering."""

from prompt_flags.api.builder import PromptBuilder
from prompt_flags.api.decorators import bucket, prompt, section
from prompt_flags.api.functional import compose, from_yaml, render_prompt
from prompt_flags.core.models import (
    Bucket,
    Flag,
    FlagOverrides,
    FlagResult,
    OrderingConstraint,
    RenderedSection,
    Section,
)
from prompt_flags.core.ordering import OrderingCycleError
from prompt_flags.core.registry import PromptRegistry
from prompt_flags.core.resolver import UndefinedFlagError
from prompt_flags.plugins.protocols import (
    FlagSource,
    PromptComposer,
    PromptLoader,
)
from prompt_flags.plugins.protocols import PromptRenderer as PromptRendererProtocol
from prompt_flags.rendering.engine import PromptRenderer

__all__ = [
    "Bucket",
    "Flag",
    "FlagOverrides",
    "FlagResult",
    "FlagSource",
    "OrderingConstraint",
    "OrderingCycleError",
    "PromptBuilder",
    "PromptComposer",
    "PromptLoader",
    "PromptRegistry",
    "PromptRenderer",
    "PromptRendererProtocol",
    "RenderedSection",
    "Section",
    "UndefinedFlagError",
    "bucket",
    "compose",
    "from_yaml",
    "prompt",
    "render_prompt",
    "section",
]
