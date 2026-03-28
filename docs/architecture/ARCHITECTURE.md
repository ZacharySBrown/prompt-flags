# Architecture

## Overview

PromptFlags is a Python package that manages named prompt sections across multiple buckets, enables/disables them via a 3-tier feature-flag hierarchy, resolves ordering via topological sort, and plugs into any existing prompt system through Protocol-based adapters.

## Package Structure

```
src/prompt_flags/
├── core/           # Domain models, PromptRegistry, flag resolver, section ordering
├── config/         # YAML config schemas, layered config loader, defaults
├── rendering/      # Jinja2 environment, custom extensions, filters
├── api/            # Fluent builder, decorators, standalone functions
├── plugins/        # Protocol interfaces, pluggy hooks, plugin discovery
└── _bundled/       # Default Jinja2 macros and templates
```

## Dependency Flow

```
core → config → rendering → api
                    ↑
                plugins (cross-cutting)
```

- **core** has no internal dependencies — pure domain models and algorithms
- **config** imports from core (models for validation)
- **rendering** imports from core (models, registry) and config (loader)
- **api** imports from all lower packages to provide the public interface
- **plugins** defines Protocol interfaces that any package can implement

## Core Abstractions

Seven domain entities form the backbone, each as a Pydantic v2 model:

| Entity | Purpose |
|--------|---------|
| **Section** | Atomic prompt block, independently feature-flagged |
| **Prompt** | Groups Sections into a logical prompt document |
| **Bucket** | Named category containing related Prompts |
| **Flag** | Feature toggle with default value |
| **FlagOverrides** | 3-tier override chain: global → bucket → prompt |
| **OrderingConstraint** | Relative ordering relation between sections |
| **PromptRegistry** | Central coordinator: holds all entities, resolves flags, renders |

Relationships: `PromptRegistry 1──* Bucket 1──* Prompt 1──* Section`

## Key Algorithms

### Flag Resolution (4-tier precedence)

1. **Runtime override** — passed at render time (highest priority)
2. **Prompt-level override** — declared in prompt config
3. **Bucket-level override** — declared in bucket config
4. **Global default** — flag's default value (lowest priority)

### Section Ordering

Combines explicit priority values with relative ordering constraints via `graphlib.TopologicalSorter` with priority-based tiebreaking.

## Public API

Two parallel interfaces that share a single `PromptRegistry`:

- **YAML-driven**: `PromptRegistry.from_yaml("promptflags.yaml")` → `registry.render(...)`
- **Code-driven**: `PromptBuilder`, `@section`/`@prompt`/`@bucket` decorators, standalone functions

## Plugin System

Protocol-based interfaces for zero-coupling integration:

| Protocol | Purpose |
|----------|---------|
| `PromptLoader` | Load templates from custom backends |
| `PromptRenderer` | Custom rendering engines |
| `PromptComposer` | Assemble sections into final output |
| `FlagSource` | External flag providers (LaunchDarkly, etc.) |

Plugins register via `pyproject.toml` entry points or programmatically.

## Further Reading

- [Core Beliefs](../design-docs/core-beliefs.md) — operating principles
- [Initial Spec](../../initial-spec.md) — full package specification
- [Design Docs](../design-docs/index.md) — feature design documents
