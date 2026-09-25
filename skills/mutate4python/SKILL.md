---
name: mutate4python
description: Run mutation testing on a Python module, scoped to code changed since the last run, and report surviving mutants as tests that do not actually catch bugs.
when_to_use: Use when asked whether the tests for a module are strong enough, when hardening a module before release, or as the final quality check on a feature branch. Examples — "are my tests for config.py actually good?", "run mutation testing on the changed files", "any surviving mutants?".
---

# mutate4python

Mutation testing changes the code (flip a comparison, swap `and` for `or`, replace `0` with `1`) and re-runs the tests. A mutant that survives means no test noticed the change. Survivors are the actionable output.

## Available scripts

- `scripts/mutate4python.py` - Self-contained (`uv run`) mutation runner. One module per invocation. Uses coverage to select only covered mutation sites and a manifest to skip scopes unchanged since the last run.

## Workflow

1. Run on a module, only mutating scopes changed since the last run:

```bash
uv run skills/mutate4python/scripts/mutate4python.py src/pkg/config.py --since-last-run --test-command "uv run pytest"
```

2. Run everything in the module (first run, or after a large refactor):

```bash
uv run skills/mutate4python/scripts/mutate4python.py src/pkg/config.py --mutate-all --test-command "uv run pytest"
```

3. Preview mutation sites without running tests:

```bash
uv run skills/mutate4python/scripts/mutate4python.py src/pkg/config.py --scan
```

4. Restrict to specific lines (for example the lines of a PR diff):

```bash
uv run skills/mutate4python/scripts/mutate4python.py src/pkg/config.py --lines 12,18,44
```

5. For each survivor: write the test that kills it, or delete the dead logic. Re-run until no survivors remain, then `--update-manifest` to record the new baseline.

## Notes

- The script runs one module at a time. To cover a branch, list changed modules with `git diff --name-only main...HEAD -- '*.py'` and loop.
- Mutation testing is slow. Run `crap4python` first and only mutate modules that score high.
- Whether survivors block merges is the consuming project's policy. Put that rule in the project's CLAUDE.md.

## Open source alternatives

- [mutmut](https://mutmut.readthedocs.io/) - most active Python mutation tester, coverage-aware, incremental cache.
- [cosmic-ray](https://cosmic-ray.readthedocs.io/) - broadest operator set, parallel workers, `cr-filter-git` for diff scoping.

The bundled script exists for single-file `uv run` portability and its scope-level manifest (skip unchanged functions). If those matter less than operator coverage and community support, use mutmut and delete this script.
