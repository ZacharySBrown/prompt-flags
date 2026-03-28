# Agent with Feature-Flagged Prompts

A minimal working example that combines **prompt_flags** with the **Anthropic SDK** to build a Claude agent whose system prompt is controlled by feature flags.

## What's in This Example

### 5 Prompt Flags

| Flag | Default | What It Controls |
|------|---------|-----------------|
| `chain_of_thought` | `true` | Step-by-step reasoning instructions before the agent answers |
| `structured_output` | `false` | Forces JSON-formatted responses with a defined schema |
| `safety_guardrails` | `true` | Anti-hallucination rules, harm refusal, uncertainty disclosure |
| `personality` | `true` | Conversational tone, follow-up suggestions, clarification prompts |
| `tool_usage_hints` | `true` | Guidance on when/how to use available tools effectively |

### 2 Agent Profiles

| Profile | CoT | JSON | Safety | Personality | Tools |
|---------|-----|------|--------|-------------|-------|
| `research_assistant` | on | off | on | on | on |
| `data_analyst` | on | on | on | off | on |

Both profiles share the same flag definitions and section structure — only the flag overrides differ. This demonstrates how prompt_flags lets you maintain **one set of prompt sections** while creating **multiple behavior profiles**.

### 2 Prompt Construction Approaches

1. **YAML-driven** (`build_prompt_from_yaml`) — Load `agent_config.yaml` and render with `from_yaml()` + `render_prompt()`. Best for production configs.
2. **Builder API** (`build_prompt_with_builder`) — Construct the prompt programmatically with `PromptBuilder`. Best for tests and dynamic scenarios.

Both produce the same output when given the same flags.

## Setup

```bash
# From the repo root
pip install -e .
pip install anthropic

# Set your API key
export ANTHROPIC_API_KEY=your-key-here
```

## Quick Start

### 1. Preview the system prompt (no API call)

```bash
# Default research assistant prompt (all default flags)
uv run python examples/agent_with_flags/agent.py --dry-run

# Data analyst profile (structured_output=on, personality=off)
uv run python examples/agent_with_flags/agent.py --prompt data_analyst --dry-run

# Override flags at runtime
uv run python examples/agent_with_flags/agent.py --dry-run \
    --flag chain_of_thought=false \
    --flag structured_output=true
```

### 2. See how flags change the prompt

```bash
# Show what changes when you toggle flags
uv run python examples/agent_with_flags/agent.py --diff \
    --flag chain_of_thought=false \
    --flag personality=false
```

### 3. Run the agent

```bash
# Default research assistant
uv run python examples/agent_with_flags/agent.py \
    --message "What are the main causes of the 2008 financial crisis?"

# Data analyst with JSON output
uv run python examples/agent_with_flags/agent.py \
    --prompt data_analyst \
    --message "What's the average GDP growth of G7 countries in the last 5 years?"

# Minimal agent: no reasoning, no personality, just safety + tools
uv run python examples/agent_with_flags/agent.py \
    --flag chain_of_thought=false \
    --flag personality=false \
    --message "What's the capital of France?"
```

### 4. Use the builder API instead of YAML

```bash
uv run python examples/agent_with_flags/agent.py --builder --dry-run
```

## How It Works

```
agent_config.yaml          agent.py
┌──────────────┐           ┌──────────────────────────┐
│ flags:       │           │                          │
│   cot: true  │──from_yaml()──▶ PromptRegistry      │
│   json: false│           │       │                  │
│              │           │       ▼                  │
│ buckets:     │           │  render_prompt(          │
│   prompts:   │           │    bucket="agent_system",│
│     sections │           │    prompt="research_...",│
│              │           │    flags={overrides}     │
└──────────────┘           │  )                       │
                           │       │                  │
                           │       ▼                  │
                           │  system_prompt: str      │
                           │       │                  │
                           │       ▼                  │
                           │  client.messages.create( │
                           │    system=system_prompt   │
                           │  )                       │
                           └──────────────────────────┘
```

1. **YAML config** defines flags, sections, and per-prompt overrides
2. **`from_yaml()`** loads the config into a `PromptRegistry`
3. **`render_prompt()`** resolves flags, filters sections, orders them, and renders
4. The resulting string is passed as the `system` parameter to `client.messages.create()`

## Flag Behavior Matrix

Here's what the system prompt looks like under different flag combinations:

| Sections in prompt | All defaults | No CoT | JSON mode | Minimal |
|---|---|---|---|---|
| Identity | yes | yes | yes | yes |
| Reasoning steps | yes | **no** | yes | **no** |
| JSON output format | **no** | **no** | **yes** | **no** |
| Safety guardrails | yes | yes | yes | yes |
| Personality | yes | yes | yes | **no** |
| Tool usage hints | yes | yes | yes | yes |

**Minimal** = `--flag chain_of_thought=false --flag personality=false`

## Using This Pattern in Your Own Agent

```python
from prompt_flags import PromptBuilder

# 1. Define your flags
builder = (
    PromptBuilder("my_agent")
    .in_bucket("agents")
    .flag("chain_of_thought", default=True, description="Step-by-step reasoning")
    .flag("structured_output", default=False, description="JSON responses")
    .flag("safety_guardrails", default=True, description="Safety constraints")
)

# 2. Add sections with flag associations
builder = (
    builder
    .section("identity", "You are a helpful assistant.", priority=1)
    .section("reasoning", "Think step by step...", flag="chain_of_thought", priority=10)
    .section("format", '{"answer": "..."}', flag="structured_output", priority=20)
    .section("safety", "Never fabricate data.", flag="safety_guardrails", priority=30)
)

# 3. Render with runtime overrides
system_prompt = builder.render(flags={"structured_output": True})

# 4. Pass to any LLM API
from anthropic import Anthropic
client = Anthropic()
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system=system_prompt,
    messages=[{"role": "user", "content": "Your question here"}],
)
```

## Files

| File | Purpose |
|------|---------|
| `agent_config.yaml` | YAML config defining 5 flags, 2 prompts, and 6 sections per prompt |
| `agent.py` | CLI script demonstrating both YAML and builder approaches |
| `README.md` | This file |
