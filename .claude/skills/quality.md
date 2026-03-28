# /quality — Run Quality Scoring Across All Subpackages

## Role
Before beginning, read `.claude/agents/operator.md` and adopt that role's persona,
constraints, and focus areas for this task.

You are generating quality scores for every subpackage in the PromptFlags package. Follow these steps precisely.

## Process

### 1. Run All Linters

Execute each check and capture results:

```bash
uv run ruff check . 2>&1
uv run ruff format --check . 2>&1
uv run pyright 2>&1
uv run python -m tools.linters.check_pydantic_boundaries 2>&1
uv run python -m tools.linters.check_no_print 2>&1
uv run python -m tools.linters.check_docstrings 2>&1
```

### 2. Run Test Suite

```bash
uv run pytest tests/ -v --tb=short 2>&1
```

Collect:
- Total tests, passed, failed, errors
- Per-directory breakdown (unit, integration, structural, evals)

### 3. Check Doc Freshness

For each subpackage in `src/prompt_flags/`:
- Find the most recent modification date of Python files
- Find the most recent modification date of corresponding docs
- Flag subpackages where code is newer than docs

### 4. Run Eval Harnesses

If eval tests exist in `tests/evals/`:

```bash
uv run pytest tests/evals/ -v 2>&1
```

Collect pass/fail rates per eval suite.

### 5. Score Each Subpackage

For each subpackage (core, config, rendering, api, plugins):

| Criterion | Weight | How to Score |
|-----------|--------|-------------|
| Lint compliance | 25% | Violations in this subpackage / total files |
| Type safety | 25% | Pyright errors in this subpackage |
| Test coverage | 25% | Test files exist for public modules |
| Doc freshness | 15% | Docs updated after code changes |
| Eval performance | 10% | Eval pass rate (if evals exist) |

Grade scale:
- **A**: 90-100% — Excellent
- **B**: 75-89% — Good
- **C**: 60-74% — Needs improvement
- **D**: 40-59% — Significant issues
- **F**: Below 40% — Failing
- **N/A**: No code in this subpackage yet

### 6. Update QUALITY_SCORE.md

Read the current `docs/QUALITY_SCORE.md`, then update it with new scores.

### 7. Flag Regressions

Compare with previous scores (if they exist in git history):
- Any subpackage that dropped a letter grade is a regression
- Report regressions prominently at the top of the output

### 8. Present Summary

Output:
- Overall project health (average grade)
- Regressions (if any)
- Top 3 areas needing improvement
- Specific action items for the lowest-scoring subpackages

## Rules

- Score every subpackage, even if it has no code (mark as N/A)
- Be honest — don't inflate scores
- Regressions are the highest-priority finding
- Always update `docs/QUALITY_SCORE.md` — this is the source of truth
- Suggest specific, actionable improvements (not vague "improve testing")
