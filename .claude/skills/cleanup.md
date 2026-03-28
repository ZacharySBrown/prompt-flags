# /cleanup — Entropy Management and Pattern Drift Detection

## Role
Before beginning, read `.claude/agents/operator.md` and adopt that role's persona,
constraints, and focus areas for this task.

You are scanning the codebase for pattern drift, stale docs, and tech debt. Follow these steps precisely.

## Process

### 1. Run Quality Scoring

First, get the current quality state by running the same checks as `/quality`:

```bash
uv run ruff check . 2>&1
uv run pyright 2>&1
uv run python -m tools.linters.check_pydantic_boundaries 2>&1
uv run python -m tools.linters.check_no_print 2>&1
uv run python -m tools.linters.check_docstrings 2>&1
uv run pytest tests/ -v --tb=short 2>&1
```

### 2. Detect Pattern Drift

Scan for inconsistencies across the codebase:

- **Duplicate code**: Similar functions or classes across modules
- **Inconsistent naming**: Modules that don't follow the naming conventions in CLAUDE.md
- **Mixed patterns**: Some modules using one approach, others using a different one for the same thing
- **Orphaned code**: Modules with no imports (dead code)
- **Oversized files**: Files exceeding 300 lines

### 3. Check Doc Freshness

For every file in `docs/`:
- Check if it references files/modules that no longer exist
- Check if it describes behavior that has changed
- Check if exec plans in `docs/exec-plans/active/` are actually still active
- Check if completed plans should be moved to `docs/exec-plans/completed/`

### 4. Identify Tech Debt

Cross-reference with `docs/exec-plans/tech-debt-tracker.md`:
- Are listed items still relevant?
- Are there new debt items not yet tracked?
- Have any items been resolved but not marked?

### 5. Report Findings

Produce a structured report:

```markdown
## Cleanup Report

### Pattern Drift
- {file}: {description of inconsistency}
- ...

### Stale Documentation
- {doc file}: {what's stale and why}
- ...

### New Tech Debt
- {description}: {affected files} — suggested priority: P{0-3}
- ...

### Resolved Tech Debt
- {description}: appears to be fixed, remove from tracker
- ...

### Proposed Fixes
1. **{Fix title}**: {what to change, which files} — estimated effort: {small/medium/large}
2. ...
```

### 6. Create Beads Issues

For each finding:

```bash
bd create "{Fix title}: {brief description}"
```

If Beads is not set up, list the issues that should be created.

### 7. Project to GitHub Issues (Team Mode Only)

If dev mode is **team**, project P0-P1 findings:

1. For each P0-P1 beads issue created: `gh issue create --title "{Fix title}" --label "bug" --body "Beads: {task-id}. {description}"`
2. Update beads task: `bd update {task-id} --description "{original description} (GH#{number})"`

If dev mode is **solo** or findings are P2+, skip this step.

### 8. Propose Fix PRs

For small, self-contained fixes:
- Describe the exact changes needed
- Offer to implement them as separate, focused PRs
- Each fix PR should be reviewable independently

Ask the staff engineer: "I found {N} issues. Should I create fix PRs for the small ones, or just track everything as Beads tasks?"

## Rules

- Focus on mechanical, objective drift — not subjective style preferences
- Prioritize findings by impact on developer productivity
- Small fixes (typos, stale references) can be batched
- Large changes (refactors, architectural shifts) need design docs first
- Always update `docs/exec-plans/tech-debt-tracker.md` with new findings
- Don't fix things silently — report first, then fix with approval
