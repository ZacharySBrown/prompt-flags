"""Central prompt registry coordinating models, resolver, and ordering.

The PromptRegistry holds all buckets, flags, and ordering constraints,
providing methods to resolve flags and compute section ordering for
any bucket/prompt scope.
"""

from prompt_flags.core.models import (
    Bucket,
    Flag,
    FlagDefinitions,
    FlagResolutionMap,
    FlagScope,
    OrderingConstraint,
    Prompt,
    RuntimeOverrides,
    Section,
)
from prompt_flags.core.ordering import order_sections
from prompt_flags.core.resolver import resolve_all_flags, resolve_flag


class PromptRegistry:
    """Central coordinator holding all prompt entities.

    Manages buckets, flags, and ordering constraints. Provides methods to
    resolve flags for a given scope and compute active section ordering.

    Attributes:
        strict: If True, raise UndefinedFlagError for unknown flags.
    """

    def __init__(self, strict: bool = True) -> None:
        """Initialize an empty registry.

        Args:
            strict: If True, raise UndefinedFlagError for unknown flags.
        """
        self.strict = strict
        self._buckets: dict[str, Bucket] = {}
        self._flags: dict[str, Flag] = {}
        self._constraints: list[OrderingConstraint] = []

    def add_bucket(self, bucket: Bucket) -> None:
        """Register a bucket in the registry.

        Args:
            bucket: The bucket to add.
        """
        self._buckets[bucket.name] = bucket

    def add_flag(self, flag: Flag) -> None:
        """Register a flag definition in the registry.

        Args:
            flag: The flag to add.
        """
        self._flags[flag.name] = flag

    def add_ordering_constraint(self, constraint: OrderingConstraint) -> None:
        """Register an ordering constraint.

        Args:
            constraint: The ordering constraint to add.
        """
        self._constraints.append(constraint)

    def get_bucket(self, name: str) -> Bucket:
        """Retrieve a bucket by name.

        Args:
            name: The bucket name.

        Returns:
            The requested bucket.

        Raises:
            KeyError: If the bucket is not found.
        """
        if name not in self._buckets:
            raise KeyError(f"Bucket not found: {name!r}")
        return self._buckets[name]

    def get_prompt(self, bucket_name: str, prompt_name: str) -> Prompt:
        """Retrieve a prompt from a specific bucket.

        Args:
            bucket_name: The bucket containing the prompt.
            prompt_name: The prompt name.

        Returns:
            The requested prompt.

        Raises:
            KeyError: If the bucket or prompt is not found.
        """
        bucket = self.get_bucket(bucket_name)
        if prompt_name not in bucket.prompts:
            raise KeyError(f"Prompt not found: {prompt_name!r} in bucket {bucket_name!r}")
        return bucket.prompts[prompt_name]

    def _flag_definitions(self) -> FlagDefinitions:
        """Build a FlagDefinitions from the current registry state.

        Returns:
            A FlagDefinitions wrapping all registered flags.
        """
        return FlagDefinitions(flags=self._flags)

    def _bucket_scope(self, bucket: Bucket) -> FlagScope:
        """Build a FlagScope from a bucket's flag overrides.

        Args:
            bucket: The bucket to extract scope from.

        Returns:
            A FlagScope wrapping the bucket's flag overrides.
        """
        return FlagScope(overrides=bucket.flags)

    def _prompt_scope(self, prompt: Prompt) -> FlagScope:
        """Build a FlagScope from a prompt's flag overrides.

        Args:
            prompt: The prompt to extract scope from.

        Returns:
            A FlagScope wrapping the prompt's flag overrides.
        """
        return FlagScope(overrides=prompt.flags)

    def resolve_flags(
        self,
        bucket_name: str,
        prompt_name: str,
        runtime_overrides: RuntimeOverrides | None = None,
    ) -> FlagResolutionMap:
        """Resolve all flags for a specific bucket/prompt scope.

        Args:
            bucket_name: The bucket name for scoping.
            prompt_name: The prompt name for scoping.
            runtime_overrides: Optional runtime flag overrides.

        Returns:
            A FlagResolutionMap containing resolved flag results.
        """
        bucket = self.get_bucket(bucket_name)
        prompt = self.get_prompt(bucket_name, prompt_name)
        return resolve_all_flags(
            self._flag_definitions(),
            self._bucket_scope(bucket),
            self._prompt_scope(prompt),
            runtime_overrides,
            strict=self.strict,
        )

    def get_active_sections(
        self,
        bucket_name: str,
        prompt_name: str,
        runtime_overrides: RuntimeOverrides | None = None,
    ) -> list[Section]:
        """Get ordered active sections for a prompt after flag resolution.

        Resolves flags for the given scope, filters out sections whose flags
        are disabled, then orders the remaining sections using constraints
        and priorities.

        Args:
            bucket_name: The bucket name.
            prompt_name: The prompt name.
            runtime_overrides: Optional runtime flag overrides.

        Returns:
            Ordered list of active sections.
        """
        prompt = self.get_prompt(bucket_name, prompt_name)
        bucket = self.get_bucket(bucket_name)
        flag_defs = self._flag_definitions()
        bucket_scope = self._bucket_scope(bucket)
        prompt_scope = self._prompt_scope(prompt)

        # Filter sections by flag state
        active: list[Section] = []
        for section in prompt.sections:
            if section.flag is None:
                active.append(section)
            else:
                result = resolve_flag(
                    section.flag,
                    flag_defs,
                    bucket_scope,
                    prompt_scope,
                    runtime_overrides,
                    strict=self.strict,
                )
                if result.value:
                    active.append(section)

        return order_sections(active, self._constraints)
