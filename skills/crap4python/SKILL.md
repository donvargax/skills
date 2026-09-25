---
name: crap4python
description: Compute per-function CRAP scores (cyclomatic complexity combined with test coverage) for Python code and report which functions are risky to change.
when_to_use: Use when asked to assess Python code quality, change risk, complexity, or which functions most need tests or refactoring, or before merging a feature to see whether the touched code got riskier. Examples — "which functions in this PR are risky to change?", "run a CRAP report", "where should I add tests first?".
---

# crap4python

CRAP (Change Risk Anti-Patterns) scores each function as `CC^2 * (1 - coverage)^3 + CC`. High complexity with low coverage scores high. The conventional threshold is 30.

## Available scripts

- `scripts/crap4python.py` - Self-contained (`uv run`) CRAP analyzer. Runs tests under coverage, then scores functions.

## Workflow

1. During feature work, score only files with uncommitted changes in the working tree, per `git status` (test files excluded):

```bash
uv run skills/crap4python/scripts/crap4python.py --changed
```

2. For a whole-repo baseline:

```bash
uv run skills/crap4python/scripts/crap4python.py .
```

3. Machine-readable output for tooling:

```bash
uv run skills/crap4python/scripts/crap4python.py --changed --porcelain
```

4. Read the output as advisory. For each function over threshold decide: add tests, split the function, or defer. If deferring, say so in the commit body in one line ("CRAP: foo() at 42, deferred, covered by follow-up #123").

## Notes

- Advisory by default. Whether CRAP gates commits is the consuming project's policy, not this skill's. Put that rule in the project's CLAUDE.md.
- Pairs with `mutate4python` (test strength) and `scrap4python` (test structure). Run CRAP first: it is cheapest and tells you where mutation testing is worth the time.

## Open source alternatives

- [crap4py](https://pypi.org/project/crap4py/) - stdlib-only port of crap4j, reads coverage.py JSON.
- [lukasa1993/crap4python](https://github.com/lukasa1993/crap4python) - Tree-sitter based, `--fail-over` threshold gate, reads LCOV, Cobertura, coverage.py JSON.
- [deangrant/crap-score](https://github.com/deangrant/crap-score) - same metric with matching CLIs for Python, Go, Rust, and TypeScript, if you want one tool across languages.

The bundled script exists because it adds `--changed` (working-tree scoping) and runs the test suite itself. If one of the above grows a diff mode, replace the script with it.
