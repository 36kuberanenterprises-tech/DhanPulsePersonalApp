# DhanPulse Personal v2.9.6

Historical requests share a client budget across index analysis, scanner and backtesting in this backend process. Identical requests share one in flight operation. The connector checks date ranges before sending, preserves HTTP status and Retry After, and applies progressively longer cooldowns after rate rejection. Other applications and server instances are outside this process budget.

All indices and MCX analysis now require a current completed broker candle. Quote samples cannot replace missing historical bars. Missing history preserves reference quotes and reports an explicit history failure. Symbol changes discard outdated failures and successful responses. Scanner and broker requests have bounded network timeouts; backtests retain a longer Android read timeout.

The six Sensex strategy families and existing order permissions are unchanged. No live orders were placed as part of verification. Live candle HTTP 403 is not considered solved until Angel One accepts a request. Existing order IP mismatch protection remains active.

Validation: backend automated tests and Android build are required before publishing. Version name, installer label and APK filename use 2.9.6, Android version code 49.
