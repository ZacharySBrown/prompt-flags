"""Flag resolution engine implementing 4-tier precedence.

Resolution order (highest to lowest priority):
1. Runtime override — programmatic override at render time
2. Prompt-level override — declared in prompt config
3. Bucket-level override — declared in bucket config
4. Global default — the flag's default value
"""

from prompt_flags.core.models import (
    FlagDefinitions,
    FlagResolutionMap,
    FlagResult,
    FlagScope,
    RuntimeOverrides,
)


class UndefinedFlagError(Exception):
    """Raised when a flag is referenced but not defined in the registry.

    Attributes:
        flag_name: The name of the undefined flag.
    """

    def __init__(self, flag_name: str) -> None:
        """Initialize with the undefined flag name.

        Args:
            flag_name: The name of the flag that was not found.
        """
        self.flag_name = flag_name
        super().__init__(f"Undefined flag: {flag_name!r}")


def resolve_flag(
    flag_name: str,
    flags: FlagDefinitions,
    bucket_flags: FlagScope,
    prompt_flags: FlagScope,
    runtime_overrides: RuntimeOverrides | None = None,
    *,
    strict: bool = True,
) -> FlagResult:
    """Resolve a single flag through the 4-tier precedence chain.

    Walks from most-specific to least-specific: runtime > prompt > bucket > global.
    A value of None at any tier means "not set, defer to parent."

    Args:
        flag_name: The flag to resolve.
        flags: Global flag definitions.
        bucket_flags: Bucket-level flag overrides.
        prompt_flags: Prompt-level flag overrides.
        runtime_overrides: Runtime overrides passed at render time.
        strict: If True, raise UndefinedFlagError for unknown flags.

    Returns:
        A FlagResult with the resolved value and source tier.

    Raises:
        UndefinedFlagError: If the flag is not defined and strict is True.
    """
    # Tier 0: Runtime override (highest priority)
    if runtime_overrides and flag_name in runtime_overrides.flags:
        return FlagResult(
            name=flag_name, value=runtime_overrides.flags[flag_name], source="runtime"
        )

    # Tier 1: Prompt-level override
    prompt_value = prompt_flags.overrides.get(flag_name)
    if prompt_value is not None:
        return FlagResult(name=flag_name, value=prompt_value, source="prompt")

    # Tier 2: Bucket-level override
    bucket_value = bucket_flags.overrides.get(flag_name)
    if bucket_value is not None:
        return FlagResult(name=flag_name, value=bucket_value, source="bucket")

    # Tier 3: Global default
    if flag_name in flags.flags:
        return FlagResult(name=flag_name, value=flags.flags[flag_name].default, source="global")

    # Undefined flag
    if strict:
        raise UndefinedFlagError(flag_name)

    return FlagResult(name=flag_name, value=False, source="default")


def resolve_all_flags(
    flags: FlagDefinitions,
    bucket_flags: FlagScope,
    prompt_flags: FlagScope,
    runtime_overrides: RuntimeOverrides | None = None,
    *,
    strict: bool = True,
) -> FlagResolutionMap:
    """Resolve all defined flags for a given scope.

    Args:
        flags: Global flag definitions.
        bucket_flags: Bucket-level flag overrides.
        prompt_flags: Prompt-level flag overrides.
        runtime_overrides: Runtime overrides passed at render time.
        strict: If True, raise UndefinedFlagError for unknown flags.

    Returns:
        A FlagResolutionMap containing all resolved flag results.
    """
    results = {
        name: resolve_flag(
            name, flags, bucket_flags, prompt_flags, runtime_overrides, strict=strict
        )
        for name in flags.flags
    }
    return FlagResolutionMap(results=results)
