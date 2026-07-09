"""
agent_meeting.py
----------------
Mudholkars and Co — AGENT MEETING (Every 1 Hour)

Like a company standup meeting — every agent reports what they found.
Then the Consensus Engine produces next-level combined analysis.

Flow:
  1. Each agent runs and posts to Agent Bus
  2. Meeting collects all posts from last 1 hour
  3. Cross-correlates: "Scout saw volume + Buzz saw trending + Intel saw news"
  4. Produces COMBINED INTELLIGENCE that no single agent could find alone
  5. Updates portfolio recommendations

This is what makes your system BETTER than any single tool.
"""

import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "market-intel-division"))
sys.path.insert(0, str(BASE / "social-media-agent"))
sys.path.insert(0, str(BASE / "buzz-hunter-agent"))
sys.path.insert(0, str(BASE / "global-intel-agent"))
sys.path.insert(0, str(BASE / "india-intel-agent"))

from agent_bus import AgentBus
from consensus_engine import ConsensusEngine
from risk_agent import RiskAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("AgentMeeting")

IST = ZoneInfo("Asia/Kolkata")


def run_meeting():
    """
    HOURLY AGENT MEETING
    Every agent reports → cross-correlation → combined verdict
    """
    ist = datetime.now(IST).strftime("%d %b %Y %H:%M IST")
    logger.info("=" * 60)
    logger.info("  🤝 AGENT MEETING — All Hands (Hourly)")
    logger.info(f"  {ist}")
    logger.info("=" * 60)

    bus = AgentBus()

    # ── STEP 1: Each department reports to the bus ────────────────
    logger.info("\n📢 Collecting reports from all departments...")

    # Run Scout (price data)
    try:
        logger.info("  Scout Agent reporting...")
        from stock_trend_agent.trackers.price_tracker import PriceTracker
        config = json.load(open(BASE / "stock-trend-agent/config/tracking_config.json"))
        pt = PriceTracker(config)
        top_stocks = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "SBIN.NS", "INFY.NS",
                      "BAJFINANCE.NS", "SUNPHARMA.NS", "ONGC.NS", "NTPC.NS", "WIPRO.NS"]
        for sym in top_stocks:
            data = pt.fetch_current(sym)
            if data and not data.get("error"):
                name = sym.replace(".NS", "")
                direction = "BULLISH" if data["pct_change"] > 1 else ("BEARISH" if data["pct_change"] < -1 else "NEUTRAL")
                score = 50 + int(data["pct_change"] * 10)
                score = max(0, min(100, score))
                flags = data.get("flags", [])
                signal = f"Price {data['pct_change']:+.2f}% | Vol {data['volume_ratio']}x"
                if flags:
                    signal += f" | {','.join(flags)}"
                bus.post("Scout", name, direction, score, signal, weight=1.5)
        logger.info("  ✔ Scout reported")
    except Exception as e:
        logger.warning(f"  Scout skip: {e}")

    # Run Technical Analyst
    try:
        logger.info("  Technical Analyst reporting...")
        sys.path.insert(0, str(BASE / "market-intel-division"))
        from core.technical_analyst import TechnicalAnalyst
        ta = TechnicalAnalyst()
        for sym in top_stocks:
            result = ta.analyze(sym)
            if result:
                name = sym.replace(".NS", "")
                direction = "BULLISH" if result["technical_score"] >= 55 else (
                    "BEARISH" if result["technical_score"] < 45 else "NEUTRAL")
                signal = f"{result['recommendation']} | {result['trend']['direction']} | RSI={result['indicators']['rsi']['value']}"
                bus.post("Technical", name, direction, result["technical_score"], signal, weight=1.5)
        logger.info("  ✔ Technical reported")
    except Exception as e:
        logger.warning(f"  Technical skip: {e}")

    # Run Fundamental Analyst
    try:
        logger.info("  Fundamental Analyst reporting...")
        from core.fundamental_analyst import FundamentalAnalyst
        fa = FundamentalAnalyst()
        for sym in top_stocks:
            result = fa.analyze(sym)
            if result:
                name = sym.replace(".NS", "")
                direction = "BULLISH" if result["fundamental_score"] >= 60 else (
                    "BEARISH" if result["fundamental_score"] < 40 else "NEUTRAL")
                signal = f"{result['classification']} | PE={result['valuation']['pe']} | ROE={result['profitability']['roe']}"
                bus.post("Fundamental", name, direction, result["fundamental_score"], signal, weight=1.5)
        logger.info("  ✔ Fundamental reported")
    except Exception as e:
        logger.warning(f"  Fundamental skip: {e}")

    # Run Buzz Hunter
    try:
        logger.info("  Buzz Hunter reporting...")
        sys.path.insert(0, str(BASE / "buzz-hunter-agent"))
        from buzz_scanner import BuzzScanner
        scanner = BuzzScanner()
        news_buzz = scanner.scan_news_buzz()
        for ticker, count in list(news_buzz.items())[:10]:
            direction = "BULLISH" if count >= 5 else ("NEUTRAL" if count >= 2 else "NEUTRAL")
            bus.post("BuzzHunter", ticker, direction, min(80, count * 12),
                     f"Trending: {count} mentions across news", weight=1.0)
        logger.info("  ✔ Buzz Hunter reported")
    except Exception as e:
        logger.warning(f"  Buzz Hunter skip: {e}")

    # Run Social Sentiment
    try:
        logger.info("  Social Media reporting...")
        sys.path.insert(0, str(BASE / "social-media-agent"))
        from global_scraper import GlobalSocialScraper
        from sentiment_analyzer import SentimentAnalyzer
        from stock_mention_tracker import StockMentionTracker

        scraper = GlobalSocialScraper()
        sentiment = SentimentAnalyzer()
        tracker = StockMentionTracker(mode="india")
        data = scraper.fetch_all()
        posts = data.get("posts", [])
        ticker_sent = tracker.get_sentiment_per_ticker(posts, sentiment)

        for ticker, s in list(ticker_sent.items())[:10]:
            bus.post("SocialMedia", ticker, s.get("label", "NEUTRAL"),
                     int(s.get("compound", 0) * 50 + 50),
                     f"Sentiment={s['compound']:+.3f} | {s['mentions']} mentions", weight=0.8)
        logger.info("  ✔ Social Media reported")
    except Exception as e:
        logger.warning(f"  Social skip: {e}")

    # Run Intel (news)
    try:
        logger.info("  News Intel reporting...")
        sys.path.insert(0, str(BASE / "global-intel-agent"))
        from news_scraper import NewsScraper
        from event_classifier import EventClassifier

        intel_config = json.load(open(BASE / "global-intel-agent/config/intel_config.json"))
        ns = NewsScraper(intel_config)
        ec = EventClassifier(intel_config)
        articles = ns.fetch_all()
        articles = ec.classify_all(articles)
        critical = [a for a in articles if a.get("severity") == "CRITICAL"]

        for a in critical[:5]:
            bus.post("NewsIntel", "MARKET", "BEARISH" if "crash" in a.get("full_text", "") else "NEUTRAL",
                     70, f"[{a.get('category','')}] {a.get('title','')[:60]}", weight=1.2)
        logger.info(f"  ✔ News Intel reported ({len(critical)} critical)")
    except Exception as e:
        logger.warning(f"  News Intel skip: {e}")

    # ── STEP 2: MEETING — Cross-correlate all signals ─────────────
    logger.info("\n🧠 MEETING: Cross-correlating all agent signals...")

    consensus_input = bus.get_consensus_input(max_age_hours=2)
    hot_stocks = bus.get_hot_stocks(min_agents=3, max_age_hours=2)

    ce = ConsensusEngine()
    consensus_results = ce.evaluate_batch(consensus_input)
    actionable = ce.get_actionable(consensus_results)

    # ── STEP 3: Portfolio decisions ───────────────────────────────
    risk = RiskAgent(capital=5000)

    # ── STEP 4: Print meeting minutes ─────────────────────────────
    print(f"\n{'='*60}")
    print(f"  📋 MEETING MINUTES — {ist}")
    print(f"{'='*60}")

    print(f"\n  📡 AGENT BUS: {len(bus.signals)} signals from last 2 hours")
    print(f"  🔥 HOT STOCKS (3+ agents mentioning):")
    if hot_stocks:
        for h in hot_stocks[:5]:
            icon = "▲" if h["consensus"] == "BULLISH" else ("▼" if h["consensus"] == "BEARISH" else "◆")
            print(f"    {icon} {h['stock']:12s} — {h['total_agents']} agents | "
                  f"Bull={h['bullish']} Bear={h['bearish']} → {h['consensus']}")
    else:
        print("    None yet (need more agents to run)")

    print(f"\n  🧠 CONSENSUS (combined verdict):")
    for r in consensus_results[:10]:
        icon = "🟢" if "BUY" in r["consensus"] else ("🔴" if "SELL" in r["consensus"] else "🟡")
        print(f"    {icon} {r['stock']:12s} {r['consensus']:12s} "
              f"Confidence={r['confidence']:.0f}% | {r['bullish_count']}↑ {r['bearish_count']}↓")

    # Actionable picks
    all_action = actionable.get("strong_buys", []) + actionable.get("buys", [])
    if all_action:
        print(f"\n  ✅ ACTIONABLE PICKS ({len(all_action)}):")
        for a in all_action[:3]:
            sl = risk.auto_stop_loss(a["stock"])
            if sl:
                print(f"    🎯 {a['stock']:12s} | Entry: ₹{sl['price']} | SL: ₹{sl['stop_loss']} | TGT: ₹{sl['target']}")
    else:
        print(f"\n  ⏸️  No high-conviction trades right now. Agents say: WAIT.")

    print(f"\n  📊 NEXT MEETING: in 1 hour")
    print(f"{'='*60}")

    # Save meeting minutes
    Path("reports").mkdir(exist_ok=True)
    minutes = {
        "timestamp": ist,
        "signals_count": len(bus.signals),
        "hot_stocks": hot_stocks[:5],
        "consensus": [{"stock": r["stock"], "verdict": r["consensus"],
                       "confidence": r["confidence"]} for r in consensus_results[:15]],
        "actionable": actionable,
    }
    with open("reports/meeting_latest.json", "w") as f:
        json.dump(minutes, f, indent=2, default=str)
    logger.info("Meeting minutes saved.")


if __name__ == "__main__":
    run_meeting()
