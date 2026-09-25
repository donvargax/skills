---
name: scrap4python
description: Analyze a Python test suite's structure (example shapes, helpers, nesting, pressure hotspots) and report test files that are hard to read or extend.
when_to_use: Use when asked whether tests are well structured, when a test file has become hard to follow, when reviewing test changes in a PR, or when deciding which legacy tests to clean up first. Examples — "are these tests in good shape?", "run SCRAP on tests/", "which test files are the messiest?".
---

# scrap4python

SCRAP scores test files on structure, not on what they cover: how examples are shaped, how helpers are used, and where "pressure" (long, nested, or overloaded tests) builds up. Output is a ranked list of files and recommendations.

## Available scripts

- `scripts/scrap4python.py` - Self-contained (`uv run`) SCRAP analyzer. Defaults to the `tests` directory when no path is given.

## Workflow

1. Report on the test suite:

```bash
uv run skills/scrap4python/scripts/scrap4python.py tests
```

2. Full per-file, per-class, per-test detail:

```bash
uv run skills/scrap4python/scripts/scrap4python.py tests --verbose
```

3. JSON for tooling or review:

```bash
uv run skills/scrap4python/scripts/scrap4python.py tests --json
```

4. Track drift over time: save a baseline once, compare on later runs. The baseline file is named after the analyzed path (`tests` becomes `target/scrap4python/tests.json`).

```bash
uv run skills/scrap4python/scripts/scrap4python.py tests --write-baseline
uv run skills/scrap4python/scripts/scrap4python.py tests --compare target/scrap4python/tests.json
```

5. Treat recommendations as advisory. Make an explicit act-or-defer decision for the test files touched by the current change. If deferring, say so in the commit body in one line.

## Notes

- Advisory by default. Whether SCRAP gates commits is the consuming project's policy. Put that rule in the project's CLAUDE.md.
- Prioritize touched test files first. Legacy hotspots outside the feature scope may be deferred.
- Pairs with `crap4python` (where production code is risky) and `mutate4python` (whether tests actually catch bugs).

## Open source alternatives

No published tool computes this metric. Closest neighbours:

- `ruff` with the `PT` (flake8-pytest-style) rules catches many structural test smells for free and is probably already in your toolchain.
- [pytest-check](https://github.com/okken/pytest-check) and `pytest --collect-only -q` give cheap signals on test count and shape.

If a maintained project appears that scores test structure, replace this script with it.
