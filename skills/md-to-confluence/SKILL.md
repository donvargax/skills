---
name: md-to-confluence
description: Publish Markdown documents to Confluence, rendering Mermaid blocks to attached PNGs before create or update.
hidden: false
---

# md-to-confluence

Use this skill to convert a Markdown document into Confluence storage HTML, render Mermaid code blocks to images, and create or update a Confluence page.

## Available scripts

- `scripts/md-to-confluence.ps1` - Main entrypoint for Markdown to Confluence publishing.
- `scripts/conf-api-v1.ps1` - Confluence REST API v1 wrapper used for attachment upload.
- `scripts/conf-api-v2.ps1` - Confluence REST API v2 wrapper used for page lookup, create, and update.

## Workflow

1. Set the Confluence site, email, and API token in both API wrapper scripts:

```powershell
# skills/md-to-confluence/scripts/conf-api-v1.ps1
$Site     = ""
$Email    = ""
$ApiToken = ""

# skills/md-to-confluence/scripts/conf-api-v2.ps1
$Site     = ""
$Email    = ""
$ApiToken = ""
```

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

4. Run a dry run first:

```bash
pwsh ./skills/md-to-confluence/scripts/md-to-confluence.ps1 \
  -File ./input.md \
  -SpaceId 123456789 \
  -Title "My Page Title" \
  -DryRun
```

5. Publish for real:

```bash
pwsh ./skills/md-to-confluence/scripts/md-to-confluence.ps1 \
  -File ./input.md \
  -SpaceId 123456789 \
  -Title "My Page Title"
```

6. Optional: publish under a parent page:

```bash
pwsh ./skills/md-to-confluence/scripts/md-to-confluence.ps1 \
  -File ./input.md \
  -SpaceId MYSPACE \
  -Title "Child Page" \
  -ParentId 987654321
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
- The API wrapper scripts currently use hardcoded credentials; keep that in mind before sharing or committing real values.
