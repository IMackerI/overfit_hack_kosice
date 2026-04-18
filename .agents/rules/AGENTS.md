---
trigger: always_on
---

# AGENTS.md - 

## Project Overview
TODO


## Architecture
TODO


### Testing
TODO

## Best Practices

- Use linting after completing changes
    - for TS/JS use `biome`
    - for Python use `ruff`

## Common mistakes
When you make a mistake twice, add it here for future agents to learn from it.


## Unexpected Findings
Whenever you find something that you didn't expect, tell the user and record it here.

- `src/` is not a Python package; imports like `from debts import ...` work when `src` is on `PYTHONPATH` or when running `python src/app.py`.
