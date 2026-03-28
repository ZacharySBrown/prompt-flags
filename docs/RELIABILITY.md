# Reliability

## Overview

Reliability practices for the PromptFlags package.

## Areas

- **Error handling**: Clear exception hierarchy, meaningful error messages with context
- **Config validation**: Pydantic v2 strict validation catches typos and invalid config at load time
- **Cycle detection**: Topological sort surfaces ordering cycles with clear diagnostics
- **Flag resolution tracing**: Every resolved flag records which tier provided the value

## Current Status

No production code yet. Reliability practices will be documented as each subpackage is implemented.
