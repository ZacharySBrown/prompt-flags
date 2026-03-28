"""Pydantic v2 config models that validate YAML input.

These models represent the YAML configuration structure. They are separate
from the core domain models and are converted to core models by the loader.

All models use ``extra="forbid"`` to catch YAML typos at load time.
"""

from pydantic import BaseModel, ConfigDict, model_validator

from prompt_flags.config.defaults import (
    DEFAULT_FLAG_TYPE,
    DEFAULT_PRIORITY,
    DEFAULT_VERSION,
)


class EnvVarDef(BaseModel):
    """Definition for an environment variable mapping.

    Attributes:
        default: Default value if the env var is not set.
        type: Type hint for the env var value (e.g., "str", "int", "float").
    """

    model_config = ConfigDict(extra="forbid")

    default: str | None = None
    type: str = DEFAULT_FLAG_TYPE


class OrderingDef(BaseModel):
    """A relative ordering constraint between two sections.

    Attributes:
        before: ID of the section that should come first.
        after: ID of the section that should come second.
    """

    model_config = ConfigDict(extra="forbid")

    before: str
    after: str


class FlagDef(BaseModel):
    """A feature flag definition with default value.

    Attributes:
        default: Default boolean value when no override is set.
        description: Human-readable description of what this flag controls.
    """

    model_config = ConfigDict(extra="forbid")

    default: bool
    description: str = ""


class FlagOverrideDef(BaseModel):
    """A flag override at bucket or prompt level.

    A value of None means "not set at this level, defer to parent."

    Attributes:
        enabled: Override value. None means inherit from parent.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None


class SectionDef(BaseModel):
    """A prompt section definition in YAML config.

    Attributes:
        id: Unique identifier for this section.
        flag: Name of the feature flag controlling this section.
        priority: Ordering priority (lower = earlier).
        before: Section IDs this section should appear before.
        after: Section IDs this section should appear after.
        content: Inline text content for this section.
        template: Template file reference for this section.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    flag: str | None = None
    priority: int = DEFAULT_PRIORITY
    before: list[str] = []
    after: list[str] = []
    content: str | None = None
    template: str | None = None


class PromptDef(BaseModel):
    """A prompt definition in YAML config.

    Attributes:
        template: Inline Jinja2 template string or template filename.
        template_path: Path to a Jinja2 template file.
        sections: Ordered list of section definitions.
        flags: Prompt-level flag overrides.
    """

    model_config = ConfigDict(extra="forbid")

    template: str | None = None
    template_path: str | None = None
    sections: list[SectionDef] = []
    flags: dict[str, FlagOverrideDef] = {}


class BucketDef(BaseModel):
    """A bucket definition in YAML config.

    Attributes:
        description: Human-readable description of this bucket.
        template_dir: Directory containing Jinja2 templates for this bucket.
        enabled: Whether this bucket is active.
        flags: Bucket-level flag overrides.
        prompts: Named prompts within this bucket.
        ordering: Bucket-level ordering constraints.
    """

    model_config = ConfigDict(extra="forbid")

    description: str = ""
    template_dir: str | None = None
    enabled: bool = True
    flags: dict[str, FlagOverrideDef] = {}
    prompts: dict[str, PromptDef] = {}
    ordering: list[OrderingDef] = []


class GlobalConfig(BaseModel):
    """Root configuration model validated from YAML.

    Cross-validates that all flag references in sections, bucket overrides,
    and prompt overrides point to declared flags.

    Attributes:
        version: Config schema version string.
        buckets: Named bucket definitions.
        flags: Global feature flag definitions.
        ordering: Global ordering constraints.
        env_vars: Environment variable mappings.
    """

    model_config = ConfigDict(extra="forbid")

    version: str = DEFAULT_VERSION
    buckets: dict[str, BucketDef] = {}
    flags: dict[str, FlagDef] = {}
    ordering: list[OrderingDef] = []
    env_vars: dict[str, EnvVarDef] = {}

    @model_validator(mode="after")
    def validate_flag_references(self) -> "GlobalConfig":
        """Validate that all flag references point to declared flags.

        Checks section flag references, bucket-level flag overrides,
        and prompt-level flag overrides.

        Returns:
            The validated config.

        Raises:
            ValueError: If any flag reference is undeclared.
        """
        declared = set(self.flags.keys())
        undeclared: list[str] = []

        for bucket_name, bucket_def in self.buckets.items():
            # Check bucket-level flag overrides
            for flag_name in bucket_def.flags:
                if flag_name not in declared:
                    undeclared.append(
                        f"Bucket {bucket_name!r} references undeclared flag "
                        f"{flag_name!r}"
                    )

            for prompt_name, prompt_def in bucket_def.prompts.items():
                # Check prompt-level flag overrides
                for flag_name in prompt_def.flags:
                    if flag_name not in declared:
                        undeclared.append(
                            f"Prompt {prompt_name!r} in bucket "
                            f"{bucket_name!r} references undeclared flag "
                            f"{flag_name!r}"
                        )

                # Check section flag references
                for section_def in prompt_def.sections:
                    if (
                        section_def.flag is not None
                        and section_def.flag not in declared
                    ):
                        undeclared.append(
                            f"Section {section_def.id!r} in prompt "
                            f"{prompt_name!r} references undeclared flag "
                            f"{section_def.flag!r}"
                        )

        if undeclared:
            raise ValueError(
                "Flag reference validation failed:\n"
                + "\n".join(f"  - {msg}" for msg in undeclared)
            )

        return self
