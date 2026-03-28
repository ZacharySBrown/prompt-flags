"""Check that library code in src/prompt_flags/ does not use print().

Library code should raise exceptions or return values, not print to stdout.

Usage:
    python -m tools.linters.check_no_print
"""

import ast
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src" / "prompt_flags"


def _check_file(filepath: Path) -> list[str]:
    """Check a single file for print() calls."""
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, UnicodeDecodeError):
        return []

    violations: list[str] = []
    relative_path = filepath.relative_to(PACKAGE_ROOT.parent.parent)

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ):
            violations.append(
                f"{relative_path}:{node.lineno}: Library code should not use `print()`. "
                f"Raise an exception or return a value instead."
            )

    return violations


def check() -> list[str]:
    """Run the no-print check and return violation messages."""
    violations: list[str] = []
    for py_file in sorted(PACKAGE_ROOT.rglob("*.py")):
        violations.extend(_check_file(py_file))
    return violations


def main() -> int:
    """Entry point for the linter."""
    violations = check()
    if violations:
        print("Print statement violations found:")  # noqa: T201
        for v in violations:
            print(f"  {v}")  # noqa: T201
        return 1
    print("No print statement violations found.")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
