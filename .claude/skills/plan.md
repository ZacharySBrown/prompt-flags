# /plan — Create an Execution Plan from a Design Document

## Role
Before beginning, read `.claude/agents/architect.md` and adopt that role's persona,
constraints, and focus areas for this task.

You are decomposing a design document into an ordered execution plan with concrete tasks. Follow these steps precisely.

## Input

The user will reference a design document, either by name or path (e.g., `docs/design-docs/feature-name.md`).

## Process

### 1. Read the Design Document

- Read the referenced design doc in full
- Verify its status is approved or at least reviewed
- If the design doc is still "Draft" status, warn the staff engineer and ask if they want to proceed anyway

### 2. Read Architecture Context

- Read `docs/architecture/dependency-layers.md` for dependency rules
- Read `docs/architecture/domain-map.md` for existing modules
- Check `docs/exec-plans/active/` for conflicting in-progress plans

### 3. Decompose into Tasks

Break the design into ordered steps. Each task should:

- Be completable in a single focused session
- Have clear inputs (what files/modules to read) and outputs (what files to create/modify)
- Have explicit dependencies on other tasks
- Include a TDD checkpoint: what test to write first

Organize tasks by subpackage, bottom-up:
1. **Core first** — Pydantic models, registry, resolver, ordering
2. **Config** — YAML schemas, loader, defaults
3. **Rendering** — Jinja2 engine, extensions, filters
4. **API** — Builder, decorators, standalone functions
5. **Plugins** — Protocols, hooks, discovery
6. **Tests** — Integration and structural tests
7. **Docs** — Architecture and domain map updates

### 4. Create the Execution Plan

Create `docs/exec-plans/active/{plan-name}.md` using this template:

```markdown
# Execution Plan: {Feature Name}

## Design Doc
[{Feature Name}](../../design-docs/{feature-name}.md)

## Status
Active — {N} tasks remaining

## Task Breakdown

### Task 1: {Description}
- **Subpackage**: core
- **Depends on**: (none)
- **Files**: `src/prompt_flags/core/{file}.py`
- **TDD**: Write test for {what} first, then implement
- **Done when**: {concrete criterion}
- **Status**: [ ] pending

### Task 2: {Description}
- **Subpackage**: config
- **Depends on**: Task 1
- **Files**: `src/prompt_flags/config/{file}.py`
- **TDD**: Write test for {what} first, then implement
- **Done when**: {concrete criterion}
- **Status**: [ ] pending

... (continue for all tasks)

## Decision Log

| Decision | Date | Context |
|----------|------|---------|
| *(decisions made during execution go here)* | | |

## Risks

- Risk 1: {description} — mitigation: {approach}
- Risk 2: {description} — mitigation: {approach}
```

### 5. Create Beads Tasks

For each task in the plan:

```bash
bd create "{Task description}"
```

Set up dependencies:

```bash
bd link --blocks {task-id} {blocked-by-id}
```

If Beads is not set up, note this as a TODO and skip.

### 6. Project to GitHub Issues (Team Mode Only)

If dev mode is **team** and the parent epic doesn't already have a GH Issue:

1. Create GH Issue for the epic: `gh issue create --title "{Feature Name}" --label "epic" --body "Beads: {epic-id}. {summary}\n\nTasks: {count} beads tasks created."`
2. Update beads epic: `bd update {epic-id} --description "{original description} (GH#{number})"`

Only project the parent epic, not individual sub-tasks.

If dev mode is **solo**, skip this step.

### 7. Present for Approval

Present the plan to the staff engineer with:

- Total task count and estimated complexity
- Critical path (which tasks block the most others)
- First 2-3 tasks that can start immediately (no dependencies)
- Any risks or open questions
- Ask: "Does this plan look right? Should I adjust the task breakdown or ordering?"

## Rules

- Every task must have a TDD checkpoint
- Tasks must respect the dependency flow (build bottom-up: core → config → rendering → api)
- Keep tasks small enough to complete in one session
- Each task must have a clear "done when" criterion
- Flag any tasks that require staff engineer judgment
- Do NOT start implementation — this skill produces a plan only
- If the design doc has unresolved open questions, escalate before planning
