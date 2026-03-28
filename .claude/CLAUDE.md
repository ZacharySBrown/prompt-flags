# PromptFlags

A Python package for feature-flagged prompt engineering — declarative section management, scoped overrides, topological ordering, and bucket-based organization.

## Package Architecture

```
src/prompt_flags/
├── core/           # Domain models (Bucket, Section, Flag, etc.), PromptRegistry, flag resolver, topological ordering
├── config/         # YAML config schemas (Pydantic v2), layered config loader, default values
├── rendering/      # Jinja2 environment setup, custom FeatureFlag extension, filters
├── api/            # Fluent PromptBuilder, @section/@prompt/@bucket decorators, standalone functions
├── plugins/        # Protocol interfaces, pluggy hook specs, plugin discovery via entry_points
└── _bundled/       # Default Jinja2 macros and templates
```

**Dependency flow**: `core → config → rendering → api`, with `plugins` as cross-cutting.

## Key Commands

```bash
uv run ruff check .                                   # Lint
uv run ruff format --check .                          # Format check
uv run pyright                                        # Type check
uv run pytest                                         # All tests
uv run python -m tools.linters.check_pydantic_boundaries  # Pydantic boundary check
uv run python -m tools.linters.check_no_print              # No print() in library code
uv run python -m tools.linters.check_docstrings            # Docstring coverage
uv run mkdocs build --strict                          # Build docs site
uv run mkdocs serve                                   # Serve docs locally
```

## Beads (Project Tracking)

```bash
bd ready          # Show next unblocked task
bd list           # List all tasks
bd show <id>      # Show task details
bd create         # Create new task
```

## Documentation (Progressive Disclosure)

- **Architecture** → `docs/architecture/ARCHITECTURE.md`
- **Core beliefs** → `docs/design-docs/core-beliefs.md`
- **Design docs** → `docs/design-docs/index.md`
- **Exec plans** → `docs/exec-plans/active/`
- **Quality scores** → `docs/QUALITY_SCORE.md`
- **Tech debt** → `docs/exec-plans/tech-debt-tracker.md`
- **Reference docs** → `docs/references/`
- **Initial spec** → `initial-spec.md`

## Conventions

- **Python 3.12+**, managed with `uv`
- **Pydantic v2 at all boundaries**: Public API functions, config schemas, domain models
- **No print() in library code**: Raise exceptions or return values; never print to stdout
- **Docstrings on public interfaces**: All public functions, classes, and methods (Google style)
- **File size limit**: 300 lines max. Split larger files into focused modules.
- **Naming**: snake_case for modules/functions, PascalCase for classes, UPPER_CASE for constants
- **Tests**: Every feature/fix needs tests. TDD preferred. `tests/` mirrors `src/` structure.
- **Imports**: Absolute imports from `prompt_flags.*`. No relative imports across subpackages.

## Review Gates

**Critical (blocks merge)**:
- Missing tests for new code
- Broken type checking
- Pydantic boundary violations in public API
- print() in library code

**Advisory (suggest, don't block)**:
- Style/formatting (auto-fixable)
- Doc freshness
- Naming conventions

## Agent Roles

Four specialized roles provide distinct perspectives, constraints, and escalation behaviors. Roles activate automatically via skills or manually via `/role`.

| Role | Skills | Posture |
|------|--------|---------|
| **Architect** | `/design`, `/plan` | Strategic — designs package API, evaluates trade-offs |
| **Engineer** | `/scaffold` | Tactical — implements via TDD, follows patterns |
| **Reviewer** | `/review` | Reactive — reviews changes, enforces gates |
| **Operator** | `/eval`, `/quality`, `/cleanup`, `/docs` | Proactive — scans health, manages entropy |

- **Dev-time profiles**: `.claude/agents/{role}.md` — persona, constraints, escalation rules
- **Activate manually**: `/role architect` (persists until `/role {other}` or "drop role")
- **Auto-activation**: Each skill loads its mapped role automatically

## Development Workflow

```
/design → Design Doc → /plan → Exec Plan → bd ready → Implement (TDD) → /review → Merge
```

## Session Management

When multiple Claude Code windows run simultaneously (e.g., Architect + Engineer), follow these rules to avoid conflicts. Design doc: `docs/design-docs/multi-session.md`.

### Startup Protocol

On first interaction in a new session:

1. **Detect active sessions** — Read `.claude/sessions/*.json`. Delete any file older than 4 hours (stale). Report active sessions to the user.
2. **Detect dev mode** — Determine solo or team mode:
   - Check: does `bd config get github.repo` return a value? Does `git remote -v` show a remote?
   - Both configured → **team mode**. Either missing → **solo mode**.
   - If beads unavailable: `git remote -v` alone. Remote exists → team; no remote → solo.
   - Report: "Dev mode: **team**" or "Dev mode: **solo**".
   - User can override anytime: "switch to solo/team mode".
3. **Select a role** — If the user's first message isn't a specific task, ask which role to activate (architect, engineer, reviewer, operator). If it IS a task, infer the appropriate role and confirm briefly.
4. **Register this session** — Write `.claude/sessions/{role}-{HHmmss}.json`:
   ```json
   {"role": "engineer", "mode": "team", "started": "2026-02-23T10:15:00Z", "task": "", "focus": ""}
   ```
5. **Claim work** — If beads is available (`bd ready`), show the next unblocked task and help claim it. Update the session file with the task ID. If beads is not available, note the planned focus in the session file.

On session end ("done", "bye", "end session", or role switch): delete the session file.

### Coordination Rules

**1. Own your lane** — Each role has a defined write scope. Don't modify files outside it.

| Role | Can Modify | Read-Only |
|------|-----------|-----------|
| Architect | `docs/`, `.claude/` (excl. `sessions/`) | Everything else |
| Engineer | `src/`, `tests/` (claimed subpackages only) | Everything |
| Reviewer | Nothing (read-only) | Everything |
| Operator | `tools/`, `docs/QUALITY_SCORE.md`, tech debt tracker | Everything else |

**2. Claim before you build** — Every coding session must reference a bead task or have a stated focus in its session file. No unclaimed work.

**3. One task at a time** — WIP limit of 1 per session. Finish or explicitly park before switching.

**4. Dependencies flow forward** — core → config → rendering → api → plugins. Don't start downstream work until its upstream dependency is done.

**5. Conflicts mean stop** — If you need a file another session owns, tell the user and wait. Don't proceed without explicit coordination.

## Dev Mode: Solo vs Team

Beads is always the agent's working memory. In team mode, significant work is also projected to GitHub Issues for remote collaborators.

| Aspect | Solo | Team |
|--------|------|------|
| Task tracking | Beads only | Beads + GH Issues (epics, P0-P1 features) |
| PR workflow | Optional | Required, linked to GH Issues |
| Session end | Commit + push | Commit + push + update GH Issues |
| Review output | Terminal only | Terminal + PR comment |

### What gets projected to GitHub Issues

- **Always**: Epics (`bd create --type epic`)
- **If P0-P1**: Features and bugs
- **Never**: Tasks, chores, agent-internal work items

### Projection workflow

When creating a beads epic/feature in team mode:
1. Create the beads task first (beads is always primary)
2. Create a GH Issue: `gh issue create --title "..." --body "Beads: {task-id}"`
3. Update beads task description to include `GH#{number}`

When closing a beads task that has a `GH#` reference:
1. Close the beads task first
2. Close or comment on the GH Issue: `gh issue close {number}` or `gh issue comment {number}`

### Mode override

- "Switch to team mode" / "switch to solo mode" — changes for the session
- Mode is recorded in the session file so other sessions can see it
