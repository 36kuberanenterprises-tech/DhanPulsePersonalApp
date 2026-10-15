# DhanPulse Personal v2.9.8

Tab and refresh corrections:
- One active tab now controls refresh requests; switching Stocks and Options no longer briefly starts an unrelated analysis refresh.
- Account and Positions refresh every 15 seconds while the app is visible. Account calls are coalesced in the app; failures are visible and clear the displayed balance. Session changes discard older responses.
- Account diagnostics use a separate 60 second timer. Explicit refresh remains available.
- Existing SENSEX 1 second checks, other index/MCX 3 second checks and scanner/option 15 second checks remain. Closed market reads use 60 seconds; stock hours are independent of the previously selected MCX tab.
- Eight horizontally scrollable navigation buttons show full labels, with larger touch targets.
- Account shows actual request duration and last successful update. This is measured elapsed time, not a claim of 10 millisecond broker latency.
- Duplicate backtest submissions are blocked while a run is active.

Validation: 66 backend tests pass, including protected routes and simulated broker account failure. Android assembly is checked in CI. No live orders are submitted by validation.

Trading strategies, entry thresholds and order safety checks are unchanged. Live authenticated broker success and clearing HTTP 403 are not confirmed by these tests. Broker history remains subject to access and rate restrictions.
