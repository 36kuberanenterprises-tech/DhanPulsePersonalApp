# DhanPulse Personal App

Latest crypto build: **V2.7.4 Backend Variables**

## Delta backend variables mode

For the Delta crypto app, the recommended setup is now the same pattern used by DhanPulse Personal: keep long lived API credentials on the backend, not in the APK.

Render service: **dhanpulse-personal-api**

Add these environment variables in Render:

- `DELTA_API_KEY`
- `DELTA_API_SECRET`
- `DELTA_APP_ACCESS_TOKEN`

The first two are your Delta Exchange India production credentials. `DELTA_APP_ACCESS_TOKEN` is a separate private token you create yourself to protect the backend account endpoint. Do not reuse the Delta API secret as this token.

In the Android app, open **Account → Delta Account → Backend Variables**. Enter only the Backend Access Token once and tap **Save Token**, then **Connect Using Backend Variables**.

The APK never receives `DELTA_API_KEY` or `DELTA_API_SECRET` in backend mode. The backend signs Delta account requests and returns only the account summary needed by the app.

The backend route is protected and rate limited. Do not commit any real API key, API secret, access token, password, or trading credential to GitHub.

## Current account features

- Delta Exchange India production public market data
- Account holder / account name when Delta returns it
- Authenticated user ID
- Net equity
- Available balance
- Total balance
- Nonzero wallet balances
- Preserved strategy history
- Continuous market analysis

## Execution status

V2.7.4 is for analysis and authenticated account verification. It does not automatically submit real money orders.

## Build

Workflow:

`.github/workflows/build-crypto-forex-v274.yml`

UI/backend-mode patch:

`v274-patch/apply_v274.py`

Backend Delta client:

`backend/src/delta.js`
