---
name: md-to-confluence
description: Publish a Markdown document to a Confluence Cloud page, rendering Mermaid code blocks to PNG attachments, creating or updating the page by title.
when_to_use: Use when the user wants a Markdown file (design doc, runbook, ADR, README) on Confluence, or wants an existing Confluence page refreshed from Markdown. Examples — "publish docs/adr-007.md to the Platform space", "update the 'Deploy Runbook' page from this file", "push this to Confluence under the Architecture parent page".
---

# md-to-confluence

Use this skill to convert a Markdown document into Confluence storage HTML, render Mermaid code blocks to images, and create or update a Confluence page.

## Before writing new code: consider `mark`

[kovetskiy/mark](https://github.com/kovetskiy/mark) is a maintained Go binary that does the same job (Markdown to Confluence, page create/update by title, parent pages, local Mermaid rendering to PNG or SVG). Prefer it when:

- you can install a binary (`brew install kovetskiy/mark/mark`, `go install`, or Docker), and
- you don't need the raw REST wrappers in this skill for other calls.

Keep this skill's scripts when you need a PowerShell-only toolchain or want the `conf-api-*.ps1` wrappers for ad hoc API calls.

## Available scripts

- `scripts/md-to-confluence.ps1` - Main entrypoint for Markdown to Confluence publishing.
- `scripts/conf-api-v1.ps1` - Confluence REST API v1 wrapper used for attachment upload.
- `scripts/conf-api-v2.ps1` - Confluence REST API v2 wrapper used for page lookup, create, and update.

The two `conf-api-*.ps1` wrappers are a thin `gh api`-style passthrough: `conf-api-v2.ps1 GET "/pages?title=Foo"` sends an authenticated request and returns the JSON. They work standalone for any Confluence call, not just publishing.

## Setup

1. Export credentials as environment variables (never edit the scripts):

```bash
export CONFLUENCE_SITE="mycompany"        # https://mycompany.atlassian.net
export CONFLUENCE_EMAIL="you@example.com"
export CONFLUENCE_API_TOKEN="..."          # https://id.atlassian.com/manage-profile/security/api-tokens
```

The scripts fail fast with a clear message if any of the three is missing.

2. Ensure required local tools are installed:

```bash
pandoc --version
pwsh --version
```

3. Install Mermaid rendering support.
Preferred path: local `mmdc`.
Fallback path: Docker.

```bash
npm install -g @mermaid-js/mermaid-cli
mmdc --version
```

If local `mmdc` is unavailable or fails, the script falls back to Docker automatically when `docker` is installed.

## Workflow

1. Run a dry run first:

```bash
pwsh ./skills/md-to-confluence/scripts/md-to-confluence.ps1 \
  -File ./input.md \
  -SpaceId 123456789 \
  -Title "My Page Title" \
  -DryRun
```

2. Publish for real:

```bash
pwsh ./skills/md-to-confluence/scripts/md-to-confluence.ps1 \
  -File ./input.md \
  -SpaceId 123456789 \
  -Title "My Page Title"
```

3. Optional: publish under a parent page:

```bash
pwsh ./skills/md-to-confluence/scripts/md-to-confluence.ps1 \
  -File ./input.md \
  -SpaceId MYSPACE \
  -Title "Child Page" \
  -ParentId 987654321
```

4. Ad hoc API calls with the wrappers:

```bash
pwsh ./skills/md-to-confluence/scripts/conf-api-v2.ps1 GET "/spaces?keys=MYSPACE"
pwsh ./skills/md-to-confluence/scripts/conf-api-v2.ps1 GET "/pages?title=My%20Page%20Title&space-id=123456789"
pwsh ./skills/md-to-confluence/scripts/conf-api-v1.ps1 POST "/content/<pageId>/child/attachment" -File ./diagram.png -Header @{ "X-Atlassian-Token" = "no-check" }
```

## What the script does

- Reads the input Markdown file.
- Extracts fenced ```` ```mermaid ```` blocks into temporary `.mmd` files.
- Renders each Mermaid diagram to a PNG.
- Converts the Markdown body to HTML with `pandoc`.
- Replaces Mermaid placeholders with Confluence attachment image macros.
- Looks up an existing page by title in the target space.
- Creates or updates the page.
- Uploads generated diagram PNGs as page attachments.

## Notes

- `-SpaceId` accepts either a numeric space id or a Confluence space key.
- Mermaid rendering order is: local `mmdc` first, Docker second.
- Local `mmdc` still depends on a browser engine such as Chrome or Chromium via Puppeteer.
- If the page title already exists in the target space, the script updates that page instead of creating a new one.
- Temporary files are removed automatically unless `KEEP_TMP=1` is set in the environment.
- Mermaid diagrams are attached as PNG files named `diagram-N.png`.

## Wishlist: a `gh api` for Atlassian

There is no widely adopted, first-party equivalent of `gh api` for Jira and Confluence: one binary, one auth setup, raw REST passthrough with JSON in and JSON out. The `conf-api-*.ps1` wrappers here are a stopgap. Candidates to watch, in order of preference:

- Atlassian's official `acli` (Jira-first, Confluence commands growing). Check whether it has gained a raw `api` subcommand before adding anything here.
- The [Atlassian Rovo MCP server](https://github.com/atlassian/atlassian-mcp-server), when the caller is an agent rather than a shell script.
- [ankitpokhrel/jira-cli](https://github.com/ankitpokhrel/jira-cli) for Jira only. Good for interactive use, no Confluence.

If none of those closes the gap, the next step is a single cross-platform script (Python, `uv run`) covering both Jira and Confluence with the same `METHOD PATH [--data] [--file]` interface as the wrappers above, and this skill should then depend on it.
