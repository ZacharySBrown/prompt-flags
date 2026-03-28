# /design — Create a Design Document from an Idea

## Role
Before beginning, read `.claude/agents/architect.md` and adopt that role's persona,
constraints, and focus areas for this task.

You are creating a design document for a new feature or capability in the PromptFlags package. Follow these steps precisely.

## Input

The user will provide a feature idea, either as a brief description or a detailed request.

## Process

### 1. Research the Codebase

Before writing anything, understand what exists:

- Search `src/prompt_flags/` for related code, models, or modules
- Read `docs/architecture/ARCHITECTURE.md` for the package overview
- Read `docs/architecture/domain-map.md` for existing modules
- Read `docs/design-docs/index.md` for existing design docs
- Read `initial-spec.md` for the package specification
- Check `docs/exec-plans/active/` for in-progress work that might overlap

### 2. Create the Design Document

Create `docs/design-docs/{feature-name}.md` using this template:

```markdown
# {Feature Name}

## Status
Draft — awaiting staff engineer review

## Problem
What problem are we solving? Why now? What's the user impact?

## Context
What exists today? What constraints do we have? What related code/docs exist?
Reference specific files: `src/prompt_flags/...`, existing models, etc.

## Proposed Approach
How will we solve it? Include:
- Which subpackages are affected (core, config, rendering, api, plugins)
- New modules or modifications to existing ones
- Key Pydantic v2 models needed
- Integration points with existing code

## Alternatives Considered
What else did we consider? Why did we reject each alternative?
At least 2 alternatives with clear trade-off analysis.

## Acceptance Criteria
Concrete, testable criteria. Each should be verifiable by a test or review check.
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] ...

## Open Questions
What remains unresolved? Tag decisions that need staff engineer judgment.
- [ ] Question 1 — needs human decision because...
- [ ] Question 2 — blocked on...
```

### 3. Update the Design Doc Index

Add an entry to `docs/design-docs/index.md`:

```markdown
| {Feature Name} | Draft | — | {today's date} |
```

### 4. Create a Beads Epic

```bash
bd create --type epic "{Feature Name}"
```

If Beads is not set up, note this as a TODO and skip.

### 5. Project to GitHub Issues (Team Mode Only)

If dev mode is **team**:

1. Create GH Issue: `gh issue create --title "{Feature Name}" --label "epic" --body "Beads: {task-id}. {one-line summary from design doc}"`
2. Update beads task: `bd update {task-id} --description "{original description} (GH#{number})"`

If dev mode is **solo**, skip this step.

### 6. Present for Review

After creating the design doc, present a summary to the staff engineer:

- One-paragraph summary of the proposed approach
- Key architectural decisions that need approval
- Open questions requiring human judgment
- Ask: "Should I proceed to create an execution plan with `/plan`, or do you want to revise the design first?"

## Rules

- Always research the codebase BEFORE writing the design doc
- Proposed changes must respect the dependency flow (core → config → rendering → api)
- Reference specific files and line numbers when discussing existing code
- Flag any proposed changes that would require new dependencies (Core Belief #3: boring tech)
- If the feature is ambiguous, escalate to the staff engineer (Core Belief #8)
- Do NOT start implementation — this skill produces a design doc only
