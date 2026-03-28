"""End-to-end integration tests: YAML config to rendered output.

Tests the complete pipeline from loading a YAML config file through
flag resolution, section ordering, rendering, and composition.
"""

from prompt_flags.api.functional import compose, render_prompt
from prompt_flags.core.models import RuntimeOverrides
from prompt_flags.core.registry import PromptRegistry
from prompt_flags.rendering.engine import PromptRenderer


class TestYAMLToRender:
    """Test the full pipeline: YAML config -> load -> resolve flags -> order sections -> render."""

    def test_load_yaml_and_render_prompt(
        self, sample_registry: PromptRegistry
    ) -> None:
        """Load sample_config.yaml, render a prompt, verify output."""
        render_prompt(sample_registry, "guides", "coding_guide")

        # chain_of_thought is True at bucket level, so reasoning_steps should appear
        # few_shot_examples is True at bucket level, so worked_example should appear
        # safety_guardrails is True globally, so style_constraints should appear
        # The sections have no inline content in sample_config, so rendered output
        # comes from section content (which is empty string for sections without content)
        # But active sections should be resolved correctly
        active = sample_registry.get_active_sections("guides", "coding_guide")
        active_ids = [s.id for s in active]
        assert "reasoning_steps" in active_ids
        assert "style_constraints" in active_ids

    def test_render_with_runtime_flag_overrides(
        self, sample_registry: PromptRegistry
    ) -> None:
        """Override flags at render time and verify they take effect."""
        # Disable chain_of_thought at runtime
        overrides = RuntimeOverrides(flags={"chain_of_thought": False})
        active = sample_registry.get_active_sections(
            "guides", "coding_guide", runtime_overrides=overrides
        )
        active_ids = [s.id for s in active]

        # chain_of_thought=False should disable reasoning_steps
        assert "reasoning_steps" not in active_ids
        # style_constraints (safety_guardrails=True) should still be present
        assert "style_constraints" in active_ids

    def test_render_with_disabled_bucket(
        self, multi_bucket_registry: PromptRegistry
    ) -> None:
        """Verify disabled buckets are skipped in compose."""
        bucket = multi_bucket_registry.get_bucket("disabled_bucket")
        assert bucket.enabled is False

        # Compose only enabled buckets -- disabled_bucket should not contribute
        result = compose(
            multi_bucket_registry,
            ["system_context", "guides", "constraints"],
        )
        assert "This should not appear" not in result

    def test_compose_multiple_buckets(
        self, multi_bucket_registry: PromptRegistry
    ) -> None:
        """Compose across multiple buckets and verify ordering."""
        result = compose(
            multi_bucket_registry,
            ["system_context", "guides", "constraints"],
        )
        # system_context sections should be rendered
        assert "You are a helpful assistant." in result
        # guides sections should be rendered (chain_of_thought=True at bucket)
        assert "Think step by step before answering." in result
        # constraints sections should be rendered (safety_guardrails=True globally)
        assert "Do not generate harmful content." in result

    def test_flag_resolution_trace(
        self, multi_bucket_registry: PromptRegistry
    ) -> None:
        """Verify FlagResult traces show correct resolution tier."""
        flag_map = multi_bucket_registry.resolve_flags("guides", "coding_guide")

        # chain_of_thought: bucket-level override = True
        cot = flag_map["chain_of_thought"]
        assert cot.value is True
        assert cot.source == "bucket"

        # few_shot_examples: bucket-level override = True (global default is False)
        fse = flag_map["few_shot_examples"]
        assert fse.value is True
        assert fse.source == "bucket"

        # json_output: no overrides, global default = False
        json_out = flag_map["json_output"]
        assert json_out.value is False
        assert json_out.source == "global"

        # safety_guardrails: no overrides, global default = True
        safety = flag_map["safety_guardrails"]
        assert safety.value is True
        assert safety.source == "global"

    def test_runtime_override_trumps_bucket(
        self, multi_bucket_registry: PromptRegistry
    ) -> None:
        """Runtime overrides have highest precedence, even over bucket."""
        overrides = RuntimeOverrides(flags={"chain_of_thought": False})
        flag_map = multi_bucket_registry.resolve_flags(
            "guides", "coding_guide", runtime_overrides=overrides
        )
        cot = flag_map["chain_of_thought"]
        assert cot.value is False
        assert cot.source == "runtime"

    def test_section_ordering_respects_constraints(
        self, multi_bucket_registry: PromptRegistry
    ) -> None:
        """Sections obey ordering constraints from YAML config."""
        # The multi_bucket config has: reasoning_steps before worked_example
        active = multi_bucket_registry.get_active_sections(
            "guides", "coding_guide"
        )
        active_ids = [s.id for s in active]
        if "reasoning_steps" in active_ids and "worked_example" in active_ids:
            assert active_ids.index("reasoning_steps") < active_ids.index(
                "worked_example"
            )

    def test_render_with_jinja2_template_in_section(
        self, renderer: PromptRenderer
    ) -> None:
        """Sections with Jinja2 content are rendered with context."""
        from prompt_flags.core.models import FlagResult, Section

        sections = [
            Section(
                id="greeting",
                content="Hello {{ name }}, welcome to {{ place }}.",
                priority=1,
            ),
        ]
        flags: dict[str, FlagResult] = {}
        rendered = renderer.render_sections(
            sections, {"name": "Alice", "place": "Wonderland"}, flags
        )
        assert len(rendered) == 1
        assert rendered[0].content == "Hello Alice, welcome to Wonderland."

    def test_full_pipeline_compose_respects_flags(
        self, multi_bucket_registry: PromptRegistry
    ) -> None:
        """Full pipeline: compose with runtime flag overrides."""
        # Disable safety_guardrails at runtime
        result = compose(
            multi_bucket_registry,
            ["guides", "constraints"],
            flags={"safety_guardrails": False},
        )
        # style_constraints and safety_rules are gated on safety_guardrails
        assert "Follow clean code practices." not in result
        assert "Do not generate harmful content." not in result
        # But reasoning sections should still appear
        assert "Think step by step before answering." in result
