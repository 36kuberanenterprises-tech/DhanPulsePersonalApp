# DhanPulse Personal App

Latest stable build: **V2.7.1 iOS Market Pro**

DhanPulse is a personal Android market analysis app using **Delta Exchange India production market data** with continuous background monitoring, ICT / liquidity / OB / FVG analysis, BUY / SELL / WAIT decision support, Entry / SL / T1 / T2 / T3 tracking, and preserved trade history.

## Delta API setup inside the app

Do **not** place an API key or secret in GitHub source files.

On the phone:

1. Open DhanPulse.
2. Tap **Account** in the bottom navigation, or tap **ACCOUNT** near the top.
3. Open **Delta Account**.
4. Enter the **Delta API Key** in the first field.
5. Enter the matching **Delta API Secret** in the second field.
6. Tap **Connect & Verify**.
7. Confirm the app shows **CONNECTED**, the account holder / account name when returned by Delta, User ID, Net Equity, Available Balance, and Total Balance.

The key and secret are stored on the Android device using encrypted preferences. They are not committed to this repository.

## Current security / execution status

Public market analysis uses Delta Exchange India production REST and WebSocket endpoints.

Authenticated account verification is read only. The current stable build does **not** automatically submit real money orders.

## Build

The current Android build workflow is:

`.github/workflows/build-crypto-forex-v271.yml`

The V2.7.1 UI patch is:

`v271-patch/apply_v271.py`

The secure Delta account verification layer is implemented by the V2.6.8 and V2.6.9 patches.

## Important

Never commit an API secret, private key, password, or trading credential to this repository. If an API key has been publicly shared, rotate it before using it for authenticated account access.
