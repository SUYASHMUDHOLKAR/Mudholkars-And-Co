# India Market Analyst Agent 🇮🇳

Specialized sub-agent that reads Scout Agent reports and produces **deep Indian market impact analysis**.

---

## What It Does

Reads what the Scout Agent detected globally and answers:
- How will US market crash impact Indian IT sector?
- If crude oil spikes, which Indian stocks will crash?
- Will Nifty gap up or down tomorrow morning?
- Which sectors should I buy/avoid today?
- What's the overall sentiment for Indian markets?

---

## Live Test Result (Just Now)

```
MARKET SENTIMENT : BULLISH  (Score: +2.0 / 10)
RISK LEVEL       : MEDIUM
NIFTY OPENING    : GAP_UP_MILD  (~+0.40%)
ESTIMATED OPEN   : 24078
INDIA VIX        : 14.7  [LOW]
USD/INR          : 95.38  (-0.23%)  → INR STRENGTHENING

GLOBAL EVENTS IMPACTING INDIA (2)
----------------------------------------
  [MEDIUM] Crude Oil falls >2%
           → Lower oil = lower import bill
           → Aviation, Paints, FMCG, Auto sectors gain
           → Expected Nifty: +0.5% to +1.5%

SECTOR OUTLOOK
----------------------------------------
  AVIATION       : BUY      (score +2)  |  INDIGO, SPICEJET
  PAINTS_TYRES   : BUY      (score +2)  |  ASIANPAINT, BERGER, APOLLOTYRE
  FMCG           : BUY      (score +2)  |  HINDUNILVR, ITC, NESTLEIND
  AUTO           : BUY      (score +2)  |  MARUTI, TATAMOTORS, M&M
  BANKING        : BUY      (score +1)  |  HDFCBANK, ICICIBANK, KOTAKBANK
  OIL_GAS        : CAUTION  (score -2)  |  RELIANCE, ONGC, IOC
```

This is **real analysis from live market data captured seconds ago**.

---

## How It Works — The Intelligence

### 1. Global Event Detection
Reads Scout Agent's findings:
- US markets up/down 3%+ → tracks FII flow impact on India
- Crude oil spike → maps to Aviation (negative), OMCs (positive)
- USD/INR movement → IT/Pharma gain on weak INR
- VIX crossing 30/40 → predicts FII selloff in India
- China crash → Indian metals follow

### 2. India-Specific Tracking
Fetches real-time:
- Nifty 50, Sensex current levels
- India VIX (fear gauge)
- SGX Nifty (Singapore futures — predicts India open)
- USD/INR forex rate
- Top Nifty50 gainers/losers

### 3. Deep Analysis Engine
Produces:
- **Sentiment Score** (-10 to +10): Overall bullish/bearish signal
- **Opening Gap Prediction**: GAP_UP / GAP_DOWN / FLAT with % estimate
- **Sector Outlook**: Every sector rated (STRONG_BUY → AVOID)
- **Stock Watchlist**: Specific NSE stocks to buy/avoid
- **Risk Level**: LOW / MEDIUM / HIGH / EXTREME

### 4. Sector → Stock Mapping
Built-in intelligence covering:
- IT: TCS, Infosys, Wipro, HCL Tech, Tech Mahindra
- Banking: HDFC, ICICI, Kotak, Axis, SBI
- Pharma: Sun Pharma, Dr Reddy's, Cipla, Divi's
- Metals: Tata Steel, JSW, Hindalco, Vedanta
- Auto: Maruti, Tata Motors, M&M, Bajaj Auto
- Oil & Gas: Reliance, ONGC, IOC, BPCL
- Aviation: Indigo, SpiceJet
- +10 more sectors, 100+ NSE stocks

---

## Usage

### Run analysis on latest Scout report

```bash
cd ~/stock-trend-agent
python3 india_agent/india_agent.py
```

This auto-detects the latest Scout Agent report and produces India-specific analysis.

### Analyze a specific Scout report

```bash
python3 india_agent/india_agent.py --report reports/report_2026-07-10.json
```

### Output location

```
reports/india_analysis/
├── india_analysis_20260710_004512.json  ← Full structured data
└── india_analysis_20260710_004512.txt   ← Human-readable report
```

---

## When to Run This Agent

| Scenario | Command | Why |
|---|---|---|
| **After Scout runs** | `python3 india_agent/india_agent.py` | Get India-specific view |
| **Before market open (9:15 AM)** | Run at 8:30 AM | Check SGX Nifty gap prediction |
| **After major US event** | Run immediately | See India impact before NSE opens |
| **Before placing trades** | Run on-demand | Know which sectors to trade |

---

## Integration with Scout Agent

To make Scout automatically trigger India analysis after every cycle, add this to `agent.py`:

```python
# After price cycle completes:
os.system("python3 india_agent/india_agent.py")
```

Or run both in sequence manually:
```bash
python3 agent.py --once && python3 india_agent/india_agent.py
```

---

## Output Fields Explained

### Sentiment Score
- **+10**: Extremely bullish — go heavy long
- **+4 to +10**: Bullish — buy on dips
- **-1.5 to +1.5**: Neutral — wait and watch
- **-4 to -1.5**: Bearish — reduce exposure
- **-10**: Extremely bearish — exit positions, short

### Opening Gap Prediction
Uses SGX Nifty premium + global event rules to estimate opening gap.
- **GAP_UP_STRONG**: >1% gap up expected
- **GAP_UP_MILD**: 0.3-1% gap up
- **FLAT_OPEN**: -0.3% to +0.3%
- **GAP_DOWN_MILD**: -1% to -0.3%
- **GAP_DOWN_STRONG**: < -1%

### Sector Direction
- **STRONG_BUY**: High confidence positive (score ≥3)
- **BUY**: Positive outlook (score 1-2)
- **NEUTRAL**: No clear signal (score 0)
- **CAUTION**: Negative bias (score -1 to -2)
- **AVOID**: Strong negative (score <-3)

---

## Global Event → India Impact Rules (Sample)

| Global Event | Indian Sector Impact | Logic |
|---|---|---|
| **US markets crash >3%** | IT, Pharma, Metals ⬇️ | FII selling, IT revenue from US hurt |
| **Crude oil spike >2%** | Aviation, Paints ⬇️ / Oil PSUs ⬆️ | India imports 85% oil, costs rise |
| **INR weakens** | IT, Pharma ⬆️ / Importers ⬇️ | IT earns in USD, reports in INR |
| **VIX crosses 40** | All sectors ⬇️ (except FMCG/Pharma) | FII panic exit from emerging markets |
| **Gold surge >1.5%** | Jewellery ⬆️ / Equities ⬇️ | Safe-haven buying = risk-off |
| **China crash** | Metals, Commodities ⬇️ | China = largest commodity consumer |

15+ rules total, all coded in `global_impact.py`.

---

## Why This Agent Matters

Without it, you only see:
- "S&P 500 fell 3% yesterday"

With it, you know:
- "FII will sell Indian equities today"
- "IT sector will fall 2-4%"
- "TCS, Infosys, Wipro — avoid today"
- "Nifty likely to gap down -1.5% at open"

**This agent converts global noise into actionable Indian market intelligence.**

---

## Next Steps — Telegram Alerts

Want this analysis pushed to your phone via Telegram automatically?

Tell me and I'll add:
```python
# Send to Telegram after analysis
send_telegram(analysis["summary"])
```

You'll get instant alerts like:
```
🔴 INDIA MARKET ALERT
Sentiment: BEARISH (-3.5)
Nifty Opening: GAP_DOWN_STRONG (-2.1%)
Risk: HIGH
Avoid: IT, METALS sectors
```
