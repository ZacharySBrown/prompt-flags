# Tech Debt Tracker

Known technical debt items, prioritized and tracked.

## Format

| ID | Description | Priority | Domain | Created | Resolved |
|----|-------------|----------|--------|---------|----------|
| *(none yet)* | | | | | |

## Priority Levels

- **P0**: Blocks development, fix immediately
- **P1**: Causes friction, fix within current sprint
- **P2**: Annoying but workable, fix when convenient
- **P3**: Cosmetic or aspirational, fix opportunistically

## Adding Debt

Use `/cleanup` to scan for tech debt, or add manually:

1. Add a row to the table above
2. Create a Beads task: `bd create --type task "Tech debt: {description}"`
3. Link to relevant code with file paths
