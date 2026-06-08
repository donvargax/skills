#!/usr/bin/env pwsh

#Requires -Version 7.0
[CmdletBinding()]
param(
	[Parameter(Position = 0)]
	[ValidateSet("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")]
	[string]$Method = "GET",

	[Parameter(Position = 1, Mandatory)]
	[string]$Path,

	# JSON string payload (non-multipart)
	[string]$Data,

	# File to upload as multipart/form-data
	[string]$File,

	# Extra headers, e.g. @{ "X-Atlassian-Token" = "no-check" }
	[hashtable]$Header
)

$ErrorActionPreference = "Stop"

# --- Hardcoded config ---
$Site     = ""   # e.g. mycompany
$Email    = ""
$ApiToken = ""
$BaseUrl  = "https://$Site.atlassian.net/wiki/api/v2"

$pair = "$Email`:$ApiToken"
$auth = "Basic " + [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($pair))

$headers = @{
	Authorization = $auth
	Accept        = "application/json"
}
if ($Header) {
	foreach ($k in $Header.Keys) {
		$headers[$k] = $Header[$k] 
	}
}

$params = @{
	Uri     = "$BaseUrl$Path"
	Method  = $Method
	Headers = $headers
}

if ($File) {
	# multipart: do NOT set Content-Type, PS handles the boundary
	$params.Form = @{
		file      = Get-Item -LiteralPath $File
		minorEdit = "true"
	}
} elseif ($Data) {
	$params.ContentType = "application/json"
	$params.Body        = $Data
}

Invoke-RestMethod @params
