# Core Beliefs

These are the golden principles that govern how agents operate in this repository. They are non-negotiable unless explicitly overridden by the staff engineer with a recorded decision.

## 1. Docs first, always

Plan before build. Every feature starts as a design doc or execution plan. Update plans as work progresses. Close features formally. The `/design` and `/plan` skills enforce this workflow.

## 2. Tests prove correctness

No feature or fix is complete without tests. TDD where possible: write the test first, watch it fail, then implement. Everything is tested, reviewed, and vetted before merge. The `/review` skill checks test coverage.

## 3. Boring tech by default

Prefer well-documented, stable libraries. Agents reason better about boring tech — there's more training data, more examples, more Stack Overflow answers. Novel dependencies need explicit justification in a decision record (`docs/design-docs/decisions/`).

## 4. Pydantic at all boundaries

All public API functions, config schemas, and domain models use Pydantic v2 models. No raw dicts crossing boundaries. This gives consumers type information, validation, and serialization for free. Enforced by `tools/linters/check_pydantic_boundaries.py`.

## 5. No print() in library code

Library code never prints to stdout. Use exceptions for errors, return values for results, and logging (if needed) via the standard `logging` module. Enforced by `tools/linters/check_no_print.py`.

## 6. Docstrings on public interfaces

All public functions, classes, and methods must have docstrings. Users and tools rely on these for understanding what code does, what parameters mean, and what side effects to expect. Enforced by `tools/linters/check_docstrings.py`.

## 7. Evals inform development

Evaluation results feed directly into the package being built. Development is eval-driven: if a feature doesn't work reliably, the implementation needs to change. The `/eval` skill creates evaluation harnesses.

## 8. Escalate ambiguity

Agents escalate ambiguous decisions to the staff engineer rather than guessing. Judgment calls are human. When an agent encounters a decision with no clear right answer, it presents options with trade-offs and asks for direction. This is a feature, not a limitation.
