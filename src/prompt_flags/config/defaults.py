"""Default configuration constants for prompt_flags.

Provides sensible fallback values used throughout the config layer
when values are not explicitly specified in YAML.
"""

DEFAULT_VERSION: str = "1.0"
"""Default config schema version."""

DEFAULT_PRIORITY: int = 100
"""Default section ordering priority (lower = earlier)."""

DEFAULT_FLAG_TYPE: str = "str"
"""Default env_var type when not specified."""
