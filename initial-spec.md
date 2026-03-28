# Implementation plan for a Python prompt feature-flag package

**The Python prompt engineering ecosystem has no library that combines feature-flagged sections, declarative ordering, and bucket-based prompt organization.** This gap — confirmed across LangChain, Guidance, DSPy, PromptLayer, and every other major library — makes the proposed package genuinely novel. The plan below specifies `promptflags`, a native Python package that manages named prompt sections across multiple buckets, enables/disables them via a 3-tier feature-flag hierarchy, resolves ordering via topological sort, and plugs into any existing prompt system through Protocol-based adapters.

---

## Package name and directory structure

The suggested package name is **`promptflags`** — short, descriptive, and available as a mental model ("feature flags for prompts"). The PyPI name would be `promptflags`, the import name `promptflags`.

```
promptflags/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── promptflags/
│       ├── __init__.py              # Public API re-exports
│       ├── py.typed                 # PEP 561 type marker
│       ├── _version.py              # Single-source version
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── models.py            # Pydantic v2 domain models (Bucket, Section, Flag, etc.)
│       │   ├── registry.py          # Central PromptRegistry — holds all buckets, sections, flags
│       │   ├── resolver.py          # Flag resolution engine (3-tier precedence)
│       │   └── ordering.py          # Topological sort + priority-based section ordering
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── schema.py            # Pydantic v2 config schemas for YAML validation
│       │   ├── loader.py            # YAML config loading + layered merging
│       │   └── defaults.py          # Built-in default config values
│       │
│       ├── rendering/
│       │   ├── __init__.py
│       │   ├── engine.py            # Jinja2 Environment setup + rendering pipeline
│       │   ├── extensions.py        # Custom Jinja2 FeatureFlag extension tag
│       │   └── filters.py           # Custom Jinja2 filters and globals for prompts
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── builder.py           # Fluent builder API for code-driven prompt assembly
│       │   ├── decorators.py        # @section, @prompt, @bucket decorators
│       │   └── functional.py        # Standalone functions (render_prompt, compose, etc.)
│       │
│       ├── plugins/
│       │   ├── __init__.py
│       │   ├── protocols.py         # Protocol interfaces for adapters
│       │   ├── hookspecs.py         # Pluggy hook specifications
│       │   └── manager.py           # Plugin discovery + registration
│       │
│       └── _bundled/
│           ├── __init__.py
│           └── templates/           # Default Jinja2 macros (feature_section, etc.)
│               └── macros/
│                   └── features.j2
│
├── tests/
│   ├── conftest.py
│   ├── test_core/
│   │   ├── test_models.py
│   │   ├── test_registry.py
│   │   ├── test_resolver.py
│   │   └── test_ordering.py
│   ├── test_config/
│   │   ├── test_schema.py
│   │   └── test_loader.py
│   ├── test_rendering/
│   │   ├── test_engine.py
│   │   └── test_extensions.py
│   ├── test_api/
│   │   ├── test_builder.py
│   │   └── test_decorators.py
│   ├── test_plugins/
│   │   └── test_protocols.py
│   └── fixtures/
│       ├── sample_config.yaml
│       └── sample_prompts/
│           ├── tool_prompts/
│           ├── guides/
│           └── output_formatting/
│
└── docs/
    ├── index.md
    ├── quickstart.md
    ├── yaml-reference.md
    └── plugin-guide.md
```

The `pyproject.toml` should use **Hatchling** as the build backend (modern, extensible, PyPA-maintained), with `src` layout, `py.typed` marker, and non-Python files (YAML schemas, Jinja2 templates) included via `[tool.hatch.build]` config. Python **≥3.10** as the minimum version, to leverage `graphlib`, `match` statements, and modern type union syntax.

---

## Core abstractions and their relationships

Seven domain entities form the backbone. Each maps to a Pydantic v2 `BaseModel` for validation and serialization.

**Section** is the atomic unit — a named block of prompt text that can be independently enabled/disabled. Every section has a unique `id`, belongs to exactly one `Prompt`, carries optional ordering metadata (`priority: int`, `before: list[str]`, `after: list[str]`), and can be either inline text or a reference to a Jinja2 template file. Sections are the things that feature flags target.

**Prompt** groups one or more Sections into a logical prompt document. A prompt has a `name`, a `template_path` (Jinja2 file) or inline `template` string, and an ordered list of section references. Prompts belong to a Bucket.

**Bucket** is a named category containing related Prompts — for example, `tool_prompts`, `guides`, `output_formatting`, `system_context`, `constraints`. Buckets have their own flag overrides (bucket-level scope) and section ordering rules. The baseline set is 3–5 buckets, but users can define any number.

**Flag** represents a single feature toggle. It has a `name`, a `default_value` (bool or a typed variant value), and optional scoped overrides stored in a `FlagOverrides` object. Flags control whether sections are rendered.

**FlagOverrides** stores the 3-tier override chain for a single flag: `global_value → bucket_overrides: dict[str, bool] → prompt_overrides: dict[str, dict[str, bool]]`. The resolver walks this chain from most-specific to least-specific.

**OrderingConstraint** expresses a relative ordering relation: `(section_a, BEFORE, section_b)`. These are collected and fed into the topological sorter. Each constraint carries a `source` field indicating where it was declared (global config, bucket config, or prompt config) for debugging.

**PromptRegistry** is the central coordinator. It holds all Buckets, Prompts, Sections, Flags, and OrderingConstraints. It provides methods to load from YAML, register via code API, resolve flags for a given scope, compute section order, and render final prompt strings. It owns the Jinja2 `Environment` and the plugin manager.

The entity relationships flow as: `PromptRegistry 1──* Bucket 1──* Prompt 1──* Section`, with `Flag` and `OrderingConstraint` as cross-cutting entities referenced by ID from any level.

---

## YAML schema design with examples

The configuration uses a **layered YAML approach**: a global config file establishes defaults, per-bucket config files override bucket-level settings, and per-prompt inline overrides take highest precedence. Pydantic v2 models validate every layer at load time with `ConfigDict(extra="forbid")` to catch typos.

### Global config (`promptflags.yaml`)

```yaml
version: "1.0"

# Bucket definitions
buckets:
  tool_prompts:
    description: "Prompts for tool use instructions"
    template_dir: "prompts/tool_prompts"
    enabled: true

  guides:
    description: "Step-by-step reasoning guides"
    template_dir: "prompts/guides"
    enabled: true

  output_formatting:
    description: "Output structure and format instructions"
    template_dir: "prompts/output_formatting"
    enabled: true

  system_context:
    description: "System-level context and identity"
    template_dir: "prompts/system_context"
    enabled: true

  constraints:
    description: "Safety and behavioral constraints"
    template_dir: "prompts/constraints"
    enabled: true

# Global feature flags (defaults for all buckets/prompts)
flags:
  chain_of_thought:
    default: true
    description: "Enable step-by-step reasoning sections"

  few_shot_examples:
    default: false
    description: "Include few-shot examples in prompts"

  json_output:
    default: false
    description: "Instruct model to respond in JSON"

  safety_guardrails:
    default: true
    description: "Include safety constraint sections"

  verbose_instructions:
    default: false
    description: "Use detailed instruction variants"

# Global section ordering
ordering:
  - before: "system_identity"
    after: "task_description"
  - before: "task_description"
    after: "constraints_block"
  - before: "constraints_block"
    after: "output_format"
  - before: "output_format"
    after: "examples"

# Env var mappings for template substitution
env_vars:
  MODEL_NAME: { default: "gpt-4" }
  TEMPERATURE: { default: "0.7", type: "float" }
  MAX_TOKENS: { default: "4096", type: "int" }
```

### Bucket-level config (`prompts/guides/bucket.yaml`)

```yaml
# Overrides for the "guides" bucket
flags:
  chain_of_thought:
    enabled: true            # Override: always on in guides
  few_shot_examples:
    enabled: true            # Override: on for all guide prompts
  verbose_instructions:
    enabled: true            # Override: guides should be verbose

ordering:
  - before: "reasoning_steps"
    after: "worked_example"

# Bucket-level prompts
prompts:
  coding_guide:
    template: "coding_guide.j2"
    sections:
      - id: "reasoning_steps"
        flag: "chain_of_thought"
        priority: 10
      - id: "worked_example"
        flag: "few_shot_examples"
        priority: 20
      - id: "style_constraints"
        flag: "safety_guardrails"
        priority: 30

  analysis_guide:
    template: "analysis_guide.j2"
    flags:
      verbose_instructions:
        enabled: false       # Prompt-level override: concise for this one
    sections:
      - id: "analysis_framework"
        flag: "chain_of_thought"
        priority: 10
      - id: "output_schema"
        flag: "json_output"
        priority: 20
```

### Pydantic v2 validation schema

The config models use `Optional[bool] = None` as the "inherit from parent" sentinel — a pattern drawn from Flagsmith and Django-Waffle. `None` means "not set at this level, defer to parent." Explicit `True`/`False` means "override."

```
GlobalConfig
├── version: str
├── buckets: dict[str, BucketDef]
│   └── BucketDef
│       ├── description: str
│       ├── template_dir: str
│       ├── enabled: bool = True
│       ├── flags: dict[str, FlagOverride] (Optional[bool] values)
│       └── prompts: dict[str, PromptDef]
│           └── PromptDef
│               ├── template: str
│               ├── flags: dict[str, FlagOverride]
│               └── sections: list[SectionDef]
│                   └── SectionDef
│                       ├── id: str
│                       ├── flag: str
│                       ├── priority: int = 100
│                       ├── before: list[str] = []
│                       └── after: list[str] = []
├── flags: dict[str, FlagDef]
│   └── FlagDef
│       ├── default: bool
│       └── description: str
├── ordering: list[OrderingDef]
│   └── OrderingDef: { before: str, after: str }
└── env_vars: dict[str, EnvVarDef]
```

All models use `ConfigDict(extra="forbid")` to reject unrecognized keys, catching YAML typos at load time. Cross-references (e.g., a section's `flag` field referencing a declared flag name) are validated via `@model_validator(mode="after")` on the root config.

---

## Jinja2 integration approach

The research strongly favors a **hybrid approach**: a global `feature_enabled()` function registered on the Jinja2 Environment, combined with a reusable macro library and an optional custom extension tag for power users. This delivers clean syntax without the debugging complexity of full custom AST extensions.

### Environment configuration

```
Environment settings:
  autoescape=False           # Not HTML — raw prompt text
  trim_blocks=True           # Remove newlines after {% %} tags
  lstrip_blocks=True         # Strip leading whitespace from tag lines
  keep_trailing_newline=True # Preserve file trailing newlines
  undefined=StrictUndefined  # Fail fast on missing variables
  extensions=[FeatureFlagExtension]  # Optional custom tag
```

The loader uses **PrefixLoader** with one prefix per bucket, wrapped in a **ChoiceLoader** that falls back to a shared template directory. This lets templates reference `{% include "shared/safety.j2" %}` while bucket-specific templates live namespaced under `tool_prompts/`, `guides/`, etc.

### Three-tier template integration

**Tier 1 — Global function (primary approach):** Register `feature_enabled(flag_name)` and `env(var_name, default)` as `env.globals`. Template authors write standard `{% if feature_enabled("chain_of_thought") %}...{% endif %}` blocks. The function internally calls the resolver with the current rendering scope (bucket + prompt context).

**Tier 2 — Macro library (recommended for readability):** A bundled `macros/features.j2` provides `feature_section(flag_name, title=None)` as a call-block macro. Usage: `{% call feature_section("chain_of_thought") %}Think step by step.{% endcall %}`. This is syntactic sugar over the global function, adding semantic clarity and the ability to include section titles.

**Tier 3 — Custom extension tag (opt-in for power users):** A `FeatureFlagExtension` that provides `{% feature "flag_name" %}...{% endfeature %}` syntax. Implemented via `jinja2.ext.Extension` with a `CallBlock` node that calls `_check_feature()` at render time. This is registered optionally and enables static analysis tools to identify all feature-flagged sections in templates.

### Template example

```jinja2
{% from "macros/features.j2" import feature_section %}

You are a {{ env("ASSISTANT_ROLE", "helpful assistant") }}.

{% call feature_section("system_identity") %}
Your name is {{ assistant_name }}. You were created by {{ org_name }}.
{% endcall %}

{% call feature_section("chain_of_thought", title="Reasoning") %}
Think step by step before answering. Show your reasoning process.
{% endcall %}

{% if feature_enabled("json_output") %}
Respond in valid JSON with keys: "answer", "confidence"
{% else %}
Respond in clear, concise plain text.
{% endif %}

{% call feature_section("safety_guardrails") %}
Important: Do not generate harmful content. Decline requests outside your capabilities.
{% endcall %}
```

The rendering engine resolves flags for the specific bucket + prompt scope, injects the resolved flag state into the Jinja2 context, and renders the template. Whitespace normalization runs as a post-processing step to collapse multiple blank lines caused by disabled sections.

---

## Flag resolution algorithm

The resolution follows a **most-specific-wins** precedence chain inspired by Flagsmith's 3-tier model and Django-Waffle's explicit precedence documentation. The algorithm is deterministic and fast (O(1) dict lookups at each tier).

**Precedence order (highest to lowest):**

1. **Runtime override** — programmatic override passed at render time (e.g., `render(flags={"chain_of_thought": False})`). Highest priority.
2. **Prompt-level override** — declared in the prompt's YAML config or via code API for a specific prompt.
3. **Bucket-level override** — declared in the bucket's config, applies to all prompts in that bucket.
4. **Global default** — the flag's `default` value from the top-level config.

**Resolution pseudocode:**

```
resolve_flag(flag_name, bucket_id, prompt_id, runtime_overrides) → bool:
    # Tier 0: Runtime override (highest)
    if flag_name in runtime_overrides:
        return runtime_overrides[flag_name]

    # Tier 1: Prompt-level override
    prompt_flags = registry.get_prompt_flags(bucket_id, prompt_id)
    if flag_name in prompt_flags and prompt_flags[flag_name] is not None:
        return prompt_flags[flag_name]

    # Tier 2: Bucket-level override
    bucket_flags = registry.get_bucket_flags(bucket_id)
    if flag_name in bucket_flags and bucket_flags[flag_name] is not None:
        return bucket_flags[flag_name]

    # Tier 3: Global default (lowest)
    flag_def = registry.get_flag_definition(flag_name)
    if flag_def is not None:
        return flag_def.default

    # Undefined flag → raise or return False (configurable)
    raise UndefinedFlagError(flag_name)
```

The sentinel value `None` (mapped from YAML's `~` or absence of the key) means "not set at this tier — defer to parent." This is the same pattern used by Flagsmith's identity → segment → environment chain and Dynaconf's merge strategy. A `FlagResolutionTrace` dataclass records which tier provided the resolved value, enabling debugging output like `chain_of_thought=True (resolved from: bucket "guides")`.

---

## Section ordering algorithm

Section ordering combines **explicit priority values** with **relative ordering constraints**, resolved via topological sort with priority-based tiebreaking. This is the approach used by task schedulers and build systems, adapted here for prompt sections.

**Algorithm:**

1. **Collect all active sections** — after flag resolution, gather only the sections whose flags are enabled. Disabled sections are excluded from the ordering graph entirely.

2. **Build the dependency graph** — from three sources, in increasing precedence: global `ordering` constraints, bucket-level `ordering` constraints, and per-section `before`/`after` declarations. Each constraint `{before: A, after: B}` adds a directed edge `A → B` in the graph.

3. **Detect cycles** — use `graphlib.TopologicalSorter.prepare()`, which raises `CycleError` with the cycle path. Surface this as a clear `OrderingCycleError` with the section names involved and which config file introduced the conflicting constraint.

4. **Sort with priority tiebreaking** — process the graph level by level using the dynamic `get_ready()` / `done()` API. Within each level (sections with no unresolved dependencies), sort by `priority` value (lower = earlier). This ensures hard ordering constraints always win, while priority determines order among unconstrained sections.

5. **Emit the final sequence** — return an ordered list of `Section` objects ready for rendering.

**Pseudocode:**

```
order_sections(active_sections, constraints) → list[Section]:
    graph = {}  # section_id → set of predecessor section_ids
    for section in active_sections:
        graph.setdefault(section.id, set())
    
    for constraint in constraints:
        if constraint.before in graph and constraint.after in graph:
            graph[constraint.after].add(constraint.before)
    
    # Also add per-section before/after declarations
    for section in active_sections:
        for before_id in section.before:
            if before_id in graph:
                graph[section.id].add(before_id)
        for after_id in section.after:
            if after_id in graph:
                graph[after_id].add(section.id)
    
    sorter = TopologicalSorter(graph)
    sorter.prepare()  # Raises CycleError if cycles exist
    
    result = []
    while sorter.is_active():
        ready = sorter.get_ready()
        # Tiebreak by priority within each topological level
        sorted_ready = sorted(ready, key=lambda sid: sections_by_id[sid].priority)
        result.extend(sorted_ready)
        sorter.done(*ready)
    
    return [sections_by_id[sid] for sid in result]
```

The stdlib `graphlib.TopologicalSorter` is sufficient — NetworkX is overkill for this use case and would add a heavy dependency. The algorithm handles missing references gracefully (constraints referencing disabled/nonexistent sections are silently skipped).

---

## Plugin interface specification

The plugin system uses **Protocol-based interfaces** for zero-coupling adapter definitions, **pluggy hooks** for pre/post processing extensibility, and **entry_points** for automatic discovery of installed plugins. This combination was chosen because Protocols let existing prompt systems implement the interface without importing `promptflags`, while pluggy provides the 1:N hook fan-out needed for processing pipelines.

### Protocol interfaces (`plugins/protocols.py`)

```
class PromptLoader(Protocol):
    """Loads raw template content from a storage backend."""
    def load(self, name: str, bucket: str | None = None) → str: ...
    def list_templates(self, bucket: str | None = None) → list[str]: ...

class PromptRenderer(Protocol):
    """Renders a template string with context variables."""
    def render(self, template: str, context: dict[str, Any]) → str: ...

class PromptComposer(Protocol):
    """Assembles multiple rendered sections into a final prompt string."""
    def compose(self, sections: list[RenderedSection]) → str: ...

class FlagSource(Protocol):
    """Provides flag state from an external system (LaunchDarkly, Unleash, etc.)."""
    def get_flag(self, name: str, context: dict[str, Any]) → bool | None: ...
    def get_all_flags(self, context: dict[str, Any]) → dict[str, bool]: ...
```

These four protocols define the integration surface. A LangChain adapter, for example, would implement `PromptComposer` to produce a `ChatPromptTemplate`. A LaunchDarkly adapter would implement `FlagSource` to fetch flags from their API.

### Pluggy hook specifications (`plugins/hookspecs.py`)

```
Hook: pre_load(template_name, bucket) → str | None
  Called before template loading. Return modified name or None to proceed.

Hook: post_load(template_name, raw_content) → str
  Called after loading raw template. Return modified content.

Hook: pre_render(template, context, flags) → tuple[str, dict]
  Called before Jinja2 rendering. Return modified template/context.

Hook: post_render(rendered_text, metadata) → str
  Called after rendering. Return modified text (e.g., token counting, truncation).

Hook: on_flag_resolved(flag_name, value, resolution_tier, scope) → None
  Called after each flag resolution. For logging/observability.
```

### Plugin discovery

Plugins register via entry points in their `pyproject.toml`:

```toml
[project.entry-points."promptflags.plugins"]
langchain = "promptflags_langchain:LangChainPlugin"
launchdarkly = "promptflags_ld:LaunchDarklyFlagSource"
```

The `PluginManager` in `plugins/manager.py` discovers these at initialization via `importlib.metadata.entry_points(group="promptflags.plugins")`, instantiates them, and registers them with the pluggy `PluginManager`. Plugins can also be registered programmatically via `registry.register_plugin(MyPlugin())`.

---

## Public API design

The package offers two parallel interfaces — YAML-driven (declarative) and code-driven (programmatic) — that can be mixed freely. Both ultimately operate on the same `PromptRegistry` instance.

### YAML-driven API

```python
from promptflags import PromptRegistry

# Load from YAML config
registry = PromptRegistry.from_yaml("promptflags.yaml")

# Render a specific prompt with resolved flags
result = registry.render("guides", "coding_guide", context={
    "assistant_name": "CodeBot",
    "examples": [...],
})

# Override flags at render time
result = registry.render("guides", "coding_guide",
    context={"assistant_name": "CodeBot"},
    flags={"chain_of_thought": False, "json_output": True},
)

# Compose all prompts in a bucket into a single string
full_prompt = registry.compose_bucket("tool_prompts", context={...})

# Compose across multiple buckets in order
full_prompt = registry.compose(
    buckets=["system_context", "guides", "tool_prompts", "constraints", "output_formatting"],
    context={...},
)

# Inspect resolved flags
trace = registry.resolve_flags("guides", "coding_guide")
# → {"chain_of_thought": FlagResult(value=True, source="bucket:guides"),
#    "json_output": FlagResult(value=False, source="global")}
```

### Code-driven builder API

```python
from promptflags import Bucket, Prompt, Section, Flag, PromptRegistry

# Define flags
cot_flag = Flag("chain_of_thought", default=True)
json_flag = Flag("json_output", default=False)

# Define sections
reasoning = Section(
    id="reasoning_steps",
    template="Think step by step before answering.",
    flag="chain_of_thought",
    priority=10,
)
output_fmt = Section(
    id="output_format",
    template="Respond in {{ format }} format.",
    flag="json_output",
    priority=20,
    after=["reasoning_steps"],
)

# Build a prompt
coding = Prompt("coding_guide", sections=[reasoning, output_fmt])

# Build a bucket
guides = Bucket("guides", prompts=[coding], flags={"chain_of_thought": True})

# Assemble registry
registry = PromptRegistry(
    buckets=[guides],
    flags=[cot_flag, json_flag],
)

result = registry.render("guides", "coding_guide", context={"format": "JSON"})
```

### Fluent builder API

```python
from promptflags import PromptBuilder

prompt = (
    PromptBuilder("coding_guide")
    .in_bucket("guides")
    .section("identity", "You are a coding assistant.", priority=1)
    .section("reasoning", "Think step by step.", flag="chain_of_thought", priority=10)
    .section("format", "Respond in {{ fmt }}.", flag="json_output", priority=20, after=["reasoning"])
    .flag("chain_of_thought", default=True)
    .flag("json_output", default=False)
    .order("identity", before="reasoning")
    .build()
)

result = prompt.render(context={"fmt": "JSON"}, flags={"json_output": True})
```

### Decorator API for code-defined prompts

```python
from promptflags import prompt, section, bucket

@bucket("guides")
@prompt("coding_guide")
class CodingGuide:

    @section(id="identity", priority=1)
    def identity(self, ctx):
        return f"You are {ctx['role']}."

    @section(id="reasoning", flag="chain_of_thought", priority=10)
    def reasoning(self, ctx):
        return "Think step by step before answering."

    @section(id="format", flag="json_output", priority=20, after=["reasoning"])
    def output_format(self, ctx):
        return f"Respond in {ctx['format']} format."
```

The decorator API registers sections on the class, and the class is auto-registered with the global `PromptRegistry` when instantiated. Code-defined and YAML-defined prompts coexist in the same registry — code definitions take precedence for sections with the same `id`, enabling YAML configs to declare structure and flags while code provides dynamic section content.

---

## Suggested implementation phases

### Phase 1 — Core domain models and flag resolution (weeks 1–2)

Build the Pydantic v2 models (`Section`, `Prompt`, `Bucket`, `Flag`, `FlagOverrides`), the `PromptRegistry` skeleton, and the 4-tier flag resolver. Write YAML config schema and loader (PyYAML + Pydantic `model_validate`). Target: load a YAML config, resolve flags at any scope, and return boolean values with resolution traces. **This is the foundation everything else depends on.**

### Phase 2 — Jinja2 rendering engine (weeks 2–3)

Implement the `Environment` setup (PrefixLoader, StrictUndefined, trim/lstrip), register `feature_enabled()` and `env()` globals, build the macro library, and implement the rendering pipeline (load → resolve flags → inject context → render → post-process whitespace). Target: render a single prompt template with feature flags correctly toggling sections.

### Phase 3 — Section ordering (week 3)

Implement `ordering.py` using `graphlib.TopologicalSorter` with priority tiebreaking. Add constraint collection from all three config levels. Add `CycleError` handling with clear error messages. Target: given a set of active sections and constraints, produce a deterministic ordered list.

### Phase 4 — Builder and decorator APIs (weeks 3–4)

Implement the fluent `PromptBuilder`, the `@section`/`@prompt`/`@bucket` decorators, and the functional API (`render_prompt()`, `compose()`). Ensure code-defined prompts register into the same `PromptRegistry` as YAML-defined ones. Target: full parity between YAML and code APIs.

### Phase 5 — Plugin system (weeks 4–5)

Define Protocol interfaces, implement pluggy hook specifications, build the `PluginManager` with entry_point discovery. Ship a built-in default implementation for each Protocol (file-based loader, Jinja2 renderer, newline-join composer). Target: a third-party package can implement `FlagSource` or `PromptLoader` and register via entry points.

### Phase 6 — Polish, docs, and optional custom extension (weeks 5–6)

Implement the optional `{% feature %}...{% endfeature %}` Jinja2 extension tag. Write comprehensive documentation (quickstart, YAML reference, plugin guide). Add CLI tool for validating configs (`promptflags validate config.yaml`). Publish to PyPI.

---

## Key dependencies

The package has a deliberately small dependency footprint, split into required and optional:

**Required dependencies** include **Jinja2 ≥3.1** for template rendering with custom extensions, `trim_blocks`, and `StrictUndefined`; **PyYAML ≥6.0** for YAML config parsing; and **Pydantic ≥2.0** for config schema validation, domain model definitions, and `ConfigDict(extra="forbid")` strictness. These three are mature, widely-used, and low-risk.

**Optional dependencies** (declared as extras) include **pluggy ≥1.3** for the hook-based plugin system (only needed if using pre/post processing hooks), **ruamel.yaml ≥0.18** as an alternative YAML parser that preserves comments (useful for round-trip config editing tools), and **rich ≥13.0** for pretty-printing flag resolution traces and config validation errors.

**Development dependencies** include **pytest ≥7.0**, **ruff** for linting/formatting, **mypy** for type checking, **pytest-cov** for coverage, and **hatch** as the project manager.

**Explicitly avoided dependencies**: NetworkX (graphlib is sufficient), OmegaConf/Hydra (Pydantic v2 + PyYAML covers the config needs without adding framework-level complexity), and any LLM-specific library (the package must remain model-agnostic).

---

## Design decisions that deserve explicit rationale

**Why Pydantic v2 over dataclasses for domain models?** Pydantic provides YAML validation (`model_validate`), `extra="forbid"` for typo detection, discriminated unions for polymorphic config sections, and `model_dump()` for serialization — all critical for a config-heavy package. The ~2ms import overhead is negligible for a prompt management library.

**Why Protocol over ABC for plugin interfaces?** The package must snap into existing prompt systems (LangChain, Haystack, custom systems) without requiring those systems to import `promptflags`. Protocols enable structural subtyping — any class with matching methods works, zero coupling required. ABCs would force explicit inheritance, which is a non-starter for third-party integration.

**Why `Optional[bool] = None` as the "inherit" sentinel?** This is the pattern used by Flagsmith, Django-Waffle ("Unknown"), and Hydra's `MISSING`. It cleanly distinguishes three states: "explicitly True," "explicitly False," and "not set at this level — defer to parent." Using a separate sentinel class (like `MISSING`) was considered but adds complexity without benefit since flags are boolean.

**Why global function + macros over a custom Jinja2 extension as the primary approach?** Custom extensions require complex AST manipulation (`nodes.CallBlock`, parser stream manipulation) and break standard Jinja2 tooling/linters. The global function `feature_enabled()` is trivially testable, debuggable, and compatible with every Jinja2 tool. Macros add semantic sugar without non-standard syntax. The custom extension is offered as an opt-in for teams that want static analysis of flag usage.

**Why not use Hydra/OmegaConf for config management?** Hydra's composition model (Defaults List, Config Groups) is designed for ML experiment management, not library configuration. It imposes a specific directory structure and CLI override grammar that would constrain users. Pydantic v2 + PyYAML gives full control over merge semantics while keeping the dependency footprint lean.

---

## Conclusion

The `promptflags` package fills a genuine gap in the Python LLM ecosystem: no existing library offers declarative feature-flagging of prompt sections with scoped overrides, topological ordering, and bucket-based organization. The implementation plan above specifies a package that is **small but complete** — seven core entities, four protocol interfaces, and two parallel APIs (YAML and code) that converge on a single registry. The phased approach ensures the flag resolver and rendering engine ship first (the two features with no existing alternatives), while the plugin system and decorator API follow as the surface area for third-party integration. An engineer should be able to build Phase 1–3 (the critical path to a usable v0.1) in approximately three weeks.