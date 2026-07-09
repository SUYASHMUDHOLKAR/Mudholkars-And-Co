# Stock Trend Agent

Automated daily stock market trend tracker using **yfinance** (free, no key) and **Alpha Vantage** (free key for technical indicators).

Tracks global indices, top US stocks, commodities, forex, and crypto. Fires alerts on unusual events every 15 minutes and generates a full end-of-day report.

---

## What It Tracks

| Category         | Examples                                      |
|------------------|-----------------------------------------------|
| US Indices       | S&P 500, NASDAQ, DJIA, Russell 2000           |
| Volatility       | VIX (Fear Index)                              |
| Asia-Pacific     | Nifty 50, Sensex, Nikkei 225, Hang Seng, KOSPI |
| Europe           | FTSE 100, DAX 40, CAC 40, Euro Stoxx 50       |
| Commodities      | Gold, Crude Oil, Silver, Natural Gas          |
| Forex            | EUR/USD, GBP/USD, USD/JPY, USD/INR            |
| Crypto           | Bitcoin, Ethereum                             |
| Top US Stocks    | AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA    |

---

## Alert Types

| Alert                  | Severity | Trigger                                      |
|------------------------|----------|----------------------------------------------|
| EXTREME_PRICE_MOVE     | EXTREME  | Price move >= 5% in a session                |
| CRITICAL_PRICE_MOVE    | CRITICAL | Price move >= 3%                             |
| VOLUME_SPIKE           | WARNING  | Volume >= 2x 30-day average                  |
| EXTREME_VOLUME_SPIKE   | CRITICAL | Volume >= 3.5x 30-day average                |
| GAP_UP / GAP_DOWN      | WARNING  | Open >= 1.5% from previous close             |
| NEAR_52W_HIGH/LOW      | INFO     | Price within 2% of 52-week high or low       |
| VIX_EXTREME_FEAR       | EXTREME  | VIX >= 40                                    |
| VIX_HIGH_FEAR          | CRITICAL | VIX >= 30                                    |
| RSI_OVERBOUGHT         | WARNING  | RSI >= 70                                    |
| RSI_OVERSOLD           | WARNING  | RSI <= 30                                    |
| MACD_BULLISH_CROSSOVER | INFO     | MACD line crosses above signal line          |
| MACD_BEARISH_CROSSOVER | WARNING  | MACD line crosses below signal line          |
| BOLLINGER_BREACH       | WARNING  | Price breaks outside Bollinger Bands         |
| GOLDEN_CROSS           | INFO     | 50-day MA crosses above 200-day MA           |
| DEATH_CROSS            | CRITICAL | 50-day MA crosses below 200-day MA           |
| GLOBAL_SELLOFF         | EXTREME  | 5+ symbols down simultaneously               |

---

## Schedule

| Cycle        | Interval    | What happens                                      |
|--------------|-------------|---------------------------------------------------|
| Price cycle  | Every 15min | Fetch OHLCV for all symbols, run alert engine     |
| Indicator    | Every 1hr   | Fetch RSI, MACD, EMA, Bollinger from Alpha Vantage |
| EOD Report   | 18:00 IST   | Full JSON + TXT daily report saved to reports/    |

---

## Project Structure

```
stock-trend-agent/
├── agent.py                        # Main scheduler — run this
├── requirements.txt                # Python dependencies
├── config/
│   └── tracking_config.json        # Tickers, thresholds, schedule, API key
├── trackers/
│   ├── price_tracker.py            # yfinance: OHLCV, volume, 52-week, MAs
│   ├── indicator_tracker.py        # Alpha Vantage: RSI, MACD, EMA, Bollinger, ADX
│   └── alert_engine.py             # Detects unusual events, fires alerts
├── data/
│   └── important_exchanges.json    # 25 global exchanges with metadata
├── reports/                        # EOD reports saved here (JSON + TXT)
└── logs/                           # Daily log files
```

---

## Setup

### 1. Install Python dependencies

```bash
cd stock-trend-agent
pip install -r requirements.txt
```

### 2. Get a free Alpha Vantage API key

- Go to: https://www.alphavantage.co/support/#api-key
- Sign up for free (takes 30 seconds)
- Free tier: **25 API calls/day**, 5 calls/minute

### 3. Add your API key to config

Open `config/tracking_config.json` and replace:

```json
"alpha_vantage": "YOUR_ALPHA_VANTAGE_API_KEY"
```

with your actual key:

```json
"alpha_vantage": "ABC123XYZ"
```

> **Note:** yfinance requires no API key — it works out of the box.

---

## Usage

### Run continuously (recommended)

```bash
python agent.py
```

Runs the 15-min + 1-hour cycles indefinitely. Press Ctrl+C to stop.

### Test with a single cycle

```bash
python agent.py --once
```

Runs one price cycle + one indicator cycle, then exits. Good for testing your setup.

### Generate today's EOD report immediately

```bash
python agent.py --report-only
```

Fetches all data now and writes `reports/report_YYYY-MM-DD.json` and `.txt`.

### Use a different config file

```bash
python agent.py --config path/to/my_config.json
```

---

## Output

### Console (live)

```
2026-07-10 09:30:01 | INFO     | --- 15-MIN PRICE CYCLE | 09:30:01 ---
2026-07-10 09:30:04 | INFO     | [^GSPC] Price: 5432.10 | Change: -1.82% | Vol ratio: 2.3x
2026-07-10 09:30:04 | WARNING  | CRITICAL | ^GSPC       | Critical move -1.82% (DOWN)
2026-07-10 09:30:04 | WARNING  | WARNING  | ^GSPC       | Volume spike: 2.3x average
```

### EOD Report (TXT)

```
=================================================================
  STOCK TREND AGENT — DAILY REPORT
  Date: 2026-07-10  |  Generated: 2026-07-10T12:30:00Z
=================================================================

MARKET OVERVIEW
----------------------------------------
  Total tracked : 38
  Gainers        : 21
  Losers         : 14
  Unchanged      : 3

TOP GAINERS
----------------------------------------
  NVDA          +4.21%  @ 142.50
  BTC-USD       +3.10%  @ 68200.00

TOP LOSERS
----------------------------------------
  ^VIX          -8.50%  @ 18.20
  CL=F          -2.10%  @ 78.40
```

---

## Customising

### Add/remove tickers

Edit `config/tracking_config.json` under `"tickers"`:

```json
"top_us_stocks": [
  {"symbol": "AAPL", "name": "Apple"},
  {"symbol": "RELIANCE.NS", "name": "Reliance Industries"}
]
```

Any Yahoo Finance symbol works — Indian stocks use `.NS` (NSE) or `.BO` (BSE) suffix.

### Change alert thresholds

```json
"alert_thresholds": {
  "price_change": {
    "warning_pct": 1.5,
    "critical_pct": 3.0,
    "extreme_pct": 5.0
  },
  "vix": {
    "elevated": 20,
    "high_fear": 30,
    "extreme_fear": 40
  }
}
```

### Change EOD report time and timezone

```json
"schedule": {
  "eod_report_time": "18:00",
  "timezone": "Asia/Kolkata"
}
```

---

## Alpha Vantage Free Tier — Managing Quota

Free tier gives 25 API calls/day. The agent uses 4 calls per symbol (RSI + MACD + EMA + Bollinger).

- Default config tracks **6 symbols** for indicators = 24 calls/day (safe)
- Built-in 13-second delay between calls respects the 5 calls/minute limit
- To increase coverage, upgrade to Alpha Vantage premium ($50/month for 75 calls/min)

---

## Data Sources

| Source        | Used for                    | Cost  | Key needed |
|---------------|-----------------------------|-------|------------|
| yfinance      | Price, OHLCV, volume, MAs   | Free  | No         |
| Alpha Vantage | RSI, MACD, EMA, Bollinger   | Free* | Yes (free) |

*Free tier: 25 calls/day
