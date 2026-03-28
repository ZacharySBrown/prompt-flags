"""Tests for the Jinja2 custom feature flag extension."""

from prompt_flags.core.models import FlagResult
from prompt_flags.rendering.engine import PromptRenderer
from prompt_flags.rendering.extensions import FeatureFlagExtension


class TestFeatureFlagExtension:
    """Tests for the {% feature %} custom tag."""

    def _make_renderer(self) -> PromptRenderer:
        """Create a renderer with the extension enabled."""
        return PromptRenderer(extensions=[FeatureFlagExtension])

    def test_feature_tag_enabled(self) -> None:
        renderer = self._make_renderer()
        flags = {"cot": FlagResult(name="cot", value=True, source="global")}
        result = renderer.render_template(
            "{% feature 'cot' %}Think step by step.{% endfeature %}",
            context={},
            flags=flags,
        )
        assert "Think step by step." in result

    def test_feature_tag_disabled(self) -> None:
        renderer = self._make_renderer()
        flags = {"cot": FlagResult(name="cot", value=False, source="global")}
        result = renderer.render_template(
            "{% feature 'cot' %}Think step by step.{% endfeature %}",
            context={},
            flags=flags,
        )
        assert result.strip() == ""

    def test_feature_tag_missing_flag(self) -> None:
        renderer = self._make_renderer()
        result = renderer.render_template(
            "{% feature 'nonexistent' %}Hidden{% endfeature %}",
            context={},
            flags={},
        )
        assert result.strip() == ""

    def test_feature_tag_with_surrounding_text(self) -> None:
        renderer = self._make_renderer()
        flags = {"show": FlagResult(name="show", value=True, source="global")}
        result = renderer.render_template(
            "Before\n{% feature 'show' %}Middle{% endfeature %}\nAfter",
            context={},
            flags=flags,
        )
        assert "Before" in result
        assert "Middle" in result
        assert "After" in result

    def test_feature_tag_disabled_removes_content(self) -> None:
        renderer = self._make_renderer()
        flags = {"show": FlagResult(name="show", value=False, source="global")}
        result = renderer.render_template(
            "Before\n{% feature 'show' %}Middle{% endfeature %}\nAfter",
            context={},
            flags=flags,
        )
        assert "Before" in result
        assert "Middle" not in result
        assert "After" in result

    def test_feature_tag_with_context_variables(self) -> None:
        renderer = self._make_renderer()
        flags = {"greet": FlagResult(name="greet", value=True, source="global")}
        result = renderer.render_template(
            "{% feature 'greet' %}Hello {{ name }}!{% endfeature %}",
            context={"name": "Alice"},
            flags=flags,
        )
        assert "Hello Alice!" in result

    def test_nested_feature_tags(self) -> None:
        renderer = self._make_renderer()
        flags = {
            "outer": FlagResult(name="outer", value=True, source="global"),
            "inner": FlagResult(name="inner", value=True, source="global"),
        }
        result = renderer.render_template(
            "{% feature 'outer' %}Outer{% feature 'inner' %}Inner{% endfeature %}{% endfeature %}",
            context={},
            flags=flags,
        )
        assert "Outer" in result
        assert "Inner" in result

    def test_nested_feature_outer_disabled(self) -> None:
        renderer = self._make_renderer()
        flags = {
            "outer": FlagResult(name="outer", value=False, source="global"),
            "inner": FlagResult(name="inner", value=True, source="global"),
        }
        result = renderer.render_template(
            "{% feature 'outer' %}Outer{% feature 'inner' %}Inner{% endfeature %}{% endfeature %}",
            context={},
            flags=flags,
        )
        assert "Outer" not in result
        assert "Inner" not in result
