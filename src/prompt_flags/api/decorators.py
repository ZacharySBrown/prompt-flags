"""Decorator-based API for registering prompts via class definitions.

Provides @bucket, @prompt, and @section decorators that register
prompt sections with a module-level global registry when the decorated
class is instantiated.
"""

from collections.abc import Callable
from typing import Any

from prompt_flags.core.models import Bucket, Prompt, Section
from prompt_flags.core.registry import PromptRegistry

# Module-level global registry for decorator-based registration
_global_registry: PromptRegistry | None = None

# Metadata attribute names stored on decorated classes/methods
_BUCKET_ATTR = "_pf_bucket_name"
_PROMPT_ATTR = "_pf_prompt_name"
_SECTION_ATTR = "_pf_section_meta"
_SECTIONS_ATTR = "_pf_sections"


def get_global_registry() -> PromptRegistry:
    """Get or create the global decorator registry.

    Returns:
        The shared PromptRegistry for all decorator-registered prompts.
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = PromptRegistry(strict=False)
    return _global_registry


def reset_global_registry() -> None:
    """Reset the global registry, clearing all registered entities.

    Intended for test isolation.
    """
    global _global_registry
    _global_registry = None


def section(
    id: str,
    *,
    flag: str | None = None,
    priority: int = 100,
    before: list[str] | None = None,
    after: list[str] | None = None,
) -> Callable[[Callable[..., str]], Callable[..., str]]:
    """Method decorator that registers a method as a section provider.

    The decorated method should accept (self, ctx) and return a string.
    Section metadata is stored on the method for later collection by
    the @prompt and @bucket class decorators.

    Args:
        id: Unique identifier for the section.
        flag: Optional feature flag controlling this section.
        priority: Ordering priority (lower = earlier). Default 100.
        before: Section IDs this section should appear before.
        after: Section IDs this section should appear after.

    Returns:
        A decorator that annotates the method with section metadata.
    """

    def decorator(func: Callable[..., str]) -> Callable[..., str]:
        """Attach section metadata to the method."""
        setattr(func, _SECTION_ATTR, {
            "id": id,
            "flag": flag,
            "priority": priority,
            "before": before or [],
            "after": after or [],
        })
        return func

    return decorator


def prompt(name: str) -> Callable[[type], type]:
    """Class decorator that registers a class as a prompt.

    Stores the prompt name on the class and collects all @section-decorated
    methods.

    Args:
        name: The prompt name.

    Returns:
        A class decorator.
    """

    def decorator(cls: type) -> type:
        """Attach prompt metadata and wrap __init__ for auto-registration."""
        setattr(cls, _PROMPT_ATTR, name)

        # Collect section-decorated methods
        section_methods: list[tuple[Callable[..., Any], dict[str, Any]]] = []
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name, None)
            if callable(attr) and hasattr(attr, _SECTION_ATTR):
                meta: dict[str, Any] = getattr(attr, _SECTION_ATTR)
                section_methods.append((attr, meta))

        # Sort by priority for deterministic ordering
        section_methods.sort(key=lambda x: x[1]["priority"])
        setattr(cls, _SECTIONS_ATTR, section_methods)

        # Wrap __init__ to register on instantiation
        original_init = cls.__init__ if hasattr(cls, "__init__") else None

        def new_init(self: Any, *args: Any, **kwargs: Any) -> None:
            """Initialize and register the instance with the global registry."""
            if original_init and original_init is not object.__init__:
                original_init(self, *args, **kwargs)

            _register_instance(self)

        cls.__init__ = new_init  # type: ignore[misc]
        return cls

    return decorator


def bucket(name: str, *, description: str = "") -> Callable[[type], type]:
    """Class decorator that registers a prompt class in a bucket.

    Stores the bucket name and description on the class.

    Args:
        name: The bucket name.
        description: Optional bucket description.

    Returns:
        A class decorator.
    """

    def decorator(cls: type) -> type:
        """Attach bucket name to the class."""
        setattr(cls, _BUCKET_ATTR, name)
        return cls

    return decorator


def _register_instance(instance: Any) -> None:
    """Register a decorated class instance with the global registry.

    Collects section metadata from the class, calls each section method
    with an empty context to get content, and registers the prompt
    and bucket.

    Args:
        instance: An instance of a @bucket/@prompt decorated class.
    """
    cls = instance.__class__
    bucket_name: str = getattr(cls, _BUCKET_ATTR, "default")
    prompt_name: str = getattr(cls, _PROMPT_ATTR)
    section_methods: list[tuple[Callable[..., Any], dict[str, Any]]] = getattr(
        cls, _SECTIONS_ATTR, []
    )

    registry = get_global_registry()

    # Build sections by calling each method with empty context
    sections: list[Section] = []
    for method, meta in section_methods:
        try:
            content = method(instance, {})
        except Exception:
            content = ""

        sections.append(
            Section(
                id=meta["id"],
                content=content,
                flag=meta["flag"],
                priority=meta["priority"],
                before=meta["before"],
                after=meta["after"],
            )
        )

    prompt_obj = Prompt(name=prompt_name, sections=sections)

    # Get or create the bucket, merging prompts
    try:
        existing_bucket = registry.get_bucket(bucket_name)
        merged_prompts = dict(existing_bucket.prompts)
        merged_prompts[prompt_name] = prompt_obj
        new_bucket = Bucket(
            name=bucket_name,
            description=existing_bucket.description,
            prompts=merged_prompts,
            flags=existing_bucket.flags,
        )
    except KeyError:
        new_bucket = Bucket(
            name=bucket_name,
            prompts={prompt_name: prompt_obj},
        )

    registry.add_bucket(new_bucket)
