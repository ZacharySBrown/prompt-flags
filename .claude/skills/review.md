# /review — Specialized Agent Review

## Role
Before beginning, read `.claude/agents/reviewer.md` and adopt that role's persona,
constraints, and focus areas for this task.

You are performing a structured code review. Run all checks, classify findings as CRITICAL or ADVISORY, and produce a clear checklist. Follow these steps precisely.

## Input

The user will indicate what to review — typically recent changes, a specific file, or a PR.

## Process

### 1. Identify Changed Files

Determine what to review:
- If given a file path, review that file
- If asked to review recent changes, run `git diff` and `git diff --cached` to find changed files
- If given a PR number, use `gh pr diff {number}` to get the changes

### 2. Run All Custom Linters

Run each linter and collect results:

```bash
uv run python -m tools.linters.check_pydantic_boundaries
uv run python -m tools.linters.check_no_print
uv run python -m tools.linters.check_docstrings
```

Also run:
```bash
uv run ruff check .
uv run pyright
```

### 3. Check Test Coverage

For each changed file in `src/prompt_flags/`:
- Determine the corresponding test file in `tests/`
- Check if tests exist for new/modified public functions
- Flag any new code without corresponding tests

### 4. Check Doc Freshness

For changed files:
- If behavior changed, check if related docs in `docs/` were updated
- Check if `docs/architecture/ARCHITECTURE.md` needs updating
- Check if `docs/architecture/domain-map.md` needs updating

### 5. Produce Review Checklist

Format the review as a structured checklist with two sections:

```markdown
## Review Results

### CRITICAL (blocks merge)

These must be fixed before merging:

- [ ] **Missing tests**: {file} — new public function `{name}` has no tests
- [ ] **Type error**: {description from pyright}
- [ ] **Pydantic boundary**: {file}:{line} — {description}
- [ ] **Print in library code**: {file}:{line} — use exception/return instead

### ADVISORY (suggest, don't block)

These are recommendations but won't block merge:

- [ ] **Style**: {description}
- [ ] **Doc freshness**: {file} changed but docs not updated
- [ ] **Naming**: {description}

### Summary

- Critical issues: {count}
- Advisory issues: {count}
- Verdict: **PASS** / **FAIL** (fail if any critical issues)
```

### 6. Post to PR (Team Mode Only)

If dev mode is **team** and reviewing a PR:

```bash
gh pr comment {number} --body "{review checklist from step 5}"
```

If dev mode is **solo**, the checklist is presented in terminal only.

## Classification Rules

### CRITICAL (blocks merge)
- Missing tests for new public functions/classes
- Pyright type errors
- Pydantic boundary violations (raw dicts in public API)
- Print statements in library code
- Security issues (hardcoded secrets, injection, etc.)
- Backward dependency imports (e.g., core importing from config)

### ADVISORY (suggest, don't block)
- Ruff style/formatting issues (auto-fixable)
- Missing or stale documentation
- Naming convention deviations
- File size over 300 lines
- Missing docstrings on internal (private) functions

## Rules

- Always run ALL checks — don't skip any
- Be specific: include file paths, line numbers, function names
- For each critical issue, include a concrete remediation suggestion
- The staff engineer can override critical issues — note this in the summary
- If there are zero critical issues, the verdict is PASS
- Do NOT fix issues — only report them. The implementer fixes.
