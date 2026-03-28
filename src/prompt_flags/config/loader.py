"""YAML config loading and conversion to core domain models.

Provides functions to load a YAML config file into a validated GlobalConfig,
and to convert that config into a populated PromptRegistry.
"""

from pathlib import Path

import yaml

from prompt_flags.config.schema import GlobalConfig
from prompt_flags.core.models import (
    Bucket,
    Flag,
    OrderingConstraint,
    Prompt,
    Section,
)
from prompt_flags.core.registry import PromptRegistry


def load_config(path: str | Path) -> GlobalConfig:
    """Load and validate a YAML config file.

    Reads the YAML file and validates its contents against the GlobalConfig
    schema. Raises FileNotFoundError if the file doesn't exist, and
    ValidationError if the YAML content is invalid.

    Args:
        path: Path to the YAML config file.

    Returns:
        A validated GlobalConfig instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
        pydantic.ValidationError: If the YAML content fails validation.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open() as f:
        data = yaml.safe_load(f)

    if data is None:
        data = {}

    return GlobalConfig.model_validate(data)


def build_registry(config: GlobalConfig) -> PromptRegistry:
    """Convert a validated GlobalConfig into a populated PromptRegistry.

    Maps config schema models to core domain models and registers all
    entities (flags, buckets, prompts, sections, ordering constraints)
    in a new PromptRegistry.

    Args:
        config: A validated GlobalConfig instance.

    Returns:
        A PromptRegistry populated with all entities from the config.
    """
    registry = PromptRegistry()

    # Register flags
    for flag_name, flag_def in config.flags.items():
        registry.add_flag(
            Flag(
                name=flag_name,
                default=flag_def.default,
                description=flag_def.description,
            )
        )

    # Register global ordering constraints
    for ordering_def in config.ordering:
        registry.add_ordering_constraint(
            OrderingConstraint(
                before=ordering_def.before,
                after=ordering_def.after,
                source="global",
            )
        )

    # Register buckets
    for bucket_name, bucket_def in config.buckets.items():
        # Convert bucket flag overrides
        bucket_flags: dict[str, bool | None] = {}
        for flag_name, override_def in bucket_def.flags.items():
            bucket_flags[flag_name] = override_def.enabled

        # Convert prompts
        prompts: dict[str, Prompt] = {}
        for prompt_name, prompt_def in bucket_def.prompts.items():
            # Convert prompt flag overrides
            prompt_flags: dict[str, bool | None] = {}
            for flag_name, override_def in prompt_def.flags.items():
                prompt_flags[flag_name] = override_def.enabled

            # Convert sections
            sections: list[Section] = []
            for section_def in prompt_def.sections:
                sections.append(
                    Section(
                        id=section_def.id,
                        content=section_def.content,
                        template_path=section_def.template,
                        flag=section_def.flag,
                        priority=section_def.priority,
                        before=section_def.before,
                        after=section_def.after,
                    )
                )

            prompts[prompt_name] = Prompt(
                name=prompt_name,
                template=prompt_def.template,
                template_path=prompt_def.template_path,
                sections=sections,
                flags=prompt_flags,
            )

        # Register bucket-level ordering constraints
        for ordering_def in bucket_def.ordering:
            registry.add_ordering_constraint(
                OrderingConstraint(
                    before=ordering_def.before,
                    after=ordering_def.after,
                    source=f"bucket:{bucket_name}",
                )
            )

        bucket = Bucket(
            name=bucket_name,
            description=bucket_def.description,
            template_dir=bucket_def.template_dir,
            enabled=bucket_def.enabled,
            prompts=prompts,
            flags=bucket_flags,
        )
        registry.add_bucket(bucket)

    return registry
