"""
full_pipeline.py
----------------
Mudholkars and Co — FULL AGENT PIPELINE

Runs ALL agents → feeds into Consensus Engine → Risk Agent → Final Calls

Usage:
  python full_pipeline.py              # full run
  python full_pipeline.py --quick      # quick scan (top 20 stocks only)

Best time to run:
  - 9:30 AM IST (30 min after market open — data settled)
  - 12:00 PM IST (mid-day check)
  - 3:30 PM IST (before close — EOD setup)
"""

import sys
import json
import logging
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

# Setup paths
BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "stock-trend-agent"))
sys.path.insert(0, str(BASE / "market-intel-division"))
sys.path.insert(0, str(BASE / "sector-intel-division"))
sys.path.insert(0, str(BASE / "social-media-agent"))
sys.path.insert(0, str(BASE / "india-social-agent"))
sys.path.insert(0, str(BASE / "buzz-hunter-agent"))
sys.path.insert(0, str(BASE / "global-intel-agent"))
sys.path.insert(0, str(BASE / "india-intel-agent"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("FullPipeline")

from consensus_engine import ConsensusEngine
from risk_agent import RiskAgent


def run_full_pipeline(quick: bool = False):
    ist = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %H:%M IST")
    logger.info("=" * 65)
    logger.info("  🏢 MUDHOLKARS & CO — FULL AGENT PIPELINE")
    logger.info(f"  {ist}")
    logger.info("=" * 65)

    # ── STEP 1: Technical + Fundamental Analysis ──────────────────
    logger.info("\n📈 STEP 1: Technical & Fundamental Analysis...")
    sys.path.insert(0, str(BASE / "market-intel-division"))
    from core.technical_analyst import TechnicalAnalyst
    from core.fundamental_analyst import FundamentalAnalyst

    ta = TechnicalAnalyst()
    fa = FundamentalAnalyst()

    # Stocks to scan
    if quick:
        scan_stocks = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
            "SBIN.NS", "BAJFINANCE.NS", "SUNPHARMA.NS", "LT.NS", "MARUTI.NS",
            "TITAN.NS", "HCLTECH.NS", "ADANIENT.NS", "ONGC.NS", "NTPC.NS",
            "COALINDIA.NS", "HAL.NS", "BHARTIARTL.NS", "WIPRO.NS", "TATASTEEL.NS",
        ]
    else:
        scan_stocks = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
            "SBIN.NS", "BAJFINANCE.NS", "SUNPHARMA.NS", "LT.NS", "MARUTI.NS",
            "TITAN.NS", "HCLTECH.NS", "ADANIENT.NS", "ONGC.NS", "NTPC.NS",
            "COALINDIA.NS", "HAL.NS", "BHARTIARTL.NS", "WIPRO.NS", "TATASTEEL.NS",
            "JSWSTEEL.NS", "HINDALCO.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS",
            "NESTLEIND.NS", "BRITANNIA.NS", "ASIANPAINT.NS", "KOTAKBANK.NS",
            "AXISBANK.NS", "INDUSINDBK.NS", "TECHM.NS", "DLF.NS", "GODREJPROP.NS",
            "IRFC.NS", "SUZLON.NS", "TATAPOWER.NS", "ADANIGREEN.NS",
            "IRCTC.NS", "ZOMATO.NS", "PIIND.NS", "CHOLAFIN.NS",
            "MUTHOOTFIN.NS", "BEL.NS", "DIXON.NS", "TRENT.NS",
            "INDIGO.NS", "ULTRACEMCO.NS", "POWERGRID.NS", "ITC.NS",
        ]

    ta_results = {}
    fa_results = {}
    logger.info(f"  Scanning {len(scan_stocks)} stocks...")

    for sym in scan_stocks:
        t = ta.analyze(sym)
        f = fa.analyze(sym)
        name = sym.replace(".NS", "")
        if t:
            ta_results[name] = t
        if f:
            fa_results[name] = f

    logger.info(f"  TA done: {len(ta_results)} | FA done: {len(fa_results)}")

    # ── STEP 2: Social Media Buzz ─────────────────────────────────
    logger.info("\n📱 STEP 2: Social Media Buzz Scan...")
    try:
        from global_scraper import GlobalSocialScraper
        from sentiment_analyzer import SentimentAnalyzer
        from stock_mention_tracker import StockMentionTracker

        scraper = GlobalSocialScraper()
        sentiment = SentimentAnalyzer()
        tracker = StockMentionTracker(mode="india")

        social_data = scraper.fetch_all()
        posts = social_data.get("posts", [])
        trending = tracker.get_trending(posts, top_n=15)
        ticker_sentiment = tracker.get_sentiment_per_ticker(posts, sentiment)
        logger.info(f"  Social: {len(posts)} posts, {len(trending)} trending tickers")
    except Exception as e:
        logger.warning(f"  Social scan skipped: {e}")
        trending = []
        ticker_sentiment = {}

    # ── STEP 3: News Intelligence ─────────────────────────────────
    logger.info("\n📰 STEP 3: News Intelligence...")
    try:
        from news_scraper import NewsScraper
        from event_classifier import EventClassifier
        from impact_analyzer import ImpactAnalyzer

        sys.path.insert(0, str(BASE / "global-intel-agent"))
        with open(BASE / "global-intel-agent/config/intel_config.json") as f:
            intel_config = json.load(f)

        ns = NewsScraper(intel_config)
        ec = EventClassifier(intel_config)
        ia = ImpactAnalyzer()

        articles = ns.fetch_all()
        articles = ec.classify_all(articles)
        articles = ia.analyze_all(articles)
        critical_news = [a for a in articles if a.get("severity") == "CRITICAL"]
        logger.info(f"  News: {len(articles)} articles, {len(critical_news)} critical")
    except Exception as e:
        logger.warning(f"  News scan skipped: {e}")
        critical_news = []

    # ── STEP 4: Buzz Hunter ───────────────────────────────────────
    logger.info("\n🕵️ STEP 4: Buzz Hunter (internet buzz)...")
    try:
        sys.path.insert(0, str(BASE / "buzz-hunter-agent"))
        from buzz_scanner import BuzzScanner
        from buzz_scorer import BuzzScorer

        scanner = BuzzScanner()
        news_buzz = scanner.scan_news_buzz()
        logger.info(f"  Buzz: {len(news_buzz)} tickers buzzing")
    except Exception as e:
        logger.warning(f"  Buzz scan skipped: {e}")
        news_buzz = {}

    # ── STEP 5: CONSENSUS ENGINE ──────────────────────────────────
    logger.info("\n🧠 STEP 5: Consensus Engine — Combining all signals...")
    ce = ConsensusEngine()

    all_stocks_signals = {}
    for stock in ta_results:
        signals = {}

        # Technical signal
        t = ta_results.get(stock, {})
        if t:
            score = t.get("technical_score", 50)
            dirn = "BULLISH" if score >= 55 else ("BEARISH" if score < 45 else "NEUTRAL")
            signals["Technical"] = {
                "direction": dirn, "score": score,
                "signal": t.get("recommendation", ""), "weight": 1.5
            }

        # Fundamental signal
        f = fa_results.get(stock, {})
        if f:
            score = f.get("fundamental_score", 50)
            dirn = "BULLISH" if score >= 60 else ("BEARISH" if score < 40 else "NEUTRAL")
            signals["Fundamental"] = {
                "direction": dirn, "score": score,
                "signal": f.get("classification", ""), "weight": 1.5
            }

        # Social buzz signal
        if stock in ticker_sentiment:
            s = ticker_sentiment[stock]
            dirn = s.get("label", "NEUTRAL")
            signals["SocialMedia"] = {
                "direction": dirn, "score": int(s.get("compound", 0) * 50 + 50),
                "signal": f"{s.get('mentions',0)} mentions", "weight": 0.8
            }

        # News buzz signal
        if stock in news_buzz:
            count = news_buzz[stock]
            signals["BuzzHunter"] = {
                "direction": "BULLISH" if count >= 3 else "NEUTRAL",
                "score": min(80, count * 15),
                "signal": f"Trending: {count} mentions", "weight": 1.0
            }

        if signals:
            all_stocks_signals[stock] = signals

    consensus_results = ce.evaluate_batch(all_stocks_signals)

    # ── STEP 6: RISK AGENT ────────────────────────────────────────
    logger.info("\n🛡️ STEP 6: Risk Agent — Position sizing...")
    risk = RiskAgent(capital=100000)

    final_calls = []
    for r in consensus_results:
        if r["consensus"] in ("STRONG BUY", "BUY") and r["confidence"] >= 50:
            stock = r["stock"]
            sl_data = risk.auto_stop_loss(stock)
            if sl_data:
                plan = risk.calculate_position(
                    stock, sl_data["price"], sl_data["stop_loss"]
                )
                if plan.get("approved"):
                    final_calls.append({
                        "stock":       stock,
                        "consensus":   r["consensus"],
                        "confidence":  r["confidence"],
                        "agents":      f"{r['bullish_count']}/{r['agents_total']}",
                        "entry":       sl_data["price"],
                        "stop_loss":   sl_data["stop_loss"],
                        "target":      sl_data["target"],
                        "quantity":    plan["quantity"],
                        "risk_reward": plan["risk_reward"],
                        "invest":      plan["position_value"],
                    })

    # ── FINAL OUTPUT ──────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  📞 MUDHOLKARS & CO — FINAL CALLS")
    print(f"  {ist}")
    print(f"  Pipeline: TA + FA + Social + News + Buzz → Consensus → Risk")
    print("=" * 65)

    if final_calls:
        print(f"\n  ✅ APPROVED TRADES ({len(final_calls)} stocks)")
        print("  " + "-" * 58)
        for i, c in enumerate(final_calls[:7], 1):
            print(f"    #{i}  {c['stock']:12s}  {c['consensus']:12s}  "
                  f"Confidence={c['confidence']:.0f}%  Agents={c['agents']}")
            print(f"        Entry: ₹{c['entry']:.2f}  |  SL: ₹{c['stop_loss']:.2f}  "
                  f"|  Target: ₹{c['target']:.2f}")
            print(f"        Qty: {c['quantity']}  |  Invest: ₹{c['invest']:,.0f}  "
                  f"|  R:R = 1:{c['risk_reward']}")
            print()
    else:
        print("\n  ⚠️ No high-conviction calls today.")
        print("  Agents say: WAIT — no strong consensus.")

    # Show consensus for all stocks
    print(f"\n  📊 ALL STOCKS CONSENSUS")
    print("  " + "-" * 58)
    for r in consensus_results[:15]:
        icon = "🟢" if "BUY" in r["consensus"] else ("🔴" if "SELL" in r["consensus"] else "🟡")
        print(f"    {icon} {r['stock']:12s}  {r['consensus']:12s}  "
              f"Confidence={r['confidence']:.0f}%  "
              f"Bull={r['bullish_count']} Bear={r['bearish_count']}")

    # Critical news
    if critical_news:
        print(f"\n  🚨 CRITICAL NEWS ({len(critical_news)})")
        print("  " + "-" * 58)
        for n in critical_news[:3]:
            print(f"    [{n.get('category','')}] {n.get('title','')[:60]}")

    print(f"\n  ⚠️  DISCLAIMER: Agent output. Not financial advice. Use SL always.")
    print("=" * 65)

    # Save report
    Path("reports").mkdir(exist_ok=True)
    report = {
        "timestamp": ist,
        "final_calls": final_calls,
        "consensus": [{"stock": r["stock"], "verdict": r["consensus"],
                       "confidence": r["confidence"]} for r in consensus_results],
        "critical_news": [n.get("title", "") for n in critical_news[:5]],
    }
    with open("reports/daily_calls_latest.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info("Report saved: reports/daily_calls_latest.json")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    run_full_pipeline(quick=args.quick)
