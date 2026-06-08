#!/usr/bin/env pwsh

#Requires -Version 7.0
<#
  md-to-confluence.ps1
  Converts Markdown (+ mermaid blocks) to a Confluence page with attached
  PNG diagrams.

  Usage:
    ./md-to-confluence.ps1 `
      -File ./input.md `
      -SpaceId 123456789 `
      -Title "Title"

  Optional:
    -ParentId 987654321
    -DryRun
#>

[CmdletBinding()]
param(
	[Parameter(Mandatory)][string]$File,
	[Parameter(Mandatory)][string]$SpaceId,   # numeric id OR space key (incl. ~personal)
	[Parameter(Mandatory)][string]$Title,
	[string]$ParentId,
	[switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

# Resolve the wrapper scripts (expected next to this one)
$ConfApiV1 = Join-Path $PSScriptRoot "conf-api-v1.ps1"
$ConfApiV2 = Join-Path $PSScriptRoot "conf-api-v2.ps1"

if (-not (Test-Path -LiteralPath $File)) {
	throw "Markdown file not found: $File"
}

foreach ($cmd in @("pandoc")) {
	if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
		throw "Missing dependency: $cmd"
	}
}

$MmdcCmd   = Get-Command "mmdc" -ErrorAction SilentlyContinue
$DockerCmd = Get-Command "docker" -ErrorAction SilentlyContinue

function Get-MmdcBrowserPath {
	if ($env:PUPPETEER_EXECUTABLE_PATH) {
		return $env:PUPPETEER_EXECUTABLE_PATH
	}

	foreach ($name in @(
		"google-chrome-stable",
		"google-chrome",
		"chromium",
		"chromium-browser",
		"microsoft-edge",
		"msedge"
	)) {
		$cmd = Get-Command $name -ErrorAction SilentlyContinue
		if ($cmd) {
			return $cmd.Source
		}
	}

	foreach ($path in @(
		"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
		"/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
		"C:\Program Files\Google\Chrome\Application\chrome.exe",
		"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
		"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
		"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
	)) {
		if (Test-Path -LiteralPath $path) {
			return $path
		}
	}

	return $null
}

# --- Resolve space key -> space id if needed ---
$SpaceInput = $SpaceId
if ($SpaceInput -match '^\d+$') {
	$SpaceId = $SpaceInput
} else {
	$encKey    = [uri]::EscapeDataString($SpaceInput)
	$spaceJson = & $ConfApiV2 GET "/spaces?keys=$encKey&limit=1"
	$SpaceId   = $spaceJson.results | Select-Object -First 1 -ExpandProperty id -ErrorAction SilentlyContinue
	if (-not $SpaceId) {
		throw "Could not resolve space key '$SpaceInput' to space id"
	}
}

# --- Temp workspace ---
$TmpDir  = Join-Path ([IO.Path]::GetTempPath()) ("md2conf-" + [Guid]::NewGuid())
New-Item -ItemType Directory -Path $TmpDir | Out-Null
$KeepTmp = $env:KEEP_TMP -eq "1"

try {
	$MdWork     = Join-Path $TmpDir "input.md"
	$MermaidDir = Join-Path $TmpDir "mermaid"
	$ImgDir     = Join-Path $TmpDir "images"
	$HtmlRaw    = Join-Path $TmpDir "body_raw.html"
	$HtmlFinal  = Join-Path $TmpDir "body_final.html"

	New-Item -ItemType Directory -Path $MermaidDir, $ImgDir | Out-Null
	Copy-Item -LiteralPath $File -Destination $MdWork

	# --- Extract mermaid blocks ---
	Write-Host "==> Extracting mermaid blocks..."
	$text  = Get-Content -LiteralPath $MdWork -Raw
	$count = 0
	$MermaidOutputDir = $MermaidDir
	$pattern = '(?s)```mermaid\s*\r?\n(.*?)```'
	$newText = [regex]::Replace($text, $pattern, {
			param($m)
			$script:count++
			$content = $m.Groups[1].Value.Trim() + "`n"
			$out = Join-Path $MermaidOutputDir "diagram-$($script:count).mmd"
			Set-Content -LiteralPath $out -Value $content -NoNewline -Encoding utf8
			"`n@@MERMAID_$($script:count)@@`n"
		})
	Set-Content -LiteralPath $MdWork -Value $newText -Encoding utf8

	$mmdFiles     = @(Get-ChildItem -Path $MermaidDir -Filter *.mmd -ErrorAction SilentlyContinue)
	$MermaidCount = $mmdFiles.Count
	Write-Host "Found mermaid diagrams: $MermaidCount"

	# --- Render mermaid diagrams to PNG ---
	if ($MermaidCount -gt 0) {
		if (-not $MmdcCmd -and -not $DockerCmd) {
			throw "Mermaid rendering requires either 'mmdc' or 'docker'"
		}

		Write-Host "==> Rendering mermaid diagrams to PNG..."
		$cfg = Join-Path $TmpDir "mermaid-config.json"
		$BrowserPath = Get-MmdcBrowserPath
		$PuppeteerCfg = $null
		@'
{
  "securityLevel": "loose"
}
'@ | Set-Content -LiteralPath $cfg -Encoding utf8

		if ($BrowserPath) {
			$PuppeteerCfg = Join-Path $TmpDir "puppeteer-config.json"
			@{
				executablePath = $BrowserPath
			} | ConvertTo-Json | Set-Content -LiteralPath $PuppeteerCfg -Encoding utf8
			Write-Host "Using browser for local mmdc: $BrowserPath"
		} elseif ($MmdcCmd) {
			Write-Warning "No local Chrome/Chromium/Edge detected for mmdc; local rendering may fail before Docker fallback."
		}

		foreach ($mmd in $mmdFiles) {
			$png = Join-Path $ImgDir "$($mmd.BaseName).png"
			$rendered = $false

			if ($MmdcCmd) {
				Write-Host "Trying local mmdc for $($mmd.Name)..."
				$mmdcArgs = @(
					"--iconPacks", "@iconify-json/logos", "@iconify-json/mdi",
					"-i", $mmd.FullName,
					"-o", $png,
					"-b", "transparent",
					"-c", $cfg
				)
				if ($PuppeteerCfg) {
					$mmdcArgs += @("-p", $PuppeteerCfg)
				}

				& $MmdcCmd.Source @mmdcArgs

				if ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath $png)) {
					$rendered = $true
				} elseif ($DockerCmd) {
					Write-Warning "Local mmdc failed for $($mmd.Name); falling back to Docker."
				} else {
					throw "Local mmdc failed for $($mmd.Name) and docker is not available"
				}
			}

			if (-not $rendered) {
				$uidArgs = @()
				if (-not $IsWindows) {
					$uid = (& id -u).Trim()
					$gid = (& id -g).Trim()
					$uidArgs = @("-u", "$uid`:$gid")
				}

				Write-Host "Using Docker mermaid-cli for $($mmd.Name)..."
				& $DockerCmd.Source run --rm @uidArgs `
					-v "$TmpDir`:$TmpDir" -w $TmpDir `
					minlag/mermaid-cli `
					--iconPacks "@iconify-json/logos" "@iconify-json/mdi" `
					-i $mmd.FullName -o $png -b transparent -c $cfg

				if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $png)) {
					throw "mermaid rendering failed for $($mmd.Name)"
				}
			}

			Write-Host "Rendered: $png"
		}
	}

	# --- Markdown -> HTML ---
	Write-Host "==> Converting Markdown to HTML..."
	pandoc $MdWork -f gfm -t html5 --wrap=none -o $HtmlRaw
	if ($LASTEXITCODE -ne 0) {
		throw "pandoc conversion failed"
	}

	# --- Inject Confluence image macros ---
	Write-Host "==> Injecting Confluence image macros..."
	$html = Get-Content -LiteralPath $HtmlRaw -Raw
	$html = [regex]::Replace($html, '@@MERMAID_(\d+)@@', {
			param($m)
			$fn = "diagram-$($m.Groups[1].Value).png"
			'<p><ac:image ac:alt="' + $fn + '">' +
			'<ri:attachment ri:filename="' + $fn + '" />' +
			'</ac:image></p>'
		})
	Set-Content -LiteralPath $HtmlFinal -Value $html -Encoding utf8

	$BodyValue = Get-Content -LiteralPath $HtmlFinal -Raw

	# --- Find existing page by title ---
	$encTitle   = [uri]::EscapeDataString($Title)
	Write-Host "==> Looking for existing page by title..."
	$searchJson = & $ConfApiV2 GET "/pages?title=$encTitle&limit=250"

	$PageId = $searchJson.results |
		Where-Object { "$($_.spaceId)" -eq "$SpaceId" } |
		Select-Object -First 1 -ExpandProperty id -ErrorAction SilentlyContinue

	if (-not $PageId) {
		Write-Host "==> Page not found. Creating..."
		$payload = [ordered]@{
			spaceId = $SpaceId
			status  = "current"
			title   = $Title
			body    = @{ representation = "storage"; value = $BodyValue }
		}
		if ($ParentId) {
			$payload.parentId = $ParentId
		}

		$createPayload = $payload | ConvertTo-Json -Depth 10

		if ($DryRun) {
			Write-Host "[DRY RUN] Would create page with payload:"
			Write-Host $createPayload
			return
		}

		$createResp = & $ConfApiV2 POST "/pages" -Data $createPayload
		$PageId = $createResp.id
		Write-Host "Created page id: $PageId"
	} else {
		Write-Host "==> Page exists (id: $PageId). Updating..."
		$pageJson = & $ConfApiV2 GET "/pages/$PageId?include-version=true"
		$curVer   = if ($pageJson.version.number) {
			$pageJson.version.number
		} else {
			1
		}
		$nextVer  = [int]$curVer + 1

		$updatePayload = [ordered]@{
			id      = $PageId
			status  = "current"
			title   = $Title
			version = @{ number = $nextVer }
			body    = @{ representation = "storage"; value = $BodyValue }
		} | ConvertTo-Json -Depth 10

		if ($DryRun) {
			Write-Host "[DRY RUN] Would update page id $PageId with payload:"
			Write-Host $updatePayload
			return
		}

		& $ConfApiV2 PUT "/pages/$PageId" -Data $updatePayload | Out-Null
		Write-Host "Updated page id: $PageId (version $nextVer)"
	}

	# --- Upload diagram attachments (v1) ---
	if ($MermaidCount -gt 0) {
		Write-Host "==> Uploading diagram attachments (v1)..."
		foreach ($png in Get-ChildItem -Path $ImgDir -Filter *.png) {
			& $ConfApiV1 POST "/content/$PageId/child/attachment" `
				-File $png.FullName `
				-Header @{ "X-Atlassian-Token" = "no-check" } | Out-Null
			Write-Host "Attached: $($png.Name)"
		}
	}

	# --- Verification ---
	Write-Host "==> Verification"
	Write-Host "Page ID: $PageId"

	Write-Host "==> Check page body (v2)"
	$verify = & $ConfApiV2 GET "/pages/$PageId?body-format=storage"
	Write-Host $verify.title
	Write-Host $verify.version.number

	Write-Host "==> Check attachments on page (v1)"
	$attach = & $ConfApiV1 GET "/content/$PageId/child/attachment?limit=200"
	foreach ($a in $attach.results) {
		$media = if ($a.metadata.mediaType) {
			$a.metadata.mediaType
		} else {
			"-"
		}
		$size  = if ($a.extensions.fileSize) {
			$a.extensions.fileSize
		} else {
			0
		}
		Write-Host ("{0}`t{1}`t{2}`t{3}" -f $a.id, $a.title, $media, $size)
	}

	$Site = ""   # e.g. mycompany
	Write-Host "==> Page attachments URL"
	Write-Host "https://$Site.atlassian.net/wiki/pages/viewpageattachments.action?pageId=$PageId"

	Write-Host "==> Done."
	Write-Host "Page ID: $PageId"
	Write-Host "Tip: open in Confluence and verify diagram rendering + page layout."
} finally {
	if (-not $KeepTmp) {
		Remove-Item -LiteralPath $TmpDir -Recurse -Force -ErrorAction SilentlyContinue
	}
}
