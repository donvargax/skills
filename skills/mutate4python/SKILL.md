---
name: mutate4python
description: Run branch-diff mutation testing and use surviving mutants as blocking quality feedback.
hidden: false
---

# mutate4python

Use this skill to execute mutation testing for changed `app/**/*.py` files and treat survivors as blocking defects.

## Available scripts

- `scripts/mutate4python.py` - Run mutation testing for Python modules.

## Workflow

1. Run branch-diff mutation tests:

```bash
python scripts/mutate4python.py app/config.py --since-last-run --test-command "uv run pytest"
```

2. If survivors exist, treat as blocking and fix tests/logic.
3. Re-run until no survivors remain.
4. Optionally run with a different test command:

```bash
python scripts/mutate4python.py app/security/context.py --mutate-all --test-command "uv run pytest"
```

## Notes

- Mutation survivors are blocking for feature completion in this repository.
- For branch-diff execution across changed files, use the repo command:

```bash
uv run quality-loop mutate-changed --base-ref main...HEAD --test-command "uv run pytest"
```
