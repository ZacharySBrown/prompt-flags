# Quality Score

Per-subpackage quality grades, updated by the `/quality` skill.

## Scoring Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Lint compliance | 25% | Zero ruff violations |
| Type safety | 25% | Pyright strict passes |
| Test coverage | 25% | Unit tests exist for all public interfaces |
| Doc freshness | 15% | Docs updated within last N changes to related code |
| Eval performance | 10% | Evals pass at acceptable thresholds |

## Grades

| Subpackage | Lint | Types | Tests | Docs | Evals | Overall |
|------------|------|-------|-------|------|-------|---------|
| core | N/A | N/A | N/A | N/A | N/A | N/A — no code yet |
| config | N/A | N/A | N/A | N/A | N/A | N/A — no code yet |
| rendering | N/A | N/A | N/A | N/A | N/A | N/A — no code yet |
| api | N/A | N/A | N/A | N/A | N/A | N/A — no code yet |
| plugins | N/A | N/A | N/A | N/A | N/A | N/A — no code yet |

## Last Updated

*(not yet scored — run `/quality` to generate initial scores)*
