# Package Dependencies

## The Rule

Internal dependencies flow forward through the package:

```
core → config → rendering → api
                    ↑
                plugins (cross-cutting)
```

## Subpackage Rules

| Subpackage | May Import From | May NOT Import From |
|------------|----------------|---------------------|
| `core` | (none — pure models and algorithms) | config, rendering, api, plugins |
| `config` | core | rendering, api, plugins |
| `rendering` | core, config | api |
| `api` | core, config, rendering, plugins | (none — top of the stack) |
| `plugins` | core (Protocol definitions reference models) | config, rendering, api |

## Valid Import Examples

```python
# In prompt_flags/config/loader.py — importing from core: OK
from prompt_flags.core.models import BucketDef, FlagDef

# In prompt_flags/rendering/engine.py — importing from core and config: OK
from prompt_flags.core.registry import PromptRegistry
from prompt_flags.config.loader import load_config

# In prompt_flags/api/builder.py — importing from any lower package: OK
from prompt_flags.core.models import Section, Prompt
from prompt_flags.rendering.engine import render_template
```

## Invalid Import Examples

```python
# In prompt_flags/core/models.py — importing from config: VIOLATION
from prompt_flags.config.loader import load_config  # core cannot import config

# In prompt_flags/config/loader.py — importing from rendering: VIOLATION
from prompt_flags.rendering.engine import Environment  # config cannot import rendering
```

## Enforcement

- **Pydantic boundary linter**: `tools/linters/check_pydantic_boundaries.py`
- **Structural tests**: `tests/structural/`
- **CI**: GitHub Actions runs linters on every PR
