# Azure recovery for 13 November DhanPulse video

This branch is a testing candidate, not a live deployment. It retains the
existing Azure authentication and order-safety policies. It neither creates
candles from quote samples nor circumvents Angel One historical API denial.

## Improvements

1. Restore previously received broker-confirmed candles across Node.js
   restarts. Restored candles remain stale until a current completed broker
   candle is actually received.
2. Authenticated read-only endpoint GET /api/diagnostics/history with
   historical access cooldown, last HTTP status, recent request counters,
   last success and rejection, and confirmed candle cache information.
   This endpoint never makes a broker request.
3. Restart a disconnected Flow WebSocket only after at least a 15-second
   pause while Android polling continues. No live orders are involved.
4. No changes to Render main or to broker static IP registration.

## Important limitation

Angel One HTTP 403 "Access denied because of exceeding access rate" may be
an account-wide broker restriction. Source changes, caching and an Azure VM
cannot guarantee restored historical access. If 403 continues, ask SmartAPI
support to check history permission and account-side throttling.

## Safely test on the current Windows Azure VM

In PowerShell, first inspect the existing directory and changes. Do not
reveal credentials in screenshots or paste them in chat.

    git -C C:\DhanPulsePersonal status --short

Do not reset, clean, overwrite or switch a dirty live checkout.

In a *separate* PowerShell window, fetch and create an isolated test folder:

    git -C C:\DhanPulsePersonal fetch origin fix/azure-flow-history-recovery-20261113
    git -C C:\DhanPulsePersonal worktree add C:\DhanPulseVideoTest origin/fix/azure-flow-history-recovery-20261113
    Set-Location C:\DhanPulseVideoTest\backend
    npm.cmd ci --no-audit --no-fund
    npm.cmd test

This does NOT start a second broker login or trading process. Do not copy
credential files into the test directory.

After tests pass, the Windows Azure backend itself still needs a controlled
deployment through the user's existing launcher and saved private credential
configuration. Prepare a rollback to the current installed commit first.
The current production process should be stopped only during an approved
maintenance window, and the new code should use the existing account-owned
secrets without exposing them. Verify the API locally before changing the
Android endpoint.

Do not expose TCP 3100 publicly or bypass existing HTTPS/Tailscale security.

## Diagnostics after Azure deployment and signed-in login

Using the existing application session, read
GET https://<your-private-azure-host>/api/diagnostics/history with the
existing authenticated X-Session-Id header. Never publish the session value.

The response identifies current local cooldown. A zero cooldown does NOT
prove that Angel One history access is restored; verify by receiving a
new completed candle with a matching broker timestamp.

## Testing order

1. Verify Azure /health and /api/auth/readiness.
2. Verify Angel One login and the /api/diagnostics/history endpoint.
3. Verify fresh NSE NIFTY and BANKNIFTY confirmed 5-minute candles.
4. Verify MCX futures candles and valid option quotes.
5. Verify Keep Eye selection, daily scanner, and live movers separately.
6. Verify Flow disconnect/reconnect with a nontrading instrument.
7. Verify Backtest no longer repeats a rejected request during a cooldown.
8. Verify read-only monitoring and stop behaviour.
9. Keep all live orders disabled until separately tested.
