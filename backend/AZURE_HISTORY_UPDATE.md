# Azure VM: durable historical candles and read-only diagnostics

This is a backend-only update. It is NOT automatically deployed to the Azure VM.
It does not replace Android Build 79 or change the Render deployment.

## What changes

* Store only confirmed OHLCV candles under the signed-in Windows user's
  LocalAppData DhanPulse/candles folder. Override with
  DHANPULSE_CANDLE_CACHE_DIR if needed.
* Restore previously confirmed candles after a process restart.
* Recheck currency/freshness at each interval before issuing calls.
* Do not generate trading signals from missing or stale historical data.
* Expose an authenticated, read-only history status endpoint without any
  additional broker request: GET /api/diagnostics/history.
* Keep existing history cooldown and HTTP 403 handling.

## Before upgrading

Stop the backend PowerShell window with Ctrl+C. Keep your saved encrypted
credentials and Desktop launcher as they are. Do not uninstall Android or
delete any credential files.

In a NEW PowerShell window on Azure VM Trade:

    git -C C:\DhanPulsePersonal status --short

If this prints any modified or untracked source files, stop and review them.
Do not run git reset, clean, or forced checkout.

When the repository is clean:

    git -C C:\DhanPulsePersonal fetch origin fix/azure-durable-candles-diagnostics-20261111
    git -C C:\DhanPulsePersonal switch --track -c azure-durable-candle-test origin/fix/azure-durable-candles-diagnostics-20261111
    Set-Location 'C:\DhanPulsePersonal\backend'
    npm.cmd ci --no-audit --no-fund
    npm.cmd test

For a second run after switching to this branch, use:

    git -C C:\DhanPulsePersonal switch azure-durable-candle-test
    git -C C:\DhanPulsePersonal pull --ff-only origin fix/azure-durable-candles-diagnostics-20261111

Start the backend with the EXISTING user-owned encrypted credential launcher:

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:USERPROFILE\Desktop\Start-DhanPulse-Azure-Updated.ps1"

Leave that backend window running.

## After a successful Angel One login

The authenticated diagnostics endpoint requires an existing X-Session-Id.
In your other PowerShell window, after logging in and setting $r.sessionId:

    $diag = Invoke-RestMethod 'http://127.0.0.1:3100/api/diagnostics/history' -Headers @{ 'X-Session-Id' = $r.sessionId }
    $diag.history | Format-List
    $diag.cache.entries | Format-Table -AutoSize

This call does NOT request candles or market quotes from Angel One. It
only reports local rate-limit state, recent local history requests, and
which confirmed candles have been cached. Existing SmartAPI account-wide
restrictions can remain even after the local cooldown has expired.

## Security and limitations

* Never paste MPIN, TOTP, API key, session tokens or encryption key in chat.
* Cache files contain only broker-confirmed OHLCV and timestamps, not credentials.
* LocalAppData contents are governed by that Windows user's filesystem rights.
* The candle cache has bounded retention (up to 1,200 bars per instrument and
  interval). It is NOT an exchange tick-by-tick history service.
* Old cached candles are allowed as research evidence, but never as proof of
  fresh trading eligibility.
* The VM is still listening on loopback. Secure public HTTPS and Android
  connectivity require a separate network configuration and further tests.
* Do not open port 3100 directly to the public internet.
