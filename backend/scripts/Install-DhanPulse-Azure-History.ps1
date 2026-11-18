<#
Safely stage and optionally install the existing DhanPulse Azure historical
diagnostics backend. Run ONLY on the Windows Azure VM that already hosts DhanPulse.
Does not modify API credentials, registered IP, Tailscale, Render, or other services.

Examples:
  powershell -NoProfile -File .\Install-DhanPulse-Azure-History.ps1
  powershell -NoProfile -File .\Install-DhanPulse-Azure-History.ps1 -Apply

For -Apply, stop ONLY the DhanPulse service first using its existing
launcher/service mechanism. The script refuses to touch an active port 3100.
#>
param(
    [switch]$Apply,
    [string]$RepoRoot = "C:\DhanPulsePersonal",
    [string]$Branch = "fix/angel403-history-diagnostics-20261118"
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Run-Checked {
    param([string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Exe failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path (Join-Path $RepoRoot '.git'))) {
    throw "DhanPulse checkout not found at $RepoRoot. No changes made."
}
if (-not (Get-Command git -ErrorAction SilentlyContinue) -or
    -not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
    throw "git and npm.cmd are required. No changes made."
}

$dirty = @(git -C $RepoRoot status --porcelain)
if ($LASTEXITCODE -ne 0) { throw "Unable to inspect Git checkout. No changes made." }
if ($dirty.Count -gt 0) {
    throw "Working checkout contains changes. Review them before updating. No files were overwritten."
}
$previous = (git -C $RepoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw "Unable to identify rollback commit." }

Run-Checked 'git' @('-C', $RepoRoot, 'fetch', 'origin', $Branch)
$stage = Join-Path $env:TEMP 'DhanPulseHistoryDiagnosticsStage'
if (Test-Path $stage) {
    throw "Staging path already exists: $stage. Inspect it before retrying. Production was not changed."
}
Run-Checked 'git' @('-C', $RepoRoot, 'worktree', 'add', '--detach', $stage, ("origin/" + $Branch))
try {
    Push-Location (Join-Path $stage 'backend')
    try {
        Run-Checked 'npm.cmd' @('ci', '--no-audit', '--no-fund')
        Run-Checked 'npm.cmd' @('test')
    } finally { Pop-Location }
    Write-Host 'Staged backend tests PASSED.' -ForegroundColor Green
} catch {
    Write-Error "Staging failed; production checkout is unchanged. $($_.Exception.Message)"
    throw
}
if (-not $Apply) {
    Write-Host 'Production is UNCHANGED. To install, stop only the DhanPulse backend, then rerun this script with -Apply.'
    exit 0
}

$tcp = Get-NetTCPConnection -State Listen -LocalPort 3100 -ErrorAction SilentlyContinue
if ($tcp) {
    throw "Port 3100 is still listening. Stop ONLY the existing DhanPulse backend before applying; no production changes made."
}

$rollbackFile = Join-Path $env:TEMP 'DhanPulseAzurePreviousCommit.txt'
Set-Content -Path $rollbackFile -Value $previous -Encoding UTF8
Write-Host "Previous backend revision recorded in $rollbackFile"
try {
    Run-Checked 'git' @('-C', $RepoRoot, 'switch', '--detach', ("origin/" + $Branch))
    Push-Location (Join-Path $RepoRoot 'backend')
    try {
        Run-Checked 'npm.cmd' @('ci', '--no-audit', '--no-fund')
        Run-Checked 'npm.cmd' @('test')
    } finally { Pop-Location }
    Write-Host 'Azure backend code installed. Existing private login launcher must be started.' -ForegroundColor Green
    Write-Host 'No credentials, IP settings or broker permissions were modified.'
} catch {
    Write-Warning "Install failed. Restoring prior Git revision $previous."
    Run-Checked 'git' @('-C', $RepoRoot, 'switch', '--detach', $previous)
    Write-Warning 'Previous source revision restored. Check dependencies and restart the original backend through its established launcher.'
    throw
}
