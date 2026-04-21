<#
.SYNOPSIS
  Install fcop MCP into Cursor on Windows.

.DESCRIPTION
  Idempotent one-shot installer:
    1. Installs `uv` (via winget) if missing
    2. Merges fcop entry into %USERPROFILE%\.cursor\mcp.json
       (preserves other MCP servers already configured)
    3. Prints restart instructions

.EXAMPLE
  irm https://raw.githubusercontent.com/joinwell52-AI/codeflow-pwa/main/codeflow-plugin/scripts/install-fcop.ps1 | iex
#>

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== fcop MCP installer ===" -ForegroundColor Cyan
Write-Host ""

# --- 1. Ensure uv -------------------------------------------------------------
function Test-Uv { return [bool](Get-Command uvx -ErrorAction SilentlyContinue) }

if (Test-Uv) {
    Write-Host "[1/3] uv already installed: $(uvx --version)" -ForegroundColor Green
} else {
    Write-Host "[1/3] Installing uv via winget..." -ForegroundColor Yellow
    try {
        winget install -e --id astral-sh.uv --accept-package-agreements --accept-source-agreements | Out-Null
    } catch {
        Write-Host "[!] winget install failed. Fallback to official script..." -ForegroundColor Yellow
        irm https://astral.sh/uv/install.ps1 | iex
    }
    # Refresh PATH for this session so `uvx` is callable immediately
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    if (-not (Test-Uv)) {
        throw "uv installation failed. Please install manually from https://docs.astral.sh/uv/ and re-run."
    }
    Write-Host "    uv installed: $(uvx --version)" -ForegroundColor Green
}

# --- 2. Prepare mcp.json ------------------------------------------------------
$cursorDir = Join-Path $env:USERPROFILE ".cursor"
$mcpPath   = Join-Path $cursorDir "mcp.json"
New-Item -ItemType Directory -Force -Path $cursorDir | Out-Null

$existing = $null
if ((Test-Path $mcpPath) -and ((Get-Item $mcpPath).Length -gt 0)) {
    try {
        $raw = Get-Content $mcpPath -Raw -Encoding UTF8
        if ($raw.Trim().Length -gt 0) {
            $existing = $raw | ConvertFrom-Json
        }
    } catch {
        $ts = Get-Date -Format "yyyyMMdd-HHmmss"
        $backup = "$mcpPath.bak.$ts"
        Copy-Item $mcpPath $backup -Force
        Write-Host "[!] Existing mcp.json is invalid JSON. Backed up to:" -ForegroundColor Yellow
        Write-Host "    $backup" -ForegroundColor Yellow
        $existing = $null
    }
}

if ($null -eq $existing) {
    $existing = [pscustomobject]@{ mcpServers = [pscustomobject]@{} }
}
if ($null -eq $existing.mcpServers) {
    $existing | Add-Member -NotePropertyName mcpServers `
        -NotePropertyValue ([pscustomobject]@{}) -Force
}

$fcopEntry = [pscustomobject]@{
    command = "uvx"
    args    = @("fcop")
}

$hadFcop = [bool]($existing.mcpServers.PSObject.Properties["fcop"])
$existing.mcpServers | Add-Member -NotePropertyName fcop `
    -NotePropertyValue $fcopEntry -Force

$json = $existing | ConvertTo-Json -Depth 10
[System.IO.File]::WriteAllText($mcpPath, $json, (New-Object System.Text.UTF8Encoding $false))

if ($hadFcop) {
    Write-Host "[2/3] fcop entry refreshed in: $mcpPath" -ForegroundColor Green
} else {
    Write-Host "[2/3] fcop added to: $mcpPath" -ForegroundColor Green
}

# --- 3. Done ------------------------------------------------------------------
Write-Host ""
Write-Host "[3/3] All done." -ForegroundColor Green
Write-Host ""
Write-Host "Next step: completely quit Cursor (including tray icon) and restart it." -ForegroundColor Cyan
Write-Host "First tool call will lazy-download fcop from PyPI (~30-90s), then cached." -ForegroundColor DarkGray
Write-Host ""
