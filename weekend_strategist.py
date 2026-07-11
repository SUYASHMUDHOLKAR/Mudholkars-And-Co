"""
weekend_strategist.py
---------------------
Mudholkars and Co — WEEKEND STRATEGIST AGENT

Runs ONLY on weekends. Its job:
  1. Analyse all data collected by 47 agents during the week
  2. Find patterns: what worked, what didn't
  3. Create a BATTLE PLAN for next week
  4. Assign specific tasks to each agent for Monday
  5. Identify top 10 stocks to watch next week
  6. Detect sector rotation for next week
  7. Update learning engine with week's results

This is your MANAGER agent — it tells other agents what to focus on.
"""

import sys
import json
import logging
from datetime import datetime, date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "market-intel-division"))

import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("WeekendStrategist")

IST = ZoneInfo("Asia/Kolkata")


class WeekendStrategist:
    """
    The Manager Agent. Runs on weekends.
    Reviews the week. Plans the next week. Assigns tasks.
    """

    def __init__(self):
        self.base = Path(__file__).parent

    def run(self) -> dict:
        """Full weekend analysis and planning."""
        ist = datetime.now(IST).strftime("%d %b %Y %H:%M IST")
        logger.info("=" * 60)
        logger.info("  🧠 WEEKEND STRATEGIST — Analysing the week")
        logger.info(f"  {ist}")
        logger.info("=" * 60)

        # Step 1: Review this week's market performance
        market_review = self._review_market()

        # Step 2: Review our trades (wins/losses)
        trade_review = self._review_trades()

        # Step 3: Find next week's top candidates
        next_week_picks = self._find_next_week_stocks()

        # Step 4: Detect sector rotation
        sector_rotation = self._detect_sector_rotation()

        # Step 5: Create task assignments for each agent
        agent_tasks = self._assign_agent_tasks(market_review, next_week_picks, sector_rotation)

        # Step 6: Build the Monday morning brief
        monday_brief = self._build_monday_brief(market_review, next_week_picks, sector_rotation, agent_tasks)

        # Save everything
        report = {
            "agent": "WeekendStrategist",
            "timestamp": ist,
            "market_review": market_review,
            "trade_review": trade_review,
            "next_week_picks": next_week_picks,
            "sector_rotation": sector_rotation,
            "agent_tasks": agent_tasks,
            "monday_brief": monday_brief,
        }

        Path("reports").mkdir(exist_ok=True)
        with open("reports/weekend_strategy.json", "w") as f:
            json.dump(report, f, indent=2, default=str)

        # Print summary
        self._print_report(report)

        # Send to Telegram
        self._send_telegram(monday_brief)

        return report

    # ═══════════════════════════════════════════════════════
    # STEP 1: How did the market do this week?
    # ═══════════════════════════════════════════════════════

    def _review_market(self) -> dict:
        """Analyse Nifty + key indices for the week."""
        logger.info("\n📈 Reviewing this week's market...")
        try:
            nifty = yf.Ticker("^NSEI")
            hist = nifty.history(period="10d", interval="1d").dropna()
            if len(hist) < 5:
                return {"status": "insufficient_data"}

            week_data = hist.tail(5)
            week_open = float(week_data["Open"].iloc[0])
            week_close = float(week_data["Close"].iloc[-1])
            week_high = float(week_data["High"].max())
            week_low = float(week_data["Low"].min())
            week_return = (week_close - week_open) / week_open * 100

            # Trend direction
            if week_return >= 2:
                trend = "STRONG_BULLISH"
            elif week_return >= 0.5:
                trend = "BULLISH"
            elif week_return <= -2:
                trend = "STRONG_BEARISH"
            elif week_return <= -0.5:
                trend = "BEARISH"
            else:
                trend = "SIDEWAYS"

            return {
                "nifty_weekly_return": round(week_return, 2),
                "nifty_close": round(week_close, 2),
                "week_high": round(week_high, 2),
                "week_low": round(week_low, 2),
                "trend": trend,
                "next_week_bias": "BULLISH" if week_return > 0 else "CAUTIOUS",
            }
        except Exception as e:
            return {"error": str(e)}

    # ═══════════════════════════════════════════════════════
    # STEP 2: How did our trades do?
    # ═══════════════════════════════════════════════════════

    def _review_trades(self) -> dict:
        """Review our portfolio trades this week."""
        portfolio_file = self.base / "reports/portfolio_state.json"
        if portfolio_file.exists():
            with open(portfolio_file) as f:
                state = json.load(f)
            return {
                "capital": state.get("capital", 5000),
                "positions": state.get("positions", []),
                "closed_trades": len(state.get("closed_trades", [])),
                "total_pnl": state.get("pnl", 0),
            }
        return {"capital": 5000, "positions": [], "closed_trades": 0}

    # ═══════════════════════════════════════════════════════
    # STEP 3: Find next week's top stocks
    # ═══════════════════════════════════════════════════════

    def _find_next_week_stocks(self) -> list:
        """Scan for stocks setting up for next week."""
        logger.info("\n🔍 Finding next week's top candidates...")

        candidates = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
            "BAJFINANCE.NS", "SUNPHARMA.NS", "LT.NS", "MARUTI.NS", "TITAN.NS",
            "HAL.NS", "ONGC.NS", "NTPC.NS", "COALINDIA.NS", "TATASTEEL.NS",
            "SBIN.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "ADANIENT.NS",
            "BHARTIARTL.NS", "ITC.NS", "DRREDDY.NS", "CIPLA.NS", "DLF.NS",
            "TATAPOWER.NS", "IRFC.NS", "SUZLON.NS", "BEL.NS", "DIXON.NS",
        ]

        picks = []
        for sym in candidates:
            try:
                t = yf.Ticker(sym)
                hist = t.history(period="3mo", interval="1d").dropna()
                if len(hist) < 50:
                    continue

                close = hist["Close"]
                price = float(close.iloc[-1])

                # RSI
                rsi = float(RSIIndicator(close=close, window=14).rsi().iloc[-1])

                # MACD
                macd_obj = MACD(close=close)
                macd_l = float(macd_obj.macd().iloc[-1])
                macd_s = float(macd_obj.macd_signal().iloc[-1])
                macd_bull = macd_l > macd_s

                # Trend
                ema20 = float(EMAIndicator(close=close, window=20).ema_indicator().iloc[-1])
                ema50 = float(EMAIndicator(close=close, window=50).ema_indicator().iloc[-1])
                above_20 = price > ema20
                above_50 = price > ema50

                # Weekly return
                week_ret = (price - float(close.iloc[-5])) / float(close.iloc[-5]) * 100

                # Score for NEXT WEEK potential
                score = 50
                if rsi <= 35: score += 15  # oversold bounce candidate
                elif rsi <= 45: score += 8
                elif rsi >= 65: score -= 5

                if macd_bull: score += 12
                if above_20 and above_50: score += 10
                elif above_20: score += 5

                # Momentum building
                if 0 < week_ret < 3: score += 5  # gentle uptrend = continuation likely

                if score >= 65:
                    picks.append({
                        "stock": sym.replace(".NS", ""),
                        "score": score,
                        "price": round(price, 2),
                        "rsi": round(rsi, 1),
                        "macd": "BULL" if macd_bull else "BEAR",
                        "trend": "UP" if above_20 and above_50 else ("MID" if above_20 else "DOWN"),
                        "week_return": round(week_ret, 2),
                        "setup": "OVERSOLD_BOUNCE" if rsi <= 35 else ("MOMENTUM" if macd_bull and above_20 else "BUILDING"),
                    })
            except:
                continue

        picks.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"  Found {len(picks)} candidates for next week")
        return picks[:10]

    # ═══════════════════════════════════════════════════════
    # STEP 4: Which sectors are rotating?
    # ═══════════════════════════════════════════════════════

    def _detect_sector_rotation(self) -> dict:
        """Find which sectors money is flowing INTO vs OUT OF."""
        logger.info("\n🔄 Detecting sector rotation...")

        sectors = {
            "IT": ["TCS.NS", "INFY.NS", "WIPRO.NS"],
            "BANKING": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"],
            "PHARMA": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS"],
            "AUTO": ["MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS"],
            "METALS": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS"],
            "OIL": ["RELIANCE.NS", "ONGC.NS", "BPCL.NS"],
            "DEFENCE": ["HAL.NS", "BEL.NS", "BHEL.NS"],
            "POWER": ["NTPC.NS", "TATAPOWER.NS", "POWERGRID.NS"],
        }

        results = {}
        for sector, stocks in sectors.items():
            returns = []
            for sym in stocks:
                try:
                    t = yf.Ticker(sym)
                    h = t.history(period="10d", interval="1d").dropna()
                    if len(h) >= 5:
                        ret = (float(h["Close"].iloc[-1]) - float(h["Close"].iloc[-5])) / float(h["Close"].iloc[-5]) * 100
                        returns.append(ret)
                except:
                    continue
            if returns:
                avg = sum(returns) / len(returns)
                results[sector] = round(avg, 2)

        # Sort by return
        sorted_sectors = sorted(results.items(), key=lambda x: x[1], reverse=True)

        money_flowing_in = [s[0] for s in sorted_sectors if s[1] > 1]
        money_flowing_out = [s[0] for s in sorted_sectors if s[1] < -1]

        return {
            "sector_returns": dict(sorted_sectors),
            "money_flowing_in": money_flowing_in,
            "money_flowing_out": money_flowing_out,
            "top_sector": sorted_sectors[0][0] if sorted_sectors else "UNKNOWN",
            "worst_sector": sorted_sectors[-1][0] if sorted_sectors else "UNKNOWN",
        }

    # ═══════════════════════════════════════════════════════
    # STEP 5: Assign tasks to agents for next week
    # ═══════════════════════════════════════════════════════

    def _assign_agent_tasks(self, market: dict, picks: list, sectors: dict) -> dict:
        """Tell each agent what to focus on next week."""
        top_stocks = [p["stock"] for p in picks[:10]]
        hot_sectors = sectors.get("money_flowing_in", [])
        avoid_sectors = sectors.get("money_flowing_out", [])

        return {
            "Scout": f"Focus on: {', '.join(top_stocks[:5])}. Track volume spikes Monday AM.",
            "Technical": f"Run deep TA on: {', '.join(top_stocks[:7])}. Look for MACD crossovers.",
            "Fundamental": f"Check Q1 results calendar. Any earnings this week for top picks?",
            "BuzzHunter": f"Track social buzz on: {', '.join(top_stocks[:5])}. Weekend hype = Monday pop.",
            "SectorIntel": f"Focus on {', '.join(hot_sectors)} sectors. Money flowing IN here.",
            "GlobalIntel": f"Watch for: Fed news, oil prices, global risk events.",
            "IndiaIntel": f"Track: FII flow Mon AM, any govt policy news, RBI commentary.",
            "SocialMedia": f"Monitor weekend discussions on {', '.join(top_stocks[:3])}.",
            "RiskAgent": f"Max exposure 60% until market confirms trend. Tight SLs.",
            "Avoid": f"Reduce exposure to: {', '.join(avoid_sectors)} — money flowing OUT.",
        }

    # ═══════════════════════════════════════════════════════
    # STEP 6: Monday morning brief
    # ═══════════════════════════════════════════════════════

    def _build_monday_brief(self, market, picks, sectors, tasks) -> str:
        """Build the Monday morning brief that goes to Telegram."""
        lines = [
            "🌅 MONDAY MORNING BRIEF — Mudholkars & Co",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
            f"📈 Last Week: Nifty {market.get('nifty_weekly_return', 0):+.1f}% | Trend: {market.get('trend', '?')}",
            f"🔮 Next Week Bias: {market.get('next_week_bias', 'CAUTIOUS')}",
            "",
            "🎯 TOP PICKS FOR THIS WEEK:",
        ]

        for i, p in enumerate(picks[:5], 1):
            lines.append(f"  {i}. {p['stock']} — Score {p['score']} | RSI={p['rsi']} | {p['setup']}")

        lines.append("")
        lines.append("🔄 SECTOR ROTATION:")
        lines.append(f"  Money IN: {', '.join(sectors.get('money_flowing_in', ['None']))}")
        lines.append(f"  Money OUT: {', '.join(sectors.get('money_flowing_out', ['None']))}")

        lines.append("")
        lines.append("📋 AGENT TASKS:")
        lines.append(f"  Scout: {tasks.get('Scout', '')[:60]}")
        lines.append(f"  Focus sectors: {', '.join(sectors.get('money_flowing_in', []))}")
        lines.append(f"  Avoid: {tasks.get('Avoid', '')[:60]}")

        lines.append("")
        lines.append("⏰ First scan: Monday 9:30 AM (automatic)")

        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════
    # Telegram + Print
    # ═══════════════════════════════════════════════════════

    def _send_telegram(self, brief: str):
        """Send Monday brief to Telegram."""
        try:
            import requests
            token = "8979796737:AAGhw3n5YyO556A-rw60Oxbm7eJNWAF6pGo"
            chat_id = "6621137200"
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={
                "chat_id": chat_id, "text": brief,
            }, timeout=10)
            logger.info("📱 Monday brief sent to Telegram!")
        except:
            logger.warning("Telegram send failed")

    def _print_report(self, report: dict):
        print("\n" + report.get("monday_brief", ""))
        print("\n" + "=" * 55)
        print("  AGENT TASK ASSIGNMENTS:")
        for agent, task in report.get("agent_tasks", {}).items():
            print(f"    {agent:15s}: {task[:70]}")
        print("=" * 55)


if __name__ == "__main__":
    strategist = WeekendStrategist()
    strategist.run()
