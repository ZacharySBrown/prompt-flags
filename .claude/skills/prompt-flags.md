# /prompt-flags — Work with the PromptFlags Package

You are helping a developer use the `prompt_flags` package to build feature-flagged prompts. This skill covers creating configs, building prompts, debugging flag resolution, and validating setups.

## Input

The user will describe what they want to do. Common requests:

- "Create a new prompt config" / "Set up YAML for my prompts"
- "Add a new section/flag/bucket"
- "Debug why a flag resolved this way"
- "Show me the section ordering for a prompt"
- "Validate my config"
- "Help me use the builder/decorator/functional API"
- "Convert between YAML and code-driven approaches"

## Available APIs

The package provides four parallel interfaces. Choose the right one for the user's needs:

### YAML-driven (best for: config files, non-developer prompt authors)
```python
from prompt_flags import from_yaml, render_prompt, compose

registry = from_yaml("promptflags.yaml")
result = render_prompt(registry, "bucket_name", "prompt_name", context={...})
full = compose(registry, ["bucket1", "bucket2"], context={...}, flags={...})
```

### Fluent builder (best for: quick one-off prompts, scripts, prototyping)
```python
from prompt_flags import PromptBuilder

result = (
    PromptBuilder("my_prompt")
    .in_bucket("my_bucket")
    .section("intro", "You are a helpful assistant.", priority=1)
    .section("reasoning", "Think step by step.", flag="cot", priority=10)
    .section("format", "Respond in {{ fmt }}.", flag="json_mode", priority=20, after=["reasoning"])
    .flag("cot", default=True)
    .flag("json_mode", default=False)
    .order("intro", after="reasoning")
    .render(context={"fmt": "JSON"}, flags={"json_mode": True})
)
```

### Decorator (best for: application code, class-based organization)
```python
from prompt_flags import bucket, prompt, section, render_prompt
from prompt_flags import get_global_registry

@bucket("guides")
@prompt("coding_guide")
class CodingGuide:
    @section(id="identity", priority=1)
    def identity(self, ctx):
        return f"You are {ctx.get('role', 'a coding assistant')}."

    @section(id="reasoning", flag="chain_of_thought", priority=10)
    def reasoning(self, ctx):
        return "Think step by step before answering."

# Instantiation triggers registration
guide = CodingGuide()
registry = get_global_registry()
result = render_prompt(registry, "guides", "coding_guide", context={"role": "a Python expert"})
```

### Functional (best for: operating on existing registries, composition)
```python
from prompt_flags import from_yaml, render_prompt, compose

registry = from_yaml("config.yaml")
single = render_prompt(registry, "guides", "coding_guide", context={...}, flags={"cot": False})
multi = compose(registry, ["system", "guides", "tools", "constraints"], context={...})
```

## Process

### If creating a new YAML config

1. Ask the user about their prompt structure:
   - What buckets do they need? (e.g., system, guides, tools, constraints, output)
   - What sections go in each prompt?
   - What flags should control which sections?
   - Any ordering requirements?

2. Generate a `promptflags.yaml` file following this schema:

```yaml
version: "1.0"

buckets:
  bucket_name:
    description: "What this bucket is for"
    enabled: true
    flags:
      flag_name:
        enabled: true  # bucket-level override (null = inherit)
    prompts:
      prompt_name:
        sections:
          - id: "section_id"
            flag: "flag_name"  # optional — omit for always-on sections
            priority: 10       # lower = earlier
            content: "The actual prompt text or Jinja2 template"
            # before: ["other_section"]  # optional ordering
            # after: ["other_section"]   # optional ordering

flags:
  flag_name:
    default: true
    description: "What this flag controls"

ordering:  # global ordering constraints
  - before: "section_a"
    after: "section_b"

env_vars:
  VAR_NAME:
    default: "value"
```

3. Validate the config:
```python
from prompt_flags.config.loader import load_config
config = load_config("promptflags.yaml")  # Raises ValidationError on problems
```

4. Show the user how to use it:
```python
from prompt_flags import from_yaml, render_prompt
registry = from_yaml("promptflags.yaml")
result = render_prompt(registry, "bucket_name", "prompt_name")
```

### If adding a section/flag/bucket to existing config

1. Read the existing config file
2. Add the new element in the correct location
3. If adding a section with a new flag, also add the flag to the top-level `flags:` section
4. Validate: `load_config("promptflags.yaml")` — the `extra="forbid"` setting will catch typos

### If debugging flag resolution

Use the registry's `resolve_flags()` method to trace resolution:

```python
from prompt_flags import from_yaml

registry = from_yaml("promptflags.yaml")
flag_map = registry.resolve_flags("bucket_name", "prompt_name")

for name, result in flag_map.results.items():
    print(f"{name} = {result.value} (from: {result.source})")
```

Resolution order (highest to lowest priority):
1. **Runtime override** — `flags={"cot": False}` passed at render time
2. **Prompt-level** — `flags: { cot: { enabled: false } }` in the prompt config
3. **Bucket-level** — `flags: { cot: { enabled: true } }` in the bucket config
4. **Global default** — `flags: { cot: { default: true } }` at the top level

If a flag is `None` / not set at a level, it defers to the next level down.

### If showing section ordering

```python
from prompt_flags import from_yaml

registry = from_yaml("promptflags.yaml")
active = registry.get_active_sections("bucket_name", "prompt_name")

for i, section in enumerate(active, 1):
    flag_info = f" [flag: {section.flag}]" if section.flag else ""
    print(f"{i}. {section.id} (priority: {section.priority}){flag_info}")
```

Ordering rules:
- Explicit constraints (`before`/`after`) always win over priority
- Within the same topological level, lower priority number = earlier
- Disabled sections (flag=False) are excluded from the graph entirely
- Constraints referencing missing/disabled sections are silently ignored
- Cycles raise `OrderingCycleError` with the cycle path

### If validating a config

```python
from prompt_flags.config.loader import load_config

try:
    config = load_config("promptflags.yaml")
    print(f"Valid! {len(config.buckets)} buckets, {len(config.flags)} flags")
except FileNotFoundError:
    print("Config file not found")
except Exception as e:
    print(f"Validation error: {e}")
```

Common validation catches:
- **Extra fields**: `extra="forbid"` rejects typos like `defualt: true`
- **Missing flag references**: Sections referencing undeclared flags fail validation
- **Type errors**: Wrong types (e.g., `priority: "high"` instead of `priority: 10`)

### If converting between approaches

**YAML → Code (builder)**:
Read the YAML, then generate equivalent PromptBuilder code. Map each section, flag, and ordering constraint.

**YAML → Code (decorators)**:
Read the YAML, then generate a decorated class per prompt. Each section becomes a method.

**Code → YAML**:
Read the code, extract sections/flags/ordering, and generate the YAML equivalent.

### If using Jinja2 templates in sections

Sections support Jinja2 syntax. Three approaches for feature-flagged content within templates:

**Tier 1 — Global function (recommended)**:
```jinja2
{% if feature_enabled("chain_of_thought") %}
Think step by step before answering.
{% endif %}
```

**Tier 2 — Macro (readable)**:
```jinja2
{% from "macros/features.j2" import feature_section %}
{% call feature_section("chain_of_thought") %}
Think step by step before answering.
{% endcall %}
```

**Tier 3 — Custom tag (opt-in)**:
```jinja2
{% feature "chain_of_thought" %}
Think step by step before answering.
{% endfeature %}
```

The `env()` function is also available in templates:
```jinja2
You are a {{ env("ASSISTANT_ROLE", "helpful assistant") }}.
```

### If creating a plugin

For integrating with external systems (LaunchDarkly, custom loaders, etc.):

```python
from prompt_flags.plugins.protocols import FlagSource

class MyFlagSource:
    """Satisfies FlagSource protocol via structural subtyping."""

    def get_flag(self, name: str, context: dict) -> bool | None:
        # Fetch from your flag system
        return my_system.get(name)

    def get_all_flags(self, context: dict) -> dict[str, bool]:
        return my_system.get_all()
```

For hook-based plugins:
```python
from prompt_flags.plugins import hookimpl

class MyPlugin:
    @hookimpl
    def post_render(self, rendered_text: str, metadata: dict) -> str:
        # Modify rendered text (e.g., add token count)
        return rendered_text + f"\n<!-- tokens: {len(rendered_text.split())} -->"
```

## Rules

- Always validate configs after creating/modifying them
- When generating YAML, use the exact schema — `extra="forbid"` rejects unknown keys
- Flag names must be declared in the top-level `flags:` section before being referenced in sections
- Section IDs must be unique within a prompt
- When debugging, always show the FlagResult.source to explain resolution
- Prefer the simplest API for the user's needs: builder for quick work, YAML for config-driven, decorators for app code
- Reference the initial spec at `initial-spec.md` for detailed design rationale
