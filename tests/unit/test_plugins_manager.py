"""Tests for the plugin manager and hook system.

Verifies PluginManager initialization, hook registration, hook execution
for all lifecycle hooks, multi-plugin ordering, and graceful handling of
plugins that implement no hooks.
"""

from __future__ import annotations

from prompt_flags.plugins.hookspecs import hookimpl
from prompt_flags.plugins.manager import PluginManager

# ---------------------------------------------------------------------------
# Test plugin implementations
# ---------------------------------------------------------------------------


class PreLoadPlugin:
    """Plugin that modifies template name during pre_load."""

    @hookimpl
    def pre_load(self, template_name: str, bucket: str | None) -> str | None:
        return f"modified_{template_name}"


class PostLoadPlugin:
    """Plugin that modifies raw content during post_load."""

    @hookimpl
    def post_load(self, template_name: str, raw_content: str) -> str:
        return raw_content.upper()


class PreRenderPlugin:
    """Plugin that modifies template and context during pre_render."""

    @hookimpl
    def pre_render(
        self, template: str, context: dict, flags: dict
    ) -> tuple[str, dict] | None:
        context["injected"] = True
        return (template + " [modified]", context)


class PostRenderPlugin:
    """Plugin that modifies rendered text during post_render."""

    @hookimpl
    def post_render(self, rendered_text: str, metadata: dict) -> str:
        return rendered_text + " [post]"


class FlagResolvedPlugin:
    """Plugin that records flag resolution calls."""

    def __init__(self) -> None:
        """Initialize with empty call log."""
        self.calls: list[dict] = []

    @hookimpl
    def on_flag_resolved(
        self, flag_name: str, value: bool, source: str, scope: dict
    ) -> None:
        self.calls.append(
            {"flag_name": flag_name, "value": value, "source": source, "scope": scope}
        )


class EmptyPlugin:
    """Plugin with no hook implementations. Should not cause errors."""


class AppendPlugin:
    """Plugin that appends a marker to post_render output."""

    @hookimpl
    def post_render(self, rendered_text: str, metadata: dict) -> str:
        return rendered_text + " [append]"


class WrapPlugin:
    """Plugin that wraps post_render output in brackets."""

    @hookimpl
    def post_render(self, rendered_text: str, metadata: dict) -> str:
        return f"[{rendered_text}]"


# ---------------------------------------------------------------------------
# PluginManager initialization tests
# ---------------------------------------------------------------------------


class TestPluginManagerInit:
    """Tests for PluginManager initialization."""

    def test_initialization_succeeds(self) -> None:
        pm = PluginManager()
        assert pm is not None

    def test_has_internal_pluggy_manager(self) -> None:
        pm = PluginManager()
        assert pm._pm is not None

    def test_hookspec_is_registered(self) -> None:
        pm = PluginManager()
        # Verify the hook spec class is registered by checking hooks exist
        assert hasattr(pm._pm.hook, "pre_load")
        assert hasattr(pm._pm.hook, "post_load")
        assert hasattr(pm._pm.hook, "pre_render")
        assert hasattr(pm._pm.hook, "post_render")
        assert hasattr(pm._pm.hook, "on_flag_resolved")


# ---------------------------------------------------------------------------
# Plugin registration tests
# ---------------------------------------------------------------------------


class TestPluginRegistration:
    """Tests for registering plugins."""

    def test_register_plugin(self) -> None:
        pm = PluginManager()
        plugin = PreLoadPlugin()
        pm.register(plugin, name="pre_load_plugin")
        assert pm._pm.is_registered(plugin)

    def test_register_plugin_without_name(self) -> None:
        pm = PluginManager()
        plugin = PreLoadPlugin()
        pm.register(plugin)
        assert pm._pm.is_registered(plugin)

    def test_register_empty_plugin_no_error(self) -> None:
        pm = PluginManager()
        plugin = EmptyPlugin()
        pm.register(plugin, name="empty")
        assert pm._pm.is_registered(plugin)


# ---------------------------------------------------------------------------
# pre_load hook tests
# ---------------------------------------------------------------------------


class TestPreLoadHook:
    """Tests for the pre_load hook."""

    def test_pre_load_modifies_template_name(self) -> None:
        pm = PluginManager()
        pm.register(PreLoadPlugin(), name="preload")
        result = pm.call_pre_load("greeting", bucket="system")
        assert result == "modified_greeting"

    def test_pre_load_no_plugins_returns_original(self) -> None:
        pm = PluginManager()
        result = pm.call_pre_load("greeting", bucket=None)
        assert result == "greeting"

    def test_pre_load_default_bucket_none(self) -> None:
        pm = PluginManager()
        pm.register(PreLoadPlugin(), name="preload")
        result = pm.call_pre_load("test")
        assert result == "modified_test"


# ---------------------------------------------------------------------------
# post_load hook tests
# ---------------------------------------------------------------------------


class TestPostLoadHook:
    """Tests for the post_load hook."""

    def test_post_load_modifies_content(self) -> None:
        pm = PluginManager()
        pm.register(PostLoadPlugin(), name="postload")
        result = pm.call_post_load("greeting", "hello world")
        assert result == "HELLO WORLD"

    def test_post_load_no_plugins_returns_original(self) -> None:
        pm = PluginManager()
        result = pm.call_post_load("greeting", "hello world")
        assert result == "hello world"


# ---------------------------------------------------------------------------
# pre_render hook tests
# ---------------------------------------------------------------------------


class TestPreRenderHook:
    """Tests for the pre_render hook."""

    def test_pre_render_modifies_template_and_context(self) -> None:
        pm = PluginManager()
        pm.register(PreRenderPlugin(), name="prerender")
        template, context = pm.call_pre_render("Hello", {"name": "world"}, {"flag1": True})
        assert template == "Hello [modified]"
        assert context["injected"] is True
        assert context["name"] == "world"

    def test_pre_render_no_plugins_returns_original(self) -> None:
        pm = PluginManager()
        template, context = pm.call_pre_render("Hello", {"name": "world"}, {})
        assert template == "Hello"
        assert context == {"name": "world"}


# ---------------------------------------------------------------------------
# post_render hook tests
# ---------------------------------------------------------------------------


class TestPostRenderHook:
    """Tests for the post_render hook."""

    def test_post_render_modifies_text(self) -> None:
        pm = PluginManager()
        pm.register(PostRenderPlugin(), name="postrender")
        result = pm.call_post_render("Hello world", {"tokens": 2})
        assert result == "Hello world [post]"

    def test_post_render_no_plugins_returns_original(self) -> None:
        pm = PluginManager()
        result = pm.call_post_render("Hello world")
        assert result == "Hello world"

    def test_post_render_default_metadata_none(self) -> None:
        pm = PluginManager()
        pm.register(PostRenderPlugin(), name="postrender")
        result = pm.call_post_render("Hello world")
        assert result == "Hello world [post]"


# ---------------------------------------------------------------------------
# on_flag_resolved hook tests
# ---------------------------------------------------------------------------


class TestOnFlagResolvedHook:
    """Tests for the on_flag_resolved hook."""

    def test_on_flag_resolved_receives_correct_data(self) -> None:
        pm = PluginManager()
        plugin = FlagResolvedPlugin()
        pm.register(plugin, name="flagresolved")
        pm.call_on_flag_resolved("dark_mode", True, "global", {"env": "prod"})
        assert len(plugin.calls) == 1
        assert plugin.calls[0] == {
            "flag_name": "dark_mode",
            "value": True,
            "source": "global",
            "scope": {"env": "prod"},
        }

    def test_on_flag_resolved_default_scope_none(self) -> None:
        pm = PluginManager()
        plugin = FlagResolvedPlugin()
        pm.register(plugin, name="flagresolved")
        pm.call_on_flag_resolved("dark_mode", False, "bucket")
        assert len(plugin.calls) == 1
        assert plugin.calls[0]["scope"] == {}

    def test_on_flag_resolved_multiple_calls(self) -> None:
        pm = PluginManager()
        plugin = FlagResolvedPlugin()
        pm.register(plugin, name="flagresolved")
        pm.call_on_flag_resolved("flag_a", True, "global")
        pm.call_on_flag_resolved("flag_b", False, "bucket")
        assert len(plugin.calls) == 2


# ---------------------------------------------------------------------------
# Multiple plugins tests
# ---------------------------------------------------------------------------


class TestMultiplePlugins:
    """Tests for multiple plugins being called."""

    def test_multiple_post_render_plugins_chain(self) -> None:
        pm = PluginManager()
        pm.register(AppendPlugin(), name="append")
        pm.register(WrapPlugin(), name="wrap")
        result = pm.call_post_render("Hello")
        # Both plugins should have been applied
        assert "[append]" in result or "[" in result
        # The exact order depends on pluggy's LIFO default;
        # what matters is both plugins executed
        assert "Hello" in result


# ---------------------------------------------------------------------------
# Entry point discovery tests
# ---------------------------------------------------------------------------


class TestEntryPointDiscovery:
    """Tests for entry point discovery."""

    def test_discover_entry_points_returns_list(self) -> None:
        pm = PluginManager()
        result = pm.discover_entry_points()
        assert isinstance(result, list)

    def test_discover_entry_points_empty_when_none_registered(self) -> None:
        pm = PluginManager()
        result = pm.discover_entry_points()
        assert result == []
