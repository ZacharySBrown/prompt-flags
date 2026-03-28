# /eval — Build an Evaluation Harness for a Package Feature

## Role
Before beginning, read `.claude/agents/operator.md` and adopt that role's persona,
constraints, and focus areas for this task.

You are creating an evaluation test suite for a specific package feature or subsystem. Follow these steps precisely.

## Input

The user will specify which feature to evaluate (e.g., "the flag resolver", "the config loader", "the rendering pipeline").

## Process

### 1. Analyze the Target

Read the feature code to understand:
- What inputs it accepts (Pydantic models)
- What outputs it produces
- What success looks like (correct output, proper error handling, etc.)
- What failure modes exist (invalid config, cycles in ordering, missing flags, etc.)

### 2. Design Evaluation Cases

Create a set of test cases organized by category:

- **Happy path**: Expected inputs → expected outputs
- **Edge cases**: Boundary conditions, empty inputs, maximum sizes
- **Failure modes**: Invalid inputs, malformed config, circular dependencies
- **Regression**: Known issues that were previously fixed

Each test case should specify:
- Input data (concrete, not abstract)
- Expected behavior (what the feature should do)
- Scoring criteria (how to grade the response)

### 3. Create Test Files

Create the evaluation harness in `tests/evals/{feature-name}/`:

```
tests/evals/{name}/
├── __init__.py
├── conftest.py          # Fixtures, mock data, shared setup
├── test_cases.py        # Test case definitions as Pydantic models
├── test_eval.py         # Pytest-based eval runner
└── rubric.md            # Human-readable scoring rubric
```

### 4. Present Summary

Tell the staff engineer:
- Number of test cases created, by category
- Scoring rubric summary
- How to run the evals: `uv run pytest tests/evals/{name}/ -v`
- Any test cases that need human-provided expected outputs

## Rules

- Test cases must use Pydantic models (Core Belief #4)
- Include at least 5 test cases per category (happy path, edge, failure)
- Results feed into `/quality` scores (Core Belief #7)
