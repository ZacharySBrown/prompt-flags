"""Tests for the flag resolver."""

import pytest

from prompt_flags.core.models import Flag, FlagDefinitions, FlagScope, RuntimeOverrides
from prompt_flags.core.resolver import (
    UndefinedFlagError,
    resolve_all_flags,
    resolve_flag,
)


def _defs(**kwargs: bool) -> FlagDefinitions:
    """Helper to create FlagDefinitions from name=default pairs."""
    return FlagDefinitions(flags={k: Flag(name=k, default=v) for k, v in kwargs.items()})


def _scope(**kwargs: bool | None) -> FlagScope:
    """Helper to create FlagScope from name=value pairs."""
    return FlagScope(overrides=kwargs)


def _runtime(**kwargs: bool) -> RuntimeOverrides:
    """Helper to create RuntimeOverrides from name=value pairs."""
    return RuntimeOverrides(flags=kwargs)


class TestResolveFlag:
    """Tests for the resolve_flag function."""

    def test_global_default(self) -> None:
        result = resolve_flag("cot", _defs(cot=True), _scope(), _scope())
        assert result.value is True
        assert result.source == "global"
        assert result.name == "cot"

    def test_bucket_override(self) -> None:
        result = resolve_flag("cot", _defs(cot=True), _scope(cot=False), _scope())
        assert result.value is False
        assert result.source == "bucket"

    def test_prompt_override(self) -> None:
        result = resolve_flag("cot", _defs(cot=True), _scope(cot=False), _scope(cot=True))
        assert result.value is True
        assert result.source == "prompt"

    def test_runtime_override(self) -> None:
        result = resolve_flag(
            "cot", _defs(cot=True), _scope(), _scope(), runtime_overrides=_runtime(cot=False)
        )
        assert result.value is False
        assert result.source == "runtime"

    def test_runtime_beats_all(self) -> None:
        result = resolve_flag(
            "cot",
            _defs(cot=False),
            _scope(cot=False),
            _scope(cot=False),
            runtime_overrides=_runtime(cot=True),
        )
        assert result.value is True
        assert result.source == "runtime"

    def test_none_bucket_defers_to_global(self) -> None:
        result = resolve_flag("cot", _defs(cot=True), _scope(cot=None), _scope())
        assert result.value is True
        assert result.source == "global"

    def test_none_prompt_defers_to_bucket(self) -> None:
        result = resolve_flag("cot", _defs(cot=True), _scope(cot=False), _scope(cot=None))
        assert result.value is False
        assert result.source == "bucket"

    def test_undefined_flag_strict(self) -> None:
        with pytest.raises(UndefinedFlagError) as exc_info:
            resolve_flag("nonexistent", _defs(), _scope(), _scope(), strict=True)
        assert exc_info.value.flag_name == "nonexistent"

    def test_undefined_flag_non_strict(self) -> None:
        result = resolve_flag("nonexistent", _defs(), _scope(), _scope(), strict=False)
        assert result.value is False
        assert result.source == "default"


class TestResolveAllFlags:
    """Tests for resolve_all_flags."""

    def test_resolves_all(self) -> None:
        results = resolve_all_flags(_defs(cot=True, json=False), _scope(cot=False), _scope())
        assert results["cot"].value is False
        assert results["json"].value is False

    def test_resolves_with_runtime_overrides(self) -> None:
        results = resolve_all_flags(
            _defs(cot=True, json=False), _scope(), _scope(), runtime_overrides=_runtime(json=True)
        )
        assert results["cot"].value is True
        assert results["json"].value is True
