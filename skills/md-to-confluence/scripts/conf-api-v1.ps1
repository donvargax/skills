#!/usr/bin/env pwsh

#Requires -Version 7.0
[CmdletBinding()]
param(
	[Parameter(Position = 0, Mandatory)]
	[ValidateSet("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")]
	[string]$Method,

	[Parameter(Position = 1, Mandatory)]
	[string]$Path,

	[string]$Data,
	[string]$File,
	[hashtable]$Header
)

$ErrorActionPreference = "Stop"

# --- Hardcoded config ---
$Site     = ""   # e.g. mycompany
$Email    = ""
$ApiToken = ""
$BaseUrl  = "https://$Site.atlassian.net/wiki/rest/api"

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
	$params.Form = @{
		file      = Get-Item -LiteralPath $File
		minorEdit = "true"
	}
} elseif ($Data) {
	$params.ContentType = "application/json"
	$params.Body        = $Data
}

Invoke-RestMethod @params
