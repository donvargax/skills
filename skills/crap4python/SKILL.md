---
name: crap4python
description: Run CRAP complexity reports for this repository and decide whether advisory findings need follow-up refactors.
hidden: false
---

# crap4python

Use this skill to run `crap4python` in this repository and produce a clear advisory report.

## Available scripts

- `scripts/crap4python.py` - Run CRAP analysis for changed files or full repository.

## Workflow

1. Run changed-only CRAP report during feature work:

```bash
python scripts/crap4python.py --changed
```

2. Run full CRAP report when evaluating broader quality posture:

```bash
python scripts/crap4python.py .
```

3. Treat output as advisory unless local policy says otherwise.
4. If no action is taken, include a brief quality note in the commit message/body.

## Notes

- In this repository, CRAP output is currently advisory and does not gate commits by itself.
- Mutation testing remains the blocking quality signal for behavioral hardening.
