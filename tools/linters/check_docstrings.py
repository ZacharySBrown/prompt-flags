"""Check that all public functions and classes in src/prompt_flags/ have docstrings.

Agents rely on docstrings for understanding what code does, what parameters mean,
and what side effects to expect.

Usage:
    python -m tools.linters.check_docstrings
"""

import ast
import sys
from pathlib import Path

HARNESS_ROOT = Path(__file__).resolve().parents[2] / "src" / "prompt_flags"


def _is_public(name: str) -> bool:
    """Check if a name is public (doesn't start with underscore)."""
    return not name.startswith("_")


def _has_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> bool:
    """Check if a function or class node has a docstring."""
    if not node.body:
        return False
    first = node.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        return isinstance(first.value.value, str)
    return False


def _check_file(filepath: Path) -> list[str]:
    """Check a single file for missing docstrings on public interfaces."""
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    violations: list[str] = []
    relative_path = filepath.relative_to(HARNESS_ROOT.parent.parent)

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and _is_public(node.name) and not _has_docstring(node):
            violations.append(
                f"{relative_path}:{node.lineno}: Public class "
                f"'{node.name}' is missing a docstring. "
                f"Agents use docstrings for navigation. "
                f"See docs/design-docs/core-beliefs.md#6"
            )

        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and _is_public(node.name)
            and not _has_docstring(node)
        ):
            violations.append(
                f"{relative_path}:{node.lineno}: Public function "
                f"'{node.name}' is missing a docstring. "
                f"Agents use docstrings for navigation. "
                f"See docs/design-docs/core-beliefs.md#6"
            )

    return violations


def check() -> list[str]:
    """Run the docstring check and return violation messages."""
    violations: list[str] = []
    for py_file in sorted(HARNESS_ROOT.rglob("*.py")):
        violations.extend(_check_file(py_file))
    return violations


def main() -> int:
    """Entry point for the linter."""
    violations = check()
    if violations:
        print("Missing docstring violations found:")  # noqa: T201
        for v in violations:
            print(f"  {v}")  # noqa: T201
        return 1
    print("No missing docstring violations found.")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
