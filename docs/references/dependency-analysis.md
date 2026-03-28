# Dependency Analysis Tools

Tooling to analyze, track, and manage dependencies between prompts, sections,
and flags across an entire `PromptRegistry`.

## Overview

The dependency analysis system has two layers:

1. **Dependency Graph** (`core/dependency_graph.py`) — a directed graph model
   that maps all relationships between flags, sections, prompts, and buckets.
2. **Analyzer Tools** (`tools/analyzers/`) — five CLI-runnable tools that query
   the graph to surface insights, gaps, and conflicts.

```
┌─────────────────────────────────────────────┐
│              PromptRegistry                 │
│  (buckets, flags, ordering constraints)     │
└──────────────────┬──────────────────────────┘
                   │ build_from_registry()
                   ▼
┌─────────────────────────────────────────────┐
│            DependencyGraph                  │
│  Nodes: Flag, Section, Prompt, Bucket       │
│  Edges: uses, contains, overrides, ordered  │
└──────────────────┬──────────────────────────┘
                   │
      ┌────────────┼────────────┬──────────────┬──────────────┐
      ▼            ▼            ▼              ▼              ▼
 flag_impact  gap_analysis  unused_flags  dep_trace  conflict_detector
```

---

## Dependency Graph Model

### Node Kinds

| Kind | Represents | ID Format |
|------|-----------|-----------|
| `FLAG` | A feature flag definition | `flag_name` |
| `SECTION` | A section within a prompt | `section_id` (scope: `bucket/prompt`) |
| `PROMPT` | A prompt document | `prompt_name` (scope: `bucket`) |
| `BUCKET` | A named bucket | `bucket_name` |

### Edge Kinds

| Edge | From → To | Meaning |
|------|-----------|---------|
| `BUCKET_CONTAINS_PROMPT` | Bucket → Prompt | Prompt belongs to bucket |
| `PROMPT_CONTAINS_SECTION` | Prompt → Section | Section belongs to prompt |
| `SECTION_USES_FLAG` | Section → Flag | Section is controlled by flag |
| `BUCKET_OVERRIDES_FLAG` | Bucket → Flag | Bucket has an override for flag |
| `PROMPT_OVERRIDES_FLAG` | Prompt → Flag | Prompt has an override for flag |
| `SECTION_ORDERED_BEFORE` | Section → Section | Ordering constraint |

### Building a Graph

```python
from prompt_flags.core.dependency_graph import build_from_registry

# From an existing registry
graph = build_from_registry(registry)

# Or from raw data
from prompt_flags.core.dependency_graph import build_dependency_graph
graph = build_dependency_graph(buckets, flags, constraints)
```

### Querying the Graph

```python
from prompt_flags.core.dependency_graph import NodeKind

# Find a specific node
flag_node = graph.get_node(NodeKind.FLAG, "chain_of_thought")

# Direct dependents (what depends on this node?)
dependents = graph.dependents_of(flag_node)

# Direct dependencies (what does this node depend on?)
deps = graph.dependencies_of(prompt_node)

# Transitive (full reachability)
all_affected = graph.transitive_dependents(flag_node)
all_deps = graph.transitive_dependencies(prompt_node)

# Filter by kind
all_flags = graph.nodes_of_kind(NodeKind.FLAG)
all_sections = graph.nodes_of_kind(NodeKind.SECTION)
```

---

## Analyzer Tools

All tools can be run from the CLI or imported as library functions.

### 1. Flag Impact

**Question:** "What happens if I toggle flag X?"

Shows every section controlled by a flag, plus which prompts and buckets
override it.

```bash
uv run python -m tools.analyzers.flag_impact config.yaml chain_of_thought
```

```python
from tools.analyzers.flag_impact import flag_impact, format_impact_report

result = flag_impact(registry, "chain_of_thought")
# result = {
#     "sections": [{"id": "reasoning_steps", "scope": "guides/coding_guide", ...}],
#     "prompts":  [{"id": "coding_guide", "scope": "guides", ...}],
#     "buckets":  [{"id": "guides", ...}],
# }
print(format_impact_report("chain_of_thought", result))
```

**Example output:**

```
Flag Impact Report: chain_of_thought
==================================================

Sections controlled by 'chain_of_thought' (2):
  - reasoning_steps (scope: guides/coding_guide)
  - analysis_framework (scope: guides/analysis_guide)

Prompts that override 'chain_of_thought' (0):

Buckets that override 'chain_of_thought' (1):
  - guides

Total affected entities: 3
```

---

### 2. Gap Analysis

**Question:** "Which prompts are missing explicit flag overrides?"

Reports every bucket and prompt that inherits a flag value from a parent
scope instead of declaring its own override. Includes per-flag coverage
percentages.

```bash
uv run python -m tools.analyzers.gap_analysis config.yaml
```

```python
from tools.analyzers.gap_analysis import gap_analysis, format_gap_report

report = gap_analysis(registry)
print(format_gap_report(report))

# Programmatic access
for gap in report.gaps:
    print(f"{gap.flag_name} @ {gap.bucket_name}/{gap.prompt_name}"
          f" → inherits {gap.resolved_value} from {gap.resolved_source}")

# Coverage stats
for flag_name, stats in report.coverage.items():
    print(f"{flag_name}: bucket={stats['bucket_coverage_pct']}%"
          f" prompt={stats['prompt_coverage_pct']}%")
```

**Example output:**

```
Flag Override Gap Analysis
==================================================
Flags: 5  |  Buckets: 2  |  Prompts: 3

Coverage Summary:
--------------------------------------------------
  Flag                       Bucket %  Prompt %
  ------------------------- ---------- ----------
  chain_of_thought               50.0%       0.0%
  few_shot_examples              50.0%       0.0%
  json_output                     0.0%       0.0%
  safety_guardrails               0.0%       0.0%
  verbose_instructions            0.0%      33.3%

Bucket-Level Gaps (8):
--------------------------------------------------
  [chain_of_thought] bucket 'tool_prompts' → inherits True from global
  [json_output] bucket 'guides' → inherits False from global
  ...

Prompt-Level Gaps (13):
--------------------------------------------------
  [chain_of_thought] prompt 'guides/coding_guide' → inherits True from bucket
  [chain_of_thought] prompt 'guides/analysis_guide' → inherits True from bucket
  ...
```

**Understanding the gap report:**

- A **bucket-level gap** means a flag has no override at the bucket level —
  it falls through to the global default.
- A **prompt-level gap** means a flag has no override at the prompt level —
  it falls through to the bucket override (or global default if the bucket
  also has no override).
- **Coverage percentage** shows what fraction of scopes have explicit overrides.
  100% means every bucket/prompt explicitly declares a value for that flag.

---

### 3. Unused Flags

**Question:** "Which flags are defined but never actually used by a section?"

Finds flags that exist in the registry but no section references them via
the `flag` field. These may be dead configuration.

```bash
uv run python -m tools.analyzers.unused_flags config.yaml
```

```python
from tools.analyzers.unused_flags import find_unused_flags, format_unused_report

unused = find_unused_flags(registry)
print(format_unused_report(unused))

for flag in unused:
    print(f"{flag.name}: default={flag.default}, has_overrides={flag.has_overrides}")
```

**Example output:**

```
Unused Flags (1)
==================================================
  - verbose_instructions (default=False) (has overrides)

These flags are defined but no section references them via the 'flag' field.
```

---

### 4. Dependency Trace

**Question:** "What is the full dependency chain for a specific prompt?"

Shows all sections, flags used, prompt-level overrides, bucket-level overrides,
and ordering constraints for a single prompt.

```bash
uv run python -m tools.analyzers.dependency_trace config.yaml guides coding_guide
```

```python
from tools.analyzers.dependency_trace import trace_prompt_dependencies, format_trace_report

trace = trace_prompt_dependencies(registry, "guides", "coding_guide")
print(format_trace_report(trace))

# Programmatic access
for section in trace.sections:
    print(f"  {section['id']} — flag: {section['flag'] or 'always on'}")
print(f"Flags used: {trace.flags_used}")
print(f"Prompt overrides: {trace.flags_overridden}")
print(f"Bucket overrides: {trace.bucket_flag_overrides}")
```

**Example output:**

```
Dependency Trace: guides/coding_guide
==================================================

Sections (3):
  - reasoning_steps [flag: chain_of_thought]
  - worked_example [flag: few_shot_examples]
  - style_constraints [flag: safety_guardrails]

Flags used by sections (3):
  - chain_of_thought
  - few_shot_examples
  - safety_guardrails

Prompt-level flag overrides (0):
  (none)

Bucket-level flag overrides (2):
  - chain_of_thought
  - few_shot_examples

Ordering constraints (1):
  - reasoning_steps → worked_example (section_ordered_before)
```

---

### 5. Conflict Detector

**Question:** "Are there any redundant or contradictory flag overrides?"

Detects four types of issues:

| Conflict Kind | Description |
|--------------|-------------|
| `redundant_bucket_override` | Bucket overrides a flag to the same value as the global default |
| `redundant_prompt_override` | Prompt overrides a flag to the same value as the effective bucket value |
| `should_be_bucket_override` | All prompts in a bucket override the same flag to the same value |
| `undefined_flag_override` | A bucket or prompt overrides a flag that isn't defined |

```bash
uv run python -m tools.analyzers.conflict_detector config.yaml
```

```python
from tools.analyzers.conflict_detector import detect_conflicts, format_conflict_report

report = detect_conflicts(registry)
print(format_conflict_report(report))

# Filter by kind
redundant = [c for c in report.conflicts if c.kind == "redundant_bucket_override"]
```

**Example output:**

```
Flag Conflict Report (2 issues)
==================================================

Redundant Bucket Overrides (1):
--------------------------------------------------
  - Bucket 'guides' overrides 'chain_of_thought' to True, which matches the global default

Should Be Bucket-Level Overrides (1):
--------------------------------------------------
  - All 2 prompts in bucket 'guides' override 'json_output' to False — consider a bucket-level override instead
```

---

## Walkthrough: Full Analysis of a Config

Here's a complete example using the `sample_config.yaml` fixture:

```python
from prompt_flags.api.functional import from_yaml
from tools.analyzers.flag_impact import flag_impact, format_impact_report
from tools.analyzers.gap_analysis import gap_analysis, format_gap_report
from tools.analyzers.unused_flags import find_unused_flags, format_unused_report
from tools.analyzers.dependency_trace import trace_prompt_dependencies, format_trace_report
from tools.analyzers.conflict_detector import detect_conflicts, format_conflict_report

# Load a registry from YAML
registry = from_yaml("tests/fixtures/sample_config.yaml")

# 1. What does chain_of_thought affect?
impact = flag_impact(registry, "chain_of_thought")
print(format_impact_report("chain_of_thought", impact))

# 2. Where are flag overrides missing?
gaps = gap_analysis(registry)
print(format_gap_report(gaps))

# 3. Any dead flags?
unused = find_unused_flags(registry)
print(format_unused_report(unused))

# 4. Trace a specific prompt
trace = trace_prompt_dependencies(registry, "guides", "coding_guide")
print(format_trace_report(trace))

# 5. Any config smells?
conflicts = detect_conflicts(registry)
print(format_conflict_report(conflicts))
```

Or run them all from the CLI:

```bash
uv run python -m tools.analyzers.flag_impact tests/fixtures/sample_config.yaml chain_of_thought
uv run python -m tools.analyzers.gap_analysis tests/fixtures/sample_config.yaml
uv run python -m tools.analyzers.unused_flags tests/fixtures/sample_config.yaml
uv run python -m tools.analyzers.dependency_trace tests/fixtures/sample_config.yaml guides coding_guide
uv run python -m tools.analyzers.conflict_detector tests/fixtures/sample_config.yaml
```

---

## Architecture Notes

- The `DependencyGraph` lives in `core/` because it depends only on core models.
  It uses `dataclass` (not Pydantic) since it's mutable internal state, not a
  public API boundary.
- The analyzer tools live in `tools/` (not `src/`) — they're development tooling,
  not part of the library's public API.
- All analyzers accept a `PromptRegistry` and return structured dataclasses, making
  them composable and testable without I/O.
- Graph traversal uses iterative DFS (no recursion) to handle arbitrary depth safely.
