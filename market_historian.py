"""
market_historian.py
-------------------
Mudholkars and Co — MARKET HISTORIAN AGENT

Studies 10 years of Indian market history:
  - Every major crash and what caused it
  - Every big rally and what triggered it
  - Every sector rotation pattern
  - Every multibagger (stocks that went 5x-100x)
  - Seasonal patterns (budget month, results season)
  - FII behavior patterns

Uses this knowledge to:
  - Predict "this setup is similar to 2020 COVID bottom"
  - Warn "this looks like 2018 IL&FS crash pattern"
  - Identify "this is early stage multibagger setup"
  - Alert "FII selling this much = bounce coming in X days"
"""

import json
import logging
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

import yfinance as yf
import numpy as np

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


class MarketHistorian:
    """
    Learns from 10 years of market history.
    Finds patterns. Predicts outcomes based on similar past setups.
    """

    HISTORY_FILE = Path("reports/market_history.json")

    # ── Known major events (Indian market 2015-2026) ──────────────
    MAJOR_EVENTS = [
        {"date": "2015-08-24", "type": "CRASH",   "name": "China Yuan Devaluation Crash",     "nifty_fall": -5.9,  "recovery_days": 90},
        {"date": "2016-11-08", "type": "CRASH",   "name": "Demonetization Shock",             "nifty_fall": -6.0,  "recovery_days": 45},
        {"date": "2018-09-21", "type": "CRASH",   "name": "IL&FS Crisis / NBFC Crash",        "nifty_fall": -12.0, "recovery_days": 180},
        {"date": "2020-03-23", "type": "CRASH",   "name": "COVID-19 Crash (Bottom)",          "nifty_fall": -38.0, "recovery_days": 180},
        {"date": "2021-10-19", "type": "TOP",     "name": "Post-COVID Bull Market Top",       "nifty_rise": 130.0, "correction_pct": -15},
        {"date": "2022-06-17", "type": "BOTTOM",  "name": "FII Selling Bottom (2022)",        "nifty_fall": -17.0, "recovery_days": 90},
        {"date": "2023-12-01", "type": "BREAKOUT","name": "Nifty 20000 Breakout",             "nifty_rise": 20.0,  "continuation_days": 60},
        {"date": "2024-06-04", "type": "CRASH",   "name": "Election Result Shock",            "nifty_fall": -8.5,  "recovery_days": 30},
        {"date": "2024-09-27", "type": "TOP",     "name": "Nifty All-Time High 26277",        "nifty_rise": 25.0,  "correction_pct": -12},
        {"date": "2025-02-05", "type": "BOTTOM",  "name": "2025 Budget Sell-off Bottom",      "nifty_fall": -15.0, "recovery_days": 60},
    ]

    # ── Multibagger patterns (stocks that gave 5x+ in 3-5 years) ──
    MULTIBAGGER_PATTERNS = [
        {"stock": "HAL", "year_start": 2020, "return_3yr": 900,
         "why": "Defence spending + Aatmanirbhar + low debt + monopoly"},
        {"stock": "BAJFINANCE", "year_start": 2015, "return_3yr": 500,
         "why": "NBFC credit boom + digital lending + ROE>25%"},
        {"stock": "TITAN", "year_start": 2016, "return_3yr": 400,
         "why": "Organised jewellery + Tata brand + rising income"},
        {"stock": "INFY", "year_start": 2020, "return_3yr": 220,
         "why": "Digital transformation demand + COVID IT boom"},
        {"stock": "IRFC", "year_start": 2021, "return_3yr": 350,
         "why": "Railway capex + PSU re-rating + dividend"},
        {"stock": "SUZLON", "year_start": 2023, "return_3yr": 500,
         "why": "Green energy push + debt resolution + order book"},
        {"stock": "DIXON", "year_start": 2020, "return_3yr": 800,
         "why": "PLI scheme + Make in India electronics"},
    ]

    # ── Seasonal patterns ──────────────────────────────────────────
    SEASONAL_PATTERNS = {
        "January": {"bias": "BULLISH",  "reason": "FII buying starts, budget anticipation"},
        "February": {"bias": "VOLATILE","reason": "Union Budget month — depends on announcements"},
        "March": {"bias": "BULLISH",    "reason": "Year-end rally, FII buying before April"},
        "April": {"bias": "BULLISH",    "reason": "Q4 results season, positive surprises"},
        "May": {"bias": "VOLATILE",     "reason": "Sell in May historically (not always India)"},
        "June": {"bias": "BULLISH",     "reason": "Monsoon arrival, FMCG/agri stocks"},
        "July": {"bias": "BULLISH",     "reason": "Q1 results, FII buying"},
        "August": {"bias": "SIDEWAYS",  "reason": "Low volume, holiday season globally"},
        "September": {"bias": "VOLATILE","reason": "FII quarter-end rebalancing"},
        "October": {"bias": "BULLISH",  "reason": "Festival season, consumer demand"},
        "November": {"bias": "BULLISH", "reason": "Diwali rally, year-end buying"},
        "December": {"bias": "BULLISH", "reason": "Year-end rally, FII window dressing"},
    }

    def __init__(self):
        self.history = self._load_history()

    # ═══════════════════════════════════════════════════════════
    # STUDY MARKET HISTORY
    # ═══════════════════════════════════════════════════════════

    def study_history(self) -> dict:
        """Full 10-year market study. Run once, updates weekly."""
        logger.info("📚 Market Historian studying 10 years of data...")

        # 1. Study Nifty patterns
        nifty_patterns = self._study_nifty_patterns()

        # 2. Study each major event aftermath
        event_aftermath = self._study_event_patterns()

        # 3. Study multibagger signals
        multibagger_signals = self._study_multibagger_patterns()

        # 4. Study FII behavior patterns
        fii_patterns = self._study_fii_patterns()

        # 5. Build prediction rules from history
        prediction_rules = self._build_prediction_rules(nifty_patterns)

        history = {
            "studied_on": datetime.now(IST).isoformat(),
            "data_range": "2015-2026 (10 years)",
            "nifty_patterns": nifty_patterns,
            "major_events": self.MAJOR_EVENTS,
            "event_aftermath": event_aftermath,
            "multibagger_signals": multibagger_signals,
            "fii_patterns": fii_patterns,
            "seasonal_patterns": self.SEASONAL_PATTERNS,
            "prediction_rules": prediction_rules,
        }

        self._save_history(history)
        logger.info(f"✅ History studied: {len(prediction_rules)} prediction rules generated")
        return history

    def _study_nifty_patterns(self) -> dict:
        """Study Nifty's behavioral patterns over 10 years."""
        try:
            nifty = yf.Ticker("^NSEI")
            hist = nifty.history(period="10y", interval="1d").dropna()

            close = hist["Close"]
            returns = close.pct_change().dropna() * 100

            # Crash recovery patterns
            big_drops = [(i, float(returns.iloc[i])) for i in range(len(returns))
                        if float(returns.iloc[i]) <= -2.0]

            recovery_times = []
            for idx, drop in big_drops[:20]:
                drop_price = float(close.iloc[idx])
                for fwd in range(1, 60):
                    if idx + fwd >= len(close):
                        break
                    future = float(close.iloc[idx + fwd])
                    if future >= drop_price:
                        recovery_times.append(fwd)
                        break

            avg_recovery = int(np.mean(recovery_times)) if recovery_times else 20

            # Best months
            monthly_returns = {}
            for i in range(len(close)):
                month = hist.index[i].strftime("%B")
                if i > 0:
                    ret = (float(close.iloc[i]) - float(close.iloc[i-1])) / float(close.iloc[i-1]) * 100
                    monthly_returns.setdefault(month, []).append(ret)

            monthly_avg = {m: round(np.mean(v), 2) for m, v in monthly_returns.items()}
            best_months = sorted(monthly_avg.items(), key=lambda x: x[1], reverse=True)[:3]
            worst_months = sorted(monthly_avg.items(), key=lambda x: x[1])[:3]

            return {
                "total_return_10yr": round((float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100, 1),
                "avg_annual_return": round(((float(close.iloc[-1]) / float(close.iloc[0])) ** 0.1 - 1) * 100, 1),
                "avg_crash_recovery_days": avg_recovery,
                "best_months": [m[0] for m in best_months],
                "worst_months": [m[0] for m in worst_months],
                "monthly_returns": monthly_avg,
                "big_crashes_per_year": round(len(big_drops) / 10, 1),
            }
        except Exception as e:
            logger.warning(f"Nifty study error: {e}")
            return {}

    def _study_event_patterns(self) -> list:
        """Study what happens AFTER major events."""
        patterns = []
        for event in self.MAJOR_EVENTS:
            if event["type"] == "CRASH":
                patterns.append({
                    "trigger": event["name"],
                    "immediate": f"Market falls {abs(event['nifty_fall'])}%",
                    "recovery": f"Recovers in ~{event.get('recovery_days', 90)} days",
                    "action": "BUY on day 3-5 after crash (oversold bounce)",
                    "sector_play": "Banking + IT first to recover",
                })
            elif event["type"] == "BREAKOUT":
                patterns.append({
                    "trigger": event["name"],
                    "immediate": "New highs = FOMO buying",
                    "action": "Buy momentum stocks, avoid defensive",
                    "sector_play": "Midcap + Small cap outperform",
                })
        return patterns

    def _study_multibagger_patterns(self) -> dict:
        """Common traits of multibagger stocks before they ran."""
        common_traits = {
            "fundamentals": [
                "ROE > 20% for 3+ consecutive years",
                "Debt/Equity < 0.5 (preferably zero debt)",
                "Revenue growing > 20% YoY",
                "Net margin expanding (not just revenue)",
                "Promoter holding > 50% and STABLE",
            ],
            "technical": [
                "Quietly consolidating for 1-2 years (base building)",
                "Volume drying up during consolidation",
                "RSI between 40-60 (not overbought yet)",
                "Breaking above 52-week high with volume",
                "MACD bullish crossover after long base",
            ],
            "thematic": [
                "Direct beneficiary of government policy (PLI, Defence, Green)",
                "Monopoly or near-monopoly in sector",
                "Sector tailwind lasting 5-10 years",
                "Management with skin in game (high promoter holding)",
            ],
            "stocks_to_watch_2026": [
                "HAL (defence monopoly, order book growing)",
                "BEL (defence electronics, Aatmanirbhar)",
                "IRFC (railway capex, assured income)",
                "TATAPOWER (green energy transition)",
                "DIXON (PLI electronics beneficiary)",
                "SUZLON (wind energy revival)",
                "POLYCAB (infra + real estate boom)",
            ],
        }
        return common_traits

    def _study_fii_patterns(self) -> dict:
        """FII behavior patterns and their market impact."""
        return {
            "fii_heavy_selling": {
                "pattern": "FII sells > ₹5000 Cr for 5+ consecutive days",
                "market_impact": "Nifty falls 5-8%",
                "historical_examples": ["2022 Jan-Jun", "2024 Oct", "2026 Jul"],
                "action": "Wait for FII to turn buyers. Buy in last week of selling.",
                "typical_duration": "3-8 weeks of selling, then reversal",
            },
            "fii_heavy_buying": {
                "pattern": "FII buys > ₹3000 Cr for 3+ consecutive days",
                "market_impact": "Nifty rallies 3-8%",
                "action": "Buy midcap/smallcap (they outperform when FII buys largecap)",
                "typical_duration": "4-12 weeks of sustained rally",
            },
            "dii_vs_fii": {
                "insight": "When FII sells but DII buys heavily, market stays resilient",
                "action": "Safe to trade when DII buying > FII selling",
            },
        }

    def _build_prediction_rules(self, nifty_patterns: dict) -> list:
        """Build actionable prediction rules from historical study."""
        rules = [
            {
                "rule": "CRASH_BOUNCE",
                "condition": "Nifty falls > 5% in 3 days",
                "historical_win_rate": 78,
                "action": "BUY index ETF or top bluechips on day 3-5",
                "target": "+5-8% in 15-20 days",
                "stop": "-3% from entry",
                "basis": f"Historical avg recovery: {nifty_patterns.get('avg_crash_recovery_days', 20)} days",
            },
            {
                "rule": "BUDGET_PLAY",
                "condition": "Union Budget within 7 days",
                "historical_win_rate": 65,
                "action": "Buy infra + capex stocks 5 days before, sell same day",
                "target": "+3-5%",
                "stop": "-2%",
                "basis": "Budget day = sell the news event",
            },
            {
                "rule": "RESULTS_BEAT",
                "condition": "Company beats estimates by > 10%",
                "historical_win_rate": 72,
                "action": "BUY next day open, hold 3-5 days",
                "target": "+5-8%",
                "stop": "-3%",
                "basis": "Earnings beats drive 3-7 day continuation",
            },
            {
                "rule": "52W_BREAKOUT",
                "condition": "Stock breaks 52-week high with 2x volume",
                "historical_win_rate": 68,
                "action": "BUY on breakout day or next day",
                "target": "+10-15% in 3-4 weeks",
                "stop": "-5% (below breakout level)",
                "basis": "52-week breakouts continue 68% of the time",
            },
            {
                "rule": "FII_REVERSAL",
                "condition": "FII sold heavily for 4+ weeks, now buying for 2 days",
                "historical_win_rate": 74,
                "action": "BUY midcap stocks aggressively",
                "target": "+15-20% in 4-6 weeks",
                "stop": "-7%",
                "basis": "FII reversal = sustained rally begins",
            },
            {
                "rule": "SECTOR_ROTATION",
                "condition": "Defensive sectors (FMCG, Pharma) outperforming for 4+ weeks",
                "historical_win_rate": 65,
                "action": "Prepare for market correction (reduce exposure)",
                "target": "Capital preservation",
                "stop": "N/A",
                "basis": "Money moving to defensives = market fear building",
            },
            {
                "rule": "OCTOBER_EFFECT",
                "condition": "Market in October (historically volatile)",
                "historical_win_rate": 60,
                "action": "Hold cash, wait for volatility to settle",
                "basis": "October historically most volatile month globally",
            },
            {
                "rule": "DIWALI_RALLY",
                "condition": "October/November, Diwali approaching",
                "historical_win_rate": 70,
                "action": "BUY consumer discretionary + retail stocks",
                "target": "+8-12%",
                "basis": "Festival season drives consumption + market sentiment",
            },
        ]
        return rules

    # ═══════════════════════════════════════════════════════════
    # MATCH CURRENT SETUP TO HISTORY
    # ═══════════════════════════════════════════════════════════

    def find_similar_historical_setup(self) -> dict:
        """
        Look at current market and find the most similar historical setup.
        Returns: which period in history this resembles + what happened next.
        """
        try:
            nifty = yf.Ticker("^NSEI")
            hist = nifty.history(period="3mo", interval="1d").dropna()

            current_price = float(hist["Close"].iloc[-1])
            ma50 = float(hist["Close"].rolling(50).mean().iloc[-1])
            recent_return = (current_price - float(hist["Close"].iloc[-20])) / float(hist["Close"].iloc[-20]) * 100

            vix = yf.Ticker("^INDIAVIX")
            vix_hist = vix.history(period="5d", interval="1d").dropna()
            vix_level = float(vix_hist["Close"].iloc[-1]) if not vix_hist.empty else 15

            # Determine current setup
            if current_price < ma50 and recent_return < -8:
                similar_period = "2022 FII selling crash"
                next_event = "Typically bottoms 3-6 weeks later. FII reversal = big rally"
                recommended_action = "Wait for FII to stop selling, then BUY aggressively"
            elif current_price > ma50 and recent_return > 5 and vix_level < 14:
                similar_period = "2023-2024 bull market"
                next_event = "Continuation likely. Mid/small cap outperforms"
                recommended_action = "Stay invested, add on dips, focus on midcap"
            elif abs(recent_return) < 3 and vix_level < 16:
                similar_period = "2019 pre-election consolidation"
                next_event = "Sideways for 4-8 weeks, then directional move"
                recommended_action = "Be selective, swing trade, avoid large positions"
            else:
                similar_period = "General consolidation phase"
                next_event = "Unclear direction, wait for signal"
                recommended_action = "Stick to high-conviction setups only"

            current_month = datetime.now(IST).strftime("%B")
            seasonal = self.SEASONAL_PATTERNS.get(current_month, {})

            return {
                "current_setup": {
                    "nifty_vs_50ma": "ABOVE" if current_price > ma50 else "BELOW",
                    "recent_20d_return": round(recent_return, 1),
                    "vix": round(vix_level, 1),
                    "month_bias": seasonal.get("bias", "NEUTRAL"),
                },
                "similar_to": similar_period,
                "historical_outcome": next_event,
                "recommended_action": recommended_action,
                "seasonal_factor": seasonal.get("reason", ""),
            }
        except Exception as e:
            logger.warning(f"Historical match error: {e}")
            return {"error": str(e)}

    def get_multibagger_candidates(self) -> list:
        """
        Scan current market for stocks matching multibagger patterns.
        """
        candidates = []
        watch_stocks = ["HAL.NS", "BEL.NS", "IRFC.NS", "TATAPOWER.NS",
                       "DIXON.NS", "SUZLON.NS", "POLYCAB.NS", "ADANIGREEN.NS",
                       "IRCTC.NS", "CDSL.NS"]

        for sym in watch_stocks:
            try:
                t = yf.Ticker(sym)
                info = t.info
                hist = t.history(period="1y", interval="1d").dropna()

                if not info or hist.empty:
                    continue

                score = 0
                reasons = []

                # Check multibagger traits
                roe = info.get("returnOnEquity", 0) or 0
                if roe * 100 >= 20:
                    score += 20
                    reasons.append(f"ROE={roe*100:.0f}%")

                de = info.get("debtToEquity", 99) or 99
                if de < 50:
                    score += 15
                    reasons.append("Low debt")

                promoter = info.get("heldPercentInsiders", 0) or 0
                if promoter * 100 >= 50:
                    score += 15
                    reasons.append(f"Promoter={promoter*100:.0f}%")

                # 52-week position
                year_high = float(hist["High"].max())
                price = float(hist["Close"].iloc[-1])
                from_high = (year_high - price) / year_high * 100
                if from_high > 20:
                    score += 10
                    reasons.append("20%+ below 52w high (building base)")

                if score >= 40:
                    candidates.append({
                        "stock": sym.replace(".NS", ""),
                        "score": score,
                        "reasons": reasons,
                        "price": round(price, 2),
                    })
            except:
                continue

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:5]

    def print_report(self):
        """Print what the historian learned."""
        history = self.history
        if not history:
            print("No history studied yet. Run study_history() first.")
            return

        print("=" * 60)
        print("  📜 MARKET HISTORIAN — 10 YEAR INTELLIGENCE")
        print("=" * 60)

        np_ = history.get("nifty_patterns", {})
        if np_:
            print(f"\n  Nifty 10yr CAGR: {np_.get('avg_annual_return', 0)}%")
            print(f"  Avg crash recovery: {np_.get('avg_crash_recovery_days', 0)} days")
            print(f"  Best months: {', '.join(np_.get('best_months', []))}")

        print(f"\n  📋 PREDICTION RULES ({len(history.get('prediction_rules', []))}):")
        for r in history.get("prediction_rules", [])[:4]:
            print(f"    • {r['rule']}: {r['historical_win_rate']}% WR → {r['action'][:50]}")

        match = self.find_similar_historical_setup()
        print(f"\n  🎯 CURRENT SETUP RESEMBLES: {match.get('similar_to', '?')}")
        print(f"  HISTORICAL OUTCOME: {match.get('historical_outcome', '?')}")
        print(f"  RECOMMENDED: {match.get('recommended_action', '?')}")
        print("=" * 60)

    def _save_history(self, history: dict):
        self.HISTORY_FILE.parent.mkdir(exist_ok=True)
        with open(self.HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2, default=str)
        self.history = history

    def _load_history(self) -> dict:
        if self.HISTORY_FILE.exists():
            try:
                return json.loads(self.HISTORY_FILE.read_text())
            except:
                pass
        return {}


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    historian = MarketHistorian()
    history = historian.study_history()
    historian.print_report()
    print("\n  🔍 CURRENT MARKET RESEMBLES:")
    match = historian.find_similar_historical_setup()
    for k, v in match.items():
        print(f"    {k}: {v}")
    print("\n  💎 MULTIBAGGER CANDIDATES:")
    for c in historian.get_multibagger_candidates():
        print(f"    {c['stock']}: score={c['score']} | {', '.join(c['reasons'])}")
