"""Minimal example: Claude agent with feature-flagged system prompts.

Demonstrates how to use prompt_flags to build a system prompt from YAML
config, then pass it to the Anthropic SDK to create a Claude agent whose
behavior changes based on which flags are enabled.

Usage:
    # Default flags (from YAML config)
    uv run python examples/agent_with_flags/agent.py

    # Override flags at runtime
    uv run python examples/agent_with_flags/agent.py \
        --flag chain_of_thought=false \
        --flag structured_output=true

    # Use a different prompt profile
    uv run python examples/agent_with_flags/agent.py \
        --prompt data_analyst

    # Dry-run: print the system prompt without calling the API
    uv run python examples/agent_with_flags/agent.py --dry-run

Requirements:
    pip install anthropic
    export ANTHROPIC_API_KEY=your-key-here
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from prompt_flags import PromptBuilder, from_yaml, render_prompt

# ── Flag Definitions (mirrors the YAML for the builder path) ─────

AGENT_FLAGS = {
    "chain_of_thought": {
        "default": True,
        "description": "Step-by-step reasoning before answering",
    },
    "structured_output": {
        "default": False,
        "description": "Respond in structured JSON format",
    },
    "safety_guardrails": {
        "default": True,
        "description": "Safety constraints and honesty guardrails",
    },
    "personality": {
        "default": True,
        "description": "Conversational tone and helpfulness cues",
    },
    "tool_usage_hints": {
        "default": True,
        "description": "Guidance on when/how to use tools",
    },
}


# ── Section Content ──────────────────────────────────────────────

SECTIONS = {
    "identity": {
        "content": (
            "You are a research assistant. Your purpose is to help users "
            "find, analyze, and synthesize information from multiple sources."
        ),
        "priority": 1,
    },
    "reasoning": {
        "content": (
            "Think through problems step by step:\n"
            "1. Identify what information is needed\n"
            "2. Consider multiple perspectives and sources\n"
            "3. Evaluate the reliability of each source\n"
            "4. Synthesize findings into a clear answer\n"
            "5. Note any gaps or uncertainties in the evidence"
        ),
        "flag": "chain_of_thought",
        "priority": 10,
    },
    "output_format": {
        "content": (
            "Always respond with valid JSON in this schema:\n"
            "{\n"
            '  "answer": "Your main answer here",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "sources": ["source1", "source2"],\n'
            '  "reasoning": "Brief explanation"\n'
            "}"
        ),
        "flag": "structured_output",
        "priority": 20,
    },
    "safety": {
        "content": (
            "Important constraints:\n"
            "- If you are unsure about something, say so explicitly\n"
            "- Never fabricate sources, citations, or data\n"
            "- If a request could cause harm, decline and explain why\n"
            "- Distinguish clearly between facts and opinions"
        ),
        "flag": "safety_guardrails",
        "priority": 30,
    },
    "personality": {
        "content": (
            "Be helpful and approachable. Use clear language, avoid jargon "
            "unless the user is technical, and offer follow-up suggestions "
            "when appropriate. If a question is ambiguous, ask for clarification "
            "rather than guessing."
        ),
        "flag": "personality",
        "priority": 40,
    },
    "tool_hints": {
        "content": (
            "You have access to tools. Use them wisely:\n"
            "- Use the search tool for factual questions you aren't certain about\n"
            "- Use the calculator for any math beyond simple arithmetic\n"
            "- Prefer tool results over your own knowledge for time-sensitive data\n"
            "- Always explain to the user what tool you're using and why"
        ),
        "flag": "tool_usage_hints",
        "priority": 50,
    },
}


# ── Tools for the Agent ──────────────────────────────────────────

AGENT_TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web for current information on a topic.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "calculator",
        "description": "Perform a mathematical calculation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The math expression to evaluate (e.g., '2 + 2')",
                },
            },
            "required": ["expression"],
        },
    },
]


# ── Approach 1: Build System Prompt from YAML Config ─────────────


def build_prompt_from_yaml(
    prompt_name: str = "research_assistant",
    flag_overrides: dict[str, bool] | None = None,
) -> str:
    """Load the YAML config and render a system prompt.

    This is the recommended approach for production: define your prompts
    in YAML, and use flag overrides to customize behavior at runtime.

    Args:
        prompt_name: Which prompt to render from the config.
        flag_overrides: Runtime flag overrides (e.g., {"chain_of_thought": False}).

    Returns:
        The rendered system prompt string.
    """
    config_path = Path(__file__).parent / "agent_config.yaml"
    registry = from_yaml(config_path)
    return render_prompt(
        registry,
        bucket_name="agent_system",
        prompt_name=prompt_name,
        flags=flag_overrides,
    )


# ── Approach 2: Build System Prompt with the Builder API ─────────


def build_prompt_with_builder(
    flag_overrides: dict[str, bool] | None = None,
) -> str:
    """Build a system prompt programmatically using PromptBuilder.

    This approach is useful when you want to construct prompts in code
    rather than YAML — for example, in tests or dynamic scenarios.

    Args:
        flag_overrides: Runtime flag overrides.

    Returns:
        The rendered system prompt string.
    """
    builder = PromptBuilder("research_assistant").in_bucket("agent_system")

    # Register all flags
    for name, config in AGENT_FLAGS.items():
        builder = builder.flag(name, default=config["default"], description=config["description"])

    # Add all sections
    for section_id, section_config in SECTIONS.items():
        builder = builder.section(
            section_id,
            section_config["content"],
            flag=section_config.get("flag"),
            priority=section_config.get("priority", 100),
        )

    return builder.render(flags=flag_overrides)


# ── Agent Runner ─────────────────────────────────────────────────


def run_agent(
    user_message: str,
    system_prompt: str,
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """Send a message to Claude using the system prompt.

    Args:
        user_message: The user's input message.
        system_prompt: The feature-flagged system prompt.
        model: The Claude model to use.

    Returns:
        The agent's response text.
    """
    try:
        from anthropic import Anthropic
    except ImportError as err:
        raise SystemExit(
            "The 'anthropic' package is required to run the agent.\n"
            "Install it with: pip install anthropic"
        ) from err

    client = Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system_prompt,
        tools=AGENT_TOOLS,
        messages=[{"role": "user", "content": user_message}],
    )

    # Extract text from the response
    text_parts = [block.text for block in response.content if hasattr(block, "text")]
    return "\n".join(text_parts) if text_parts else "(no text response)"


# ── CLI ──────────────────────────────────────────────────────────


def parse_flag_override(value: str) -> tuple[str, bool]:
    """Parse a flag override from CLI argument.

    Args:
        value: String in format "flag_name=true" or "flag_name=false".

    Returns:
        Tuple of (flag_name, bool_value).
    """
    name, _, raw = value.partition("=")
    if raw.lower() in ("true", "1", "yes"):
        return name, True
    elif raw.lower() in ("false", "0", "no"):
        return name, False
    raise argparse.ArgumentTypeError(f"Invalid flag value: {value!r} (use true/false)")


def main() -> None:
    """CLI entry point for the agent example."""
    parser = argparse.ArgumentParser(
        description="Run a Claude agent with feature-flagged system prompts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Default config\n"
            "  python agent.py\n\n"
            "  # Override flags\n"
            "  python agent.py --flag chain_of_thought=false --flag structured_output=true\n\n"
            "  # Different prompt profile\n"
            "  python agent.py --prompt data_analyst\n\n"
            "  # Dry-run: just print the system prompt\n"
            "  python agent.py --dry-run\n\n"
            "  # Use the builder API instead of YAML\n"
            "  python agent.py --builder\n"
        ),
    )
    parser.add_argument(
        "--prompt",
        default="research_assistant",
        help="Prompt name from the YAML config (default: research_assistant)",
    )
    parser.add_argument(
        "--flag",
        action="append",
        type=parse_flag_override,
        default=[],
        dest="flags",
        help="Flag override in format name=true/false (repeatable)",
    )
    parser.add_argument(
        "--message",
        default="What are the main causes of the 2008 financial crisis?",
        help="User message to send to the agent",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the system prompt and exit (don't call the API)",
    )
    parser.add_argument(
        "--builder",
        action="store_true",
        help="Use the PromptBuilder API instead of YAML config",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="Show how the prompt changes with vs. without the flag overrides",
    )

    args = parser.parse_args()
    flag_overrides = dict(args.flags) if args.flags else None

    # Build the system prompt
    if args.builder:
        system_prompt = build_prompt_with_builder(flag_overrides)
    else:
        system_prompt = build_prompt_from_yaml(args.prompt, flag_overrides)

    # Diff mode: show default vs. overridden prompt
    if args.diff:
        if args.builder:
            default_prompt = build_prompt_with_builder()
        else:
            default_prompt = build_prompt_from_yaml(args.prompt)
        _print_diff(default_prompt, system_prompt, flag_overrides)
        return

    # Dry-run mode: print the prompt and exit
    if args.dry_run:
        _print_header("System Prompt", flag_overrides)
        sys.stdout.write(system_prompt + "\n")
        return

    # Run the agent
    _print_header("Running Agent", flag_overrides)
    sys.stdout.write(f"User: {args.message}\n")
    sys.stdout.write("-" * 50 + "\n")
    response = run_agent(args.message, system_prompt)
    sys.stdout.write(f"Agent: {response}\n")


def _print_header(title: str, flag_overrides: dict[str, bool] | None) -> None:
    """Print a formatted header with active flag info."""
    sys.stdout.write(f"\n{'=' * 50}\n")
    sys.stdout.write(f"  {title}\n")
    if flag_overrides:
        overrides_str = ", ".join(f"{k}={v}" for k, v in flag_overrides.items())
        sys.stdout.write(f"  Overrides: {overrides_str}\n")
    sys.stdout.write(f"{'=' * 50}\n\n")


def _print_diff(
    default: str,
    overridden: str,
    flag_overrides: dict[str, bool] | None,
) -> None:
    """Show the difference between default and overridden prompts."""
    _print_header("Prompt Diff", flag_overrides)

    default_lines = set(default.strip().splitlines())
    overridden_lines = set(overridden.strip().splitlines())

    removed = default_lines - overridden_lines
    added = overridden_lines - default_lines

    if removed:
        sys.stdout.write("Removed sections:\n")
        for line in sorted(removed):
            if line.strip():
                sys.stdout.write(f"  - {line.strip()}\n")
        sys.stdout.write("\n")

    if added:
        sys.stdout.write("Added sections:\n")
        for line in sorted(added):
            if line.strip():
                sys.stdout.write(f"  + {line.strip()}\n")
        sys.stdout.write("\n")

    if not removed and not added:
        sys.stdout.write("No difference — overrides match defaults.\n")


if __name__ == "__main__":
    main()
