# DhanPulse Azure private HTTPS endpoint
# Run on the same Windows VM where the existing local backend is running.
# Do not place API keys, MPIN, TOTP, or session tokens in this script.
# No Azure public inbound firewall rule is needed.
$ErrorActionPreference = 'Stop'
$backend = 'http://127.0.0.1:3100'

Write-Host 'Checking the EXISTING Azure backend...' -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod "$backend/health" -TimeoutSec 15
    $ready = Invoke-RestMethod "$backend/api/auth/readiness" -TimeoutSec 15
    if (-not $health.ok -or -not $ready.loginReady) {
        throw "Backend is available, but login is not configured. Health: $($health.ok) LoginReady: $($ready.loginReady)"
    }
} catch {
    Write-Host 'Backend not ready. Start your existing Start-DhanPulse-Azure-Updated.ps1 first.' -ForegroundColor Red
    throw
}
Write-Host 'Local Azure backend and login readiness are OK.' -ForegroundColor Green

$command = Get-Command tailscale.exe -ErrorAction SilentlyContinue
$exe = if ($command) { $command.Source } else { Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe' }
if (-not (Test-Path $exe)) {
    Write-Host 'Tailscale is not installed. Install it from https://tailscale.com/download/windows and sign in using your own account.' -ForegroundColor Yellow
    exit 1
}

Write-Host 'Checking Tailscale account...' -ForegroundColor Cyan
& $exe status
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Sign in from the Tailscale icon in the Windows system tray, then run this script again.' -ForegroundColor Yellow
    exit 1
}

Write-Host 'Enabling PRIVATE tailnet HTTPS forwarding to 127.0.0.1:3100...' -ForegroundColor Cyan
& $exe serve --bg 3100
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Complete any Tailscale HTTPS/Serve approval shown in the browser, then retry.' -ForegroundColor Yellow
    exit 1
}

Write-Host ''
Write-Host 'Private HTTPS URL and proxy status:' -ForegroundColor Green
& $exe serve status
Write-Host ''
Write-Host 'Copy the https://...ts.net URL above into DhanPulse Build 80 on your Android phone.' -ForegroundColor Green
Write-Host 'Your phone must be signed into the same Tailscale tailnet with Tailscale connected.' -ForegroundColor Yellow
Write-Host 'Keep the existing DhanPulse backend running. Do not open public port 3100.' -ForegroundColor Yellow
