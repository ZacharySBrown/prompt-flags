# /scaffold — Create a New Module in a Subpackage

## Role
Before beginning, read `.claude/agents/engineer.md` and adopt that role's persona,
constraints, and focus areas for this task.

You are creating a new module within an existing subpackage, with test stubs and doc placeholders. Follow these steps precisely.

## Input

The user will provide a module name, target subpackage, and brief description (e.g., "resolver in core — 4-tier flag resolution engine").

## Process

### 1. Validate the Module Name

- Must be snake_case
- Must not conflict with existing modules in the target subpackage
- Target subpackage must be one of: `core`, `config`, `rendering`, `api`, `plugins`

### 2. Create the Module

Create the module in the appropriate subpackage:

```python
# src/prompt_flags/{subpackage}/{module}.py
"""Brief description of the module."""

from pydantic import BaseModel  # if defining models


class {ClassName}(BaseModel):
    """Docstring describing the class."""
    pass
```

### 3. Create Test Stubs

```python
# tests/unit/test_{subpackage}_{module}.py
"""Tests for {subpackage}/{module}."""


def test_{module}_placeholder():
    """Verify the module can be imported."""
    from prompt_flags.{subpackage}.{module} import {ClassName}
    assert {ClassName} is not None
```

### 4. Update Documentation

**Update `docs/architecture/domain-map.md`** if adding a new module to the subpackage table.

### 5. Verify

Run all checks to ensure the new module is clean:

```bash
uv run ruff check .
uv run pyright
uv run pytest tests/ -v
uv run python -m tools.linters.check_pydantic_boundaries
uv run python -m tools.linters.check_no_print
uv run python -m tools.linters.check_docstrings
```

### 6. Create Beads Task

```bash
bd create "Implement {subpackage}/{module}: {brief description}"
```

If Beads is not set up, note this as a TODO.

### 7. Project to GitHub Issues (Team Mode Only)

If dev mode is **team** and the task is P0-P1:

1. Create GH Issue: `gh issue create --title "Implement {module}" --label "feature" --body "Beads: {task-id}. {brief description}"`
2. Update beads task description to include `GH#{number}`

If dev mode is **solo** or priority is P2+, skip this step.

### 8. Present Summary

Tell the staff engineer:
- What files were created (list all)
- What docs were updated
- How to start implementing: "Pick up the Beads task and start with tests"
- Suggest running `/plan` to decompose the implementation into tasks

## Rules

- Follow the exact module naming conventions (snake_case files, PascalCase classes)
- Every module must have a module-level docstring
- Every public class must have a docstring
- Models must use Pydantic v2 BaseModel
- Test stubs must actually pass (not just be placeholders with `pass`)
- Run all verification checks before presenting results
- Do NOT implement business logic — create the skeleton only
