---
name: scrap4python
description: Run SCRAP test-structure analysis and make an explicit decision on whether to act on advisory recommendations.
hidden: false
---

# scrap4python

Use this skill to run `scrap4python` reports for the test suite and capture an explicit action/no-action decision.

## Available scripts

- `scripts/scrap4python.py` - Run SCRAP test-structure analysis.

## Workflow

1. Run SCRAP report on tests:

```bash
python scripts/scrap4python.py tests
```

2. Optional JSON output for tooling or review:

```bash
python scripts/scrap4python.py tests --json
```

3. Review recommendations as advisory guidance.
4. Make an explicit decision to act or defer.
5. If deferred, add a short quality note in the commit message/body.

## Notes

- SCRAP output is advisory and does not block commits by itself.
- Prioritize touched test files first; legacy hotspots outside the feature scope may be deferred.
