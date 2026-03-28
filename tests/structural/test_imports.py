"""Structural tests for package imports and dependency flow.

Uses AST parsing to verify that the package's internal dependency rules
are maintained: code flows forward only through the layer hierarchy,
and the public API surface is complete.
"""

import ast
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src" / "prompt_flags"


def _get_imports_from_file(filepath: Path) -> list[str]:
    """Extract all import module paths from a Python file using AST parsing.

    Args:
        filepath: Path to the Python file.

    Returns:
        List of fully qualified module paths that are imported.
    """
    source = filepath.read_text()
    tree = ast.parse(source, filename=str(filepath))
    imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append(node.module)

    return imports


def _get_all_imports_in_package(subpackage: str) -> list[tuple[str, str]]:
    """Get all imports from all Python files in a subpackage.

    Args:
        subpackage: The subpackage directory name (e.g., "core", "config").

    Returns:
        List of (file_path, imported_module) tuples.
    """
    pkg_dir = PACKAGE_ROOT / subpackage
    if not pkg_dir.exists():
        return []

    results: list[tuple[str, str]] = []
    for py_file in sorted(pkg_dir.rglob("*.py")):
        relative = str(py_file.relative_to(PACKAGE_ROOT))
        for imp in _get_imports_from_file(py_file):
            results.append((relative, imp))

    return results


class TestPackageImports:
    """Verify package structure and import hygiene."""

    def test_top_level_imports(self) -> None:
        """All public API names are importable from prompt_flags."""
        from prompt_flags import (  # noqa: F401
            Bucket,
            Flag,
            FlagOverrides,
            FlagResult,
            FlagSource,
            OrderingConstraint,
            OrderingCycleError,
            PromptBuilder,
            PromptComposer,
            PromptLoader,
            PromptRegistry,
            PromptRenderer,
            RenderedSection,
            Section,
            UndefinedFlagError,
            bucket,
            compose,
            from_yaml,
            prompt,
            render_prompt,
            section,
        )

    def test_core_has_no_upstream_imports(self) -> None:
        """Verify core/ does not import from config/, rendering/, or api/."""
        forbidden_prefixes = [
            "prompt_flags.config",
            "prompt_flags.rendering",
            "prompt_flags.api",
        ]
        imports = _get_all_imports_in_package("core")

        violations: list[str] = []
        for filepath, module in imports:
            for prefix in forbidden_prefixes:
                if module.startswith(prefix):
                    violations.append(
                        f"{filepath} imports {module} (forbidden: core/ "
                        f"cannot import from {prefix})"
                    )

        assert violations == [], (
            "core/ has forbidden upstream imports:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_config_does_not_import_rendering_or_api(self) -> None:
        """Verify config/ only imports from core/ (and stdlib/third-party)."""
        forbidden_prefixes = [
            "prompt_flags.rendering",
            "prompt_flags.api",
        ]
        imports = _get_all_imports_in_package("config")

        violations: list[str] = []
        for filepath, module in imports:
            for prefix in forbidden_prefixes:
                if module.startswith(prefix):
                    violations.append(
                        f"{filepath} imports {module} (forbidden: config/ "
                        f"cannot import from {prefix})"
                    )

        assert violations == [], (
            "config/ has forbidden upstream imports:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_rendering_does_not_import_api(self) -> None:
        """Verify rendering/ does not import from api/."""
        forbidden_prefixes = [
            "prompt_flags.api",
        ]
        imports = _get_all_imports_in_package("rendering")

        violations: list[str] = []
        for filepath, module in imports:
            for prefix in forbidden_prefixes:
                if module.startswith(prefix):
                    violations.append(
                        f"{filepath} imports {module} (forbidden: rendering/ "
                        f"cannot import from {prefix})"
                    )

        assert violations == [], (
            "rendering/ has forbidden upstream imports:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_plugins_does_not_import_config_rendering_api(self) -> None:
        """Verify plugins/ only imports from core/ (and stdlib/third-party)."""
        forbidden_prefixes = [
            "prompt_flags.config",
            "prompt_flags.rendering",
            "prompt_flags.api",
        ]
        imports = _get_all_imports_in_package("plugins")

        violations: list[str] = []
        for filepath, module in imports:
            for prefix in forbidden_prefixes:
                if module.startswith(prefix):
                    violations.append(
                        f"{filepath} imports {module} (forbidden: plugins/ "
                        f"cannot import from {prefix})"
                    )

        assert violations == [], (
            "plugins/ has forbidden upstream imports:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_py_typed_marker_exists(self) -> None:
        """PEP 561 py.typed marker is present."""
        marker = PACKAGE_ROOT / "py.typed"
        assert marker.exists(), (
            f"PEP 561 py.typed marker not found at {marker}. "
            f"This is required for type checker support."
        )

    def test_all_subpackages_have_init(self) -> None:
        """Every subpackage directory has an __init__.py."""
        subpackages = ["core", "config", "rendering", "api", "plugins", "_bundled"]
        for pkg in subpackages:
            init = PACKAGE_ROOT / pkg / "__init__.py"
            assert init.exists(), (
                f"Missing __init__.py in {PACKAGE_ROOT / pkg}"
            )

    def test_no_circular_imports_in_core(self) -> None:
        """Verify core/ modules don't have circular import patterns.

        Specifically: models.py should not import from resolver, ordering,
        or registry. Those modules can import from models.
        """
        models_imports = _get_imports_from_file(PACKAGE_ROOT / "core" / "models.py")

        forbidden_modules = [
            "prompt_flags.core.resolver",
            "prompt_flags.core.ordering",
            "prompt_flags.core.registry",
        ]
        violations = [
            m for m in models_imports if m in forbidden_modules
        ]
        assert violations == [], (
            f"core/models.py has circular imports: {violations}"
        )

    def test_api_layer_imports_only_from_lower_layers(self) -> None:
        """Verify api/ imports only from core/, config/, rendering/, and plugins/."""
        allowed_internal_prefixes = [
            "prompt_flags.core",
            "prompt_flags.config",
            "prompt_flags.rendering",
            "prompt_flags.plugins",
            "prompt_flags.api",  # Self-imports are fine
        ]
        imports = _get_all_imports_in_package("api")

        violations: list[str] = []
        for filepath, module in imports:
            if not module.startswith("prompt_flags"):
                continue  # Skip stdlib/third-party
            allowed = any(module.startswith(p) for p in allowed_internal_prefixes)
            if not allowed:
                violations.append(
                    f"{filepath} imports {module} (not in allowed layers)"
                )

        assert violations == [], (
            "api/ has imports from unexpected layers:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    @pytest.mark.parametrize(
        "subpackage",
        ["core", "config", "rendering", "api", "plugins"],
    )
    def test_init_exports_match_public_api(self, subpackage: str) -> None:
        """Each subpackage __init__.py defines __all__."""
        init_file = PACKAGE_ROOT / subpackage / "__init__.py"
        source = init_file.read_text()
        tree = ast.parse(source, filename=str(init_file))

        has_all = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        has_all = True

        assert has_all, (
            f"{subpackage}/__init__.py does not define __all__. "
            f"Public exports should be explicit."
        )
