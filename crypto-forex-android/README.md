# DhanPulse Crypto and Forex Android

Separate Android analysis app.

Version 1.0.0

Package: com.dhanpulse.cryptoforex

Crypto market data comes from Binance Futures public REST and WebSocket endpoints. No broker login or API key is required.

XAUUSD and forex data uses Twelve Data. The API key is stored locally on the Android device.

The app analyses EMA 9, EMA 15, EMA slope, Supertrend, RSI, MACD, ATR, Bollinger Bands, VWAP where real volume is available, support, resistance, candle structure, higher timeframe direction, and crypto derivatives context including open interest, funding rate and order book imbalance.

Signals are BUY, SELL or WAIT. Valid signals include Entry, Stop Loss, Target 1, Target 2 and Target 3.

Signals are simulated analysis only. They are recorded locally and subsequent real candles are used to calculate T1, T2, T3 and Stop Loss performance.

No orders are placed.
