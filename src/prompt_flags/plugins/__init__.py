"""Plugin system: Protocol interfaces, hook specs, and discovery."""

from prompt_flags.plugins.protocols import (
    FlagSource,
    PromptComposer,
    PromptLoader,
    PromptRenderer,
)

__all__ = [
    "FlagSource",
    "PromptComposer",
    "PromptLoader",
    "PromptRenderer",
]

try:
    from prompt_flags.plugins.hookspecs import (
        PromptFlagsHookSpec,
        hookimpl,
        hookspec,
    )
    from prompt_flags.plugins.manager import PluginManager

    __all__ += [
        "PluginManager",
        "PromptFlagsHookSpec",
        "hookimpl",
        "hookspec",
    ]
except ImportError:
    pass
