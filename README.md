# Mudholkars and Co — Agent Army 🏢

Private AI agent infrastructure for stock market tracking, analysis, and trading.

---

## Company Structure

```
Mudholkars_and_Co/
│
├── stock-trend-agent/          ← Agent 1: Scout + India Market Analyst   ✅ LIVE
│   ├── agent.py                   Scout — 38+ symbols, every 15 min
│   ├── india_agent/               India Analyst — global→India impact
│   ├── trackers/                  Price, Indicators, Alerts
│   └── reports/
│
├── global-intel-agent/         ← Agent 2: Global Intelligence            ✅ LIVE
│   ├── intel_agent.py             25 global sources × 25 world categories
│   ├── news_scraper.py
│   ├── event_classifier.py
│   ├── impact_analyzer.py
│   ├── sector_mapper.py
│   └── reports/
│
├── india-intel-agent/          ← Agent 3: India Intelligence             ✅ LIVE
│   ├── india_intel_agent.py       25 Indian sources × 25 India categories
│   ├── india_news_scraper.py
│   ├── india_event_classifier.py
│   ├── india_impact_analyzer.py
│   └── reports/
│
├── [coming soon]               ← Agent 4: Risk Agent
├── [coming soon]               ← Agent 5: Trader Agent
└── [coming soon]               ← Orchestrator: Master command center
```

---

## Agents Status

| # | Agent | Role | Schedule | Status |
|---|-------|------|----------|--------|
| 1 | **Scout Agent** | Watches 38+ global market symbols | Every 15 min | ✅ Live |
| 1b | **India Market Analyst** | Global event → Indian market impact | On demand | ✅ Live |
| 2 | **Global Intel Agent** | 25 global news sources × 25 world event categories | Every 30 min | ✅ Live |
| 3 | **India Intel Agent** | 25 Indian news sources × 25 India-specific categories | Every 30 min | ✅ Live |
| 4 | Risk Agent | Portfolio exposure, stop-loss monitoring | Planned | 🔜 |
| 5 | Trader Agent | Executes buy/sell on broker API | Planned | 🔜 |
| 6 | Orchestrator | Master controller | Planned | 🔜 |

---

## Quick Start

```bash
# Agent 1: Scout
cd ~/Mudholkars_and_Co/stock-trend-agent
python3 agent.py --once

# Agent 2: Global Intel
cd ~/Mudholkars_and_Co/global-intel-agent
python3 intel_agent.py --once

# Agent 3: India Intel
cd ~/Mudholkars_and_Co/india-intel-agent
python3 india_intel_agent.py --once

# Run all continuously (3 terminals)
python3 agent.py                              # Terminal 1
python3 intel_agent.py                        # Terminal 2
python3 india_intel_agent.py                  # Terminal 3
```

---

## Live Test Results (10 Jul 2026 01:05 IST)

### India Intel Agent — First Run
- **96 articles** from Indian sources
- **21 CRITICAL alerts** | **13 HIGH**
- Top: HDFC Bank Q1 results date announced (score 97)
- Top: SBI Funds IPO ₹545-574 price band (BULLISH, score 97)
- Top: BrahMos deal (Modi tour) → Defence stocks
- India Politics category: BJP/NDA election filings

### What India Intel Tracks That Others Don't
| Category | Example Today |
|---|---|
| CORPORATE_EARNINGS | HDFC Bank Q1 results date |
| STARTUPS_IPO | SBI Funds IPO launched |
| INDIA_POLITICS | BrahMos deal, election filings |
| SEBI_REGULATIONS | Crypto trading news |
| NIFTY_SENSEX_TECHNICAL | Technical level alerts |

---

## Owner
**Mudholkars and Co**  
*Built with Kiro AI — July 2026*
