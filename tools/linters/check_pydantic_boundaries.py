"""Check that public functions in the prompt_flags public API use Pydantic models at boundaries.

Functions in core/ and api/ that form the public interface must use Pydantic models
(not raw dicts, Any, or untyped parameters) for their inputs and return types.

Usage:
    python -m tools.linters.check_pydantic_boundaries
"""

import ast
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src" / "prompt_flags"

# Subpackages whose public functions must use typed parameters
BOUNDARY_PACKAGES = ["api", "core"]

# Types that are not acceptable at public boundaries
FORBIDDEN_ANNOTATIONS = {"dict", "Dict", "Any"}


def _is_public(name: str) -> bool:
    """Check if a name is public (doesn't start with underscore)."""
    return not name.startswith("_")


def _annotation_to_str(node: ast.expr | None) -> str:
    """Convert an AST annotation node to a string representation."""
    if node is None:
        return ""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_annotation_to_str(node.value)}.{node.attr}"
    if isinstance(node, ast.Subscript):
        return f"{_annotation_to_str(node.value)}[{_annotation_to_str(node.slice)}]"
    if isinstance(node, ast.Constant):
        return str(node.value)
    if isinstance(node, ast.Tuple):
        return ", ".join(_annotation_to_str(e) for e in node.elts)
    if isinstance(node, ast.BinOp):
        return f"{_annotation_to_str(node.left)} | {_annotation_to_str(node.right)}"
    return ast.dump(node)


def _check_annotation(annotation_str: str) -> str | None:
    """Check if an annotation uses a forbidden type. Returns the forbidden type or None."""
    for forbidden in FORBIDDEN_ANNOTATIONS:
        if forbidden in annotation_str.split("[")[0].split(","):
            return forbidden
        if annotation_str == forbidden:
            return forbidden
    return None


def check() -> list[str]:
    """Run the Pydantic boundary check and return violation messages."""
    violations: list[str] = []

    for pkg in BOUNDARY_PACKAGES:
        pkg_dir = PACKAGE_ROOT / pkg
        if not pkg_dir.exists():
            continue

        for py_file in sorted(pkg_dir.rglob("*.py")):
            try:
                source = py_file.read_text()
                tree = ast.parse(source, filename=str(py_file))
            except (SyntaxError, UnicodeDecodeError):
                continue

            relative_path = py_file.relative_to(PACKAGE_ROOT.parent.parent)

            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if not _is_public(node.name):
                    continue

                # Check for missing return annotation
                if node.returns is None and node.name != "__init__":
                    violations.append(
                        f"{relative_path}:{node.lineno}: Public function "
                        f"'{node.name}' has no return type annotation. "
                        f"Public API functions must use typed parameters."
                    )
                    continue

                # Check return type for forbidden types
                if node.returns is not None:
                    ret_str = _annotation_to_str(node.returns)
                    forbidden = _check_annotation(ret_str)
                    if forbidden:
                        violations.append(
                            f"{relative_path}:{node.lineno}: Public function "
                            f"'{node.name}' returns '{forbidden}'. "
                            f"Use a Pydantic model instead."
                        )

                # Check parameter annotations
                for arg in node.args.args:
                    if arg.arg in ("self", "cls"):
                        continue
                    if arg.annotation is None:
                        violations.append(
                            f"{relative_path}:{node.lineno}: Public function "
                            f"'{node.name}' parameter '{arg.arg}' has no type "
                            f"annotation. Public API functions must use typed parameters."
                        )
                    else:
                        ann_str = _annotation_to_str(arg.annotation)
                        forbidden = _check_annotation(ann_str)
                        if forbidden:
                            violations.append(
                                f"{relative_path}:{node.lineno}: Public function "
                                f"'{node.name}' parameter '{arg.arg}' uses "
                                f"'{forbidden}'. Use a Pydantic model instead."
                            )

    return violations


def main() -> int:
    """Entry point for the linter."""
    violations = check()
    if violations:
        print("Pydantic boundary violations found:")  # noqa: T201
        for v in violations:
            print(f"  {v}")  # noqa: T201
        return 1
    print("No Pydantic boundary violations found.")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main())
