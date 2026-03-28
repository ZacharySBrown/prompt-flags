"""Core domain models for the prompt_flags package.

All models are immutable Pydantic v2 value objects with strict validation.
"""

from pydantic import BaseModel, ConfigDict


class Section(BaseModel):
    """An atomic block of prompt text that can be independently enabled/disabled.

    Sections are the lowest-level building blocks. Each section has a unique ID,
    optional content or template reference, and ordering metadata.

    Attributes:
        id: Unique identifier for this section.
        content: Inline text content for this section.
        template_path: Path to a Jinja2 template file.
        flag: Name of the feature flag controlling this section.
        priority: Ordering priority (lower = earlier). Default 100.
        before: Section IDs this section should appear before.
        after: Section IDs this section should appear after.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    content: str | None = None
    template_path: str | None = None
    flag: str | None = None
    priority: int = 100
    before: list[str] = []
    after: list[str] = []


class Prompt(BaseModel):
    """A logical prompt document grouping one or more sections.

    Attributes:
        name: Unique name identifying this prompt.
        template: Inline Jinja2 template string.
        template_path: Path to a Jinja2 template file.
        sections: Ordered list of sections in this prompt.
        flags: Prompt-level flag overrides. None means inherit from parent.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    template: str | None = None
    template_path: str | None = None
    sections: list[Section] = []
    flags: dict[str, bool | None] = {}


class Bucket(BaseModel):
    """A named category containing related prompts.

    Attributes:
        name: Unique name identifying this bucket.
        description: Human-readable description of this bucket's purpose.
        template_dir: Directory containing Jinja2 templates for this bucket.
        enabled: Whether this bucket is active.
        prompts: Named prompts within this bucket.
        flags: Bucket-level flag overrides. None means inherit from parent.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    description: str = ""
    template_dir: str | None = None
    enabled: bool = True
    prompts: dict[str, Prompt] = {}
    flags: dict[str, bool | None] = {}


class Flag(BaseModel):
    """A feature flag definition with a default value.

    Attributes:
        name: Unique name identifying this flag.
        default: Default boolean value when no override is set.
        description: Human-readable description of what this flag controls.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    default: bool
    description: str = ""


class FlagOverrides(BaseModel):
    """Stores the 3-tier override chain for a single flag.

    The resolver walks from most-specific to least-specific:
    prompt_overrides > bucket_overrides > global_value.

    Attributes:
        global_value: Global override value. None means use flag default.
        bucket_overrides: Per-bucket override values.
        prompt_overrides: Per-bucket-per-prompt override values.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    global_value: bool | None = None
    bucket_overrides: dict[str, bool | None] = {}
    prompt_overrides: dict[str, dict[str, bool | None]] = {}


class OrderingConstraint(BaseModel):
    """Expresses a relative ordering relation between two sections.

    The constraint means: the section named `before` must appear before
    the section named `after` in the final ordering.

    Attributes:
        before: ID of the section that comes first.
        after: ID of the section that comes second.
        source: Where this constraint was declared, for debugging.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    before: str
    after: str
    source: str = ""


class FlagResult(BaseModel):
    """The resolved value of a flag with provenance information.

    Attributes:
        name: The flag name that was resolved.
        value: The resolved boolean value.
        source: Which tier provided the resolved value (e.g., "global", "bucket", "runtime").
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    value: bool
    source: str


class RuntimeOverrides(BaseModel):
    """Runtime flag overrides passed at render time.

    Attributes:
        flags: Mapping of flag names to their override values.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    flags: dict[str, bool] = {}


class FlagScope(BaseModel):
    """Scoped flag overrides for resolution (bucket or prompt level).

    Values of None mean "not set at this level, defer to parent."

    Attributes:
        overrides: Mapping of flag names to their override values.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    overrides: dict[str, bool | None] = {}


class FlagDefinitions(BaseModel):
    """Collection of flag definitions.

    Attributes:
        flags: Mapping of flag names to their Flag definitions.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    flags: dict[str, Flag] = {}


class FlagResolutionMap(BaseModel):
    """Collection of resolved flag results for a given scope.

    Attributes:
        results: Mapping of flag names to their resolved FlagResult.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    results: dict[str, FlagResult] = {}

    def __getitem__(self, key: str) -> FlagResult:
        """Get a flag result by name.

        Args:
            key: The flag name.

        Returns:
            The resolved FlagResult.
        """
        return self.results[key]

    def __contains__(self, key: object) -> bool:
        """Check if a flag name is in the results.

        Args:
            key: The flag name to check.

        Returns:
            True if the flag is present.
        """
        return key in self.results


class RenderedSection(BaseModel):
    """A section after rendering, containing final content.

    Attributes:
        id: The section ID.
        content: The rendered text content.
        flag: The flag that controlled this section, if any.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    content: str
    flag: str | None = None
