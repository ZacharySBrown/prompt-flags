# Security

## Overview

Security practices for the PromptFlags package.

## Principles

- **No secrets in code**: All credentials via environment variables
- **Pydantic validation**: Input validation on all config and public API boundaries
- **Jinja2 sandboxing**: Templates run with `StrictUndefined` to fail fast on missing variables
- **Dependency minimalism**: Small dependency footprint reduces supply chain risk

## Areas

- **Template security**: Jinja2 autoescape disabled (prompt text, not HTML) — document this tradeoff
- **Config validation**: `extra="forbid"` rejects unrecognized YAML keys
- **Plugin trust**: Entry-point plugins run with full access — document trust model
- **Dependency security**: Regular audits, pinned versions, vulnerability scanning

## Current Status

No production code yet. Security practices will be documented as each subpackage is implemented.
