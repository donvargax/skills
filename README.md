# skills

Agent skills for Claude Code. Each skill is a directory under `skills/` with a `SKILL.md` and, where needed, a self-contained script.

House rule: no code is best, someone else's code is second, our own code is a reluctant third. Every skill that ships a script lists the open source tools that could replace it, and says what would have to change for that to happen.

## Install

```bash
claude plugin marketplace add donvargax/skills
claude plugin install donvargax-skills@donvargax-skills
```

Or copy a single skill directory into `.claude/skills/` in a project.

## Skills

| Skill | What it does | Bundled script | Replace with |
|---|---|---|---|
| [crap4python](skills/crap4python/SKILL.md) | CRAP score per function: complexity combined with coverage | `uv run` Python, adds `--changed` working-tree scoping | [crap4py](https://pypi.org/project/crap4py/), [lukasa1993/crap4python](https://github.com/lukasa1993/crap4python), [crap-score](https://github.com/deangrant/crap-score) once one has a diff mode |
| [scrap4python](skills/scrap4python/SKILL.md) | Test-suite structure and pressure report | `uv run` Python | Nothing equivalent yet. `ruff` `PT` rules cover part of it |
| [mutate4python](skills/mutate4python/SKILL.md) | Mutation testing scoped to changed scopes | `uv run` Python | [mutmut](https://mutmut.readthedocs.io/), [cosmic-ray](https://cosmic-ray.readthedocs.io/) |
| [md-to-confluence](skills/md-to-confluence/SKILL.md) | Markdown plus Mermaid to a Confluence page | PowerShell 7, pandoc, mmdc | [kovetskiy/mark](https://github.com/kovetskiy/mark), which already does all of it |
| [fetching-images](skills/fetching-images/SKILL.md) | Licensed images with attribution from Wikimedia, Unsplash, Pexels, Pixabay | `uv run` Python | [Openverse](https://openverse.org/) API for a single CC-only source |

## Conventions

- Scripts are single files runnable with `uv run` (PEP 723 inline metadata). Multi-module tools are bundled with stickytape.
- Skills never hardcode credentials. Secrets come from environment variables and the script fails fast when one is missing.
- `SKILL.md` frontmatter uses `name`, `description`, and `when_to_use` only. `description` says what the skill does; `when_to_use` gives trigger examples.
- Skills stay project-neutral. Policy such as "mutation survivors block merges" belongs in the consuming project's `CLAUDE.md`, not here.

## Wishlist

**A `gh api` for Jira and Confluence.** One binary, one auth setup, raw REST passthrough: `atl api confluence GET /pages?title=Foo`, `atl api jira POST /issue --data @body.json`. Nothing first-party fills this today. The `conf-api-*.ps1` wrappers in `md-to-confluence` are the stopgap. Watch Atlassian's official `acli` for a raw `api` subcommand, and the [Atlassian Rovo MCP server](https://github.com/atlassian/atlassian-mcp-server) for agent use. If neither closes the gap, the plan is a single `uv run` Python script covering both products with the same `METHOD PATH [--data] [--file]` interface, and `md-to-confluence` then depends on it.

**A single orchestrating quality gate.** One skill that runs CRAP, then mutation testing on the high-scoring modules, then SCRAP on touched tests, and prints one summary. The three skills above become its building blocks.
