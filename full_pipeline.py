"""
full_pipeline.py
----------------
Mudholkars and Co — FULL AGENT PIPELINE (v2.0 — All Agents Wired)

Runs ALL agents → feeds into Consensus Engine → Risk Agent → Final Calls

Agents contributing to consensus (8+):
  1. Technical Analyst     (weight 1.5)
  2. Fundamental Analyst   (weight 1.5)
  3. Social Media Buzz     (weight 0.8)
  4. Buzz Hunter           (weight 1.0)
  5. FII/DII Flow          (weight 1.3)
  6. Options PCR           (weight 1.2)
  7. Breakout Scanner      (weight 1.5)
  8. Sector Momentum       (weight 1.2)
  9. Promoter Tracker      (weight 1.0)
  10. Earnings Calendar    (weight -1.0, safety filter)
  11. Market Historian     (weight 1.3)
  12. Enhanced Strategy ML (weight 1.5)

Usage:
  python full_pipeline.py              # full run
  python full_pipeline.py --quick      # quick scan (top 200 stocks only)

Best time to run:
  - 9:30 AM IST (30 min after market open — data settled)
  - 12:00 PM IST (mid-day check)
  - 3:30 PM IST (before close — EOD setup)
"""

import os
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

os.chdir(str(BASE))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("FullPipeline")

from consensus_engine import ConsensusEngine
from risk_agent import RiskAgent
from nse_data_feed import NSEDataFeed

# Capital — single source of truth
CAPITAL = int(os.environ.get("INITIAL_CAPITAL", 1000000))


def _load_focus_stocks() -> list:
    """
    On Monday, read weekend_strategy.json to prioritize focus stocks.
    Returns a list of stock symbols to scan first / with priority.
    """
    try:
        strategy_file = BASE / "reports" / "weekend_strategy.json"
        if strategy_file.exists():
            data = json.loads(strategy_file.read_text())
            picks = data.get("next_week_picks", [])
            focus = [p["stock"] for p in picks if "stock" in p]
            if focus:
                logger.info(f"  📋 Weekend strategy focus: {focus[:10]}")
            return focus
    except Exception as e:
        logger.warning(f"  Could not load weekend strategy: {e}")
    return []


def run_full_pipeline(quick: bool = False):
    ist = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %H:%M IST")
    today = datetime.now(ZoneInfo("Asia/Kolkata"))
    logger.info("=" * 65)
    logger.info("  🏢 MUDHOLKARS & CO — FULL AGENT PIPELINE v2.0")
    logger.info(f"  {ist} | Capital: ₹{CAPITAL:,.0f}")
    logger.info("=" * 65)

    # Load weekend focus stocks (especially useful on Mondays)
    focus_stocks = _load_focus_stocks()

    # ── STEP 1: Market Regime Detection ───────────────────────────
    logger.info("\n🌡️ STEP 1: Market Regime Detection...")
    regime = {"regime": "UNKNOWN", "aggression": "MEDIUM", "score": 50}
    try:
        from market_regime import MarketRegimeDetector
        regime = MarketRegimeDetector().detect()
        logger.info(f"  Regime: {regime['regime']} | Score: {regime.get('score', '?')} | Aggression: {regime['aggression']}")
    except Exception as e:
        logger.warning(f"  Market regime detection failed: {e}")

    # ── STEP 2: Technical + Fundamental Analysis ──────────────────
    logger.info("\n📈 STEP 2: Technical & Fundamental Analysis...")
    from core.technical_analyst import TechnicalAnalyst
    from core.fundamental_analyst import FundamentalAnalyst
    from core.stock_universe import StockUniverse

    ta = TechnicalAnalyst()
    fa = FundamentalAnalyst()

    su = StockUniverse(str(BASE / "market-intel-division"))
    all_nse = su.get_all_stocks()

    if quick:
        scan_stocks = [f"{s}.NS" for s in all_nse[:200]]
    else:
        scan_stocks = [f"{s}.NS" for s in all_nse]
        logger.info(f"  FULL SCAN MODE: {len(scan_stocks)} stocks")

    # Prioritize focus stocks (put them first)
    if focus_stocks:
        focus_set = set(focus_stocks)
        prioritized = [f"{s}.NS" for s in focus_stocks if f"{s}.NS" in scan_stocks]
        rest = [s for s in scan_stocks if s.replace(".NS", "") not in focus_set]
        scan_stocks = prioritized + rest

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

    # ── STEP 3: Social Media Buzz ─────────────────────────────────
    logger.info("\n📱 STEP 3: Social Media Buzz Scan...")
    trending = []
    ticker_sentiment = {}
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

    # ── STEP 4: News Intelligence ─────────────────────────────────
    logger.info("\n📰 STEP 4: News Intelligence...")
    critical_news = []
    try:
        from news_scraper import NewsScraper
        from event_classifier import EventClassifier
        from impact_analyzer import ImpactAnalyzer

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

    # ── STEP 5: Buzz Hunter ───────────────────────────────────────
    logger.info("\n🕵️ STEP 5: Buzz Hunter (internet buzz)...")
    news_buzz = {}
    try:
        from buzz_scanner import BuzzScanner

        scanner = BuzzScanner()
        news_buzz = scanner.scan_news_buzz()
        logger.info(f"  Buzz: {len(news_buzz)} tickers buzzing")
    except Exception as e:
        logger.warning(f"  Buzz scan skipped: {e}")

    # ══════════════════════════════════════════════════════════════
    # STEP 6: BUILD CONSENSUS SIGNALS (all agents feed in here)
    # ══════════════════════════════════════════════════════════════
    logger.info("\n🧠 STEP 6: Building agent signals for all stocks...")

    all_stocks_signals = {}
    for stock in ta_results:
        signals = {}

        # ── Agent 1: Technical Analyst ──
        t = ta_results.get(stock, {})
        if t:
            score = t.get("technical_score", 50)
            dirn = "BULLISH" if score >= 55 else ("BEARISH" if score < 45 else "NEUTRAL")
            signals["Technical"] = {
                "direction": dirn, "score": score,
                "signal": t.get("recommendation", ""), "weight": 1.5
            }

        # ── Agent 2: Fundamental Analyst ──
        f = fa_results.get(stock, {})
        if f:
            score = f.get("fundamental_score", 50)
            dirn = "BULLISH" if score >= 60 else ("BEARISH" if score < 40 else "NEUTRAL")
            signals["Fundamental"] = {
                "direction": dirn, "score": score,
                "signal": f.get("classification", ""), "weight": 1.5
            }

        # ── Agent 3: Social Media Buzz ──
        if stock in ticker_sentiment:
            s = ticker_sentiment[stock]
            dirn = s.get("label", "NEUTRAL")
            signals["SocialMedia"] = {
                "direction": dirn, "score": int(s.get("compound", 0) * 50 + 50),
                "signal": f"{s.get('mentions', 0)} mentions", "weight": 0.8
            }

        # ── Agent 4: Buzz Hunter ──
        if stock in news_buzz:
            count = news_buzz[stock]
            signals["BuzzHunter"] = {
                "direction": "BULLISH" if count >= 3 else "NEUTRAL",
                "score": min(80, count * 15),
                "signal": f"Trending: {count} mentions", "weight": 1.0
            }

        if signals:
            all_stocks_signals[stock] = signals

    # ── STEP 7: NSE DATA FEED (FII/DII + Options) ───────────────
    logger.info("\n🏦 STEP 7: NSE FII/DII + Options Chain...")
    try:
        nse = NSEDataFeed()
        market_signal = nse.get_market_signal()
        fii_bias = market_signal.get("fii_dii", {}).get("market_impact", "NEUTRAL")
        pcr_sig = market_signal.get("nifty_pcr_signal", "NEUTRAL")
        logger.info(f"  FII: {market_signal.get('fii_dii', {}).get('signal', '?')} | "
                    f"PCR: {market_signal.get('nifty_pcr', 0):.2f} | "
                    f"Combined: {market_signal.get('combined_signal', '?')}")

        # ── Agent 5: FII/DII Flow ──
        # ── Agent 6: Options PCR ──
        for stock in all_stocks_signals:
            if fii_bias in ("BULLISH", "MILD_BULLISH"):
                all_stocks_signals[stock]["FII_DII"] = {
                    "direction": "BULLISH", "score": 68,
                    "signal": f"FII buying {market_signal.get('fii_dii', {}).get('fii_net_cr', 0):+.0f}Cr",
                    "weight": 1.3
                }
            elif fii_bias in ("BEARISH", "MILD_BEARISH"):
                all_stocks_signals[stock]["FII_DII"] = {
                    "direction": "BEARISH", "score": 32,
                    "signal": "FII selling", "weight": 1.3
                }

            if pcr_sig in ("STRONG_BULLISH", "BULLISH"):
                all_stocks_signals[stock]["Options"] = {
                    "direction": "BULLISH", "score": 65,
                    "signal": f"PCR={market_signal.get('nifty_pcr', 0):.2f} bullish",
                    "weight": 1.2
                }
            elif pcr_sig == "BEARISH":
                all_stocks_signals[stock]["Options"] = {
                    "direction": "BEARISH", "score": 35,
                    "signal": "PCR bearish", "weight": 1.2
                }
    except Exception as e:
        logger.warning(f"  NSE feed skipped: {e}")

    # ── STEP 8: Advanced Scanners ─────────────────────────────────
    logger.info("\n🔬 STEP 8: Breakouts + Sector Momentum + Promoter + Earnings...")
    try:
        from breakout_scanner import BreakoutScanner
        from sector_momentum import SectorMomentumScorer
        from promoter_tracker import PromoterTracker
        from earnings_calendar import EarningsCalendar

        # ── Agent 7: Breakout Scanner ──
        breakout_symbols = [s.replace('.NS', '') for s in scan_stocks[:100]]
        breakouts = BreakoutScanner().scan(breakout_symbols)
        if breakouts:
            logger.info(f"  Breakouts: {len(breakouts)} stocks at 52-week levels")
            for b in breakouts:
                sym = b.get("symbol", "")
                if sym in all_stocks_signals:
                    btype = b.get("type", "BREAKOUT")
                    all_stocks_signals[sym]["Breakout"] = {
                        "direction": "BULLISH" if btype == "HIGH" else "BEARISH",
                        "score": 78 if btype == "HIGH" else 30,
                        "signal": f"52-week {btype} at ₹{b.get('price', 0):.0f}",
                        "weight": 1.5
                    }

        # ── Agent 8: Sector Momentum ──
        sector_scorer = SectorMomentumScorer()
        top_sectors = sector_scorer.get_top_sectors()
        hot_sectors = [s["sector"] for s in top_sectors if s.get("signal") == "BUY"]
        cold_sectors = [s["sector"] for s in top_sectors if s.get("signal") == "AVOID"]
        logger.info(f"  Hot sectors: {hot_sectors[:3]} | Cold: {cold_sectors[:3]}")

        # Map stocks to sectors and add sector signal
        sector_map = {}
        from sector_momentum import SECTOR_STOCKS
        for sector, stocks in SECTOR_STOCKS.items():
            for s in stocks:
                sector_map[s.replace(".NS", "")] = sector

        for stock in all_stocks_signals:
            sector = sector_map.get(stock, "")
            if sector in hot_sectors:
                all_stocks_signals[stock]["SectorMomentum"] = {
                    "direction": "BULLISH", "score": 70,
                    "signal": f"{sector} sector is hot", "weight": 1.2
                }
            elif sector in cold_sectors:
                all_stocks_signals[stock]["SectorMomentum"] = {
                    "direction": "BEARISH", "score": 30,
                    "signal": f"{sector} sector weak", "weight": 1.2
                }

        # ── Agent 9: Promoter Tracker (sample top consensus stocks) ──
        promoter = PromoterTracker()
        top_candidate_stocks = sorted(
            all_stocks_signals.keys(),
            key=lambda s: sum(d.get("score", 50) for d in all_stocks_signals[s].values()),
            reverse=True
        )[:30]

        for stock in top_candidate_stocks:
            try:
                p_result = promoter.check_promoter_activity(stock)
                if p_result and p_result.get("signal") == "BUYING":
                    all_stocks_signals[stock]["PromoterBuying"] = {
                        "direction": "BULLISH", "score": 72,
                        "signal": f"Promoter buying ({p_result.get('promoter_pct', 0):.0f}%)",
                        "weight": 1.0
                    }
                elif p_result and not p_result.get("safe"):
                    all_stocks_signals[stock]["PromoterRisk"] = {
                        "direction": "BEARISH", "score": 25,
                        "signal": f"Low promoter ({p_result.get('promoter_pct', 0):.0f}%)",
                        "weight": 1.0
                    }
            except Exception:
                pass

        # ── Agent 10: Earnings Calendar (safety filter) ──
        earnings = EarningsCalendar()
        earnings_data = earnings.get_upcoming_results(top_candidate_stocks)
        for stock, e_info in earnings_data.items():
            if not e_info.get("safe_to_trade", True):
                all_stocks_signals.setdefault(stock, {})["EarningsRisk"] = {
                    "direction": "NEUTRAL", "score": 40,
                    "signal": f"Earnings in {e_info.get('days_to_results', '?')} days — risky",
                    "weight": -1.0  # negative weight = penalty
                }

    except Exception as e:
        logger.warning(f"  Advanced scanners partially failed: {e}")

    # ── STEP 9: Market Historian ──────────────────────────────────
    logger.info("\n📚 STEP 9: Market Historian — Pattern matching...")
    try:
        from market_historian import MarketHistorian
        historian = MarketHistorian()

        # Get current market context
        hist_analysis = historian.analyze_current_market()
        if hist_analysis:
            pattern = hist_analysis.get("similar_pattern", "")
            confidence = hist_analysis.get("confidence", 0)
            if pattern and confidence >= 60:
                logger.info(f"  Historian: '{pattern}' (confidence {confidence}%)")
                # Apply historian bias to all stocks
                bias = hist_analysis.get("market_bias", "NEUTRAL")
                if bias in ("BULLISH", "RECOVERY"):
                    for stock in all_stocks_signals:
                        all_stocks_signals[stock]["MarketHistorian"] = {
                            "direction": "BULLISH", "score": 65,
                            "signal": f"Historical pattern: {pattern}", "weight": 1.3
                        }
                elif bias in ("BEARISH", "CRASH_WARNING"):
                    for stock in all_stocks_signals:
                        all_stocks_signals[stock]["MarketHistorian"] = {
                            "direction": "BEARISH", "score": 30,
                            "signal": f"Caution: {pattern}", "weight": 1.3
                        }
    except Exception as e:
        logger.warning(f"  Market Historian skipped: {e}")

    # ── STEP 10: Enhanced Strategy ML Check ───────────────────────
    logger.info("\n🤖 STEP 10: Enhanced Strategy ML predictions...")
    try:
        from enhanced_strategy import FinalStrategy, MarketFilter

        market_filter = MarketFilter()
        market_check = market_filter.is_market_safe()
        if not market_check.get("safe", True):
            logger.info(f"  ⚠️ Market filter says UNSAFE: {market_check.get('reason', '')}")
            # Penalize all stocks
            for stock in all_stocks_signals:
                all_stocks_signals[stock]["MarketFilter"] = {
                    "direction": "BEARISH", "score": 25,
                    "signal": f"Market unsafe: {market_check.get('bias', 'BEARISH')}",
                    "weight": 1.5
                }
        else:
            logger.info(f"  ✅ Market filter: SAFE ({market_check.get('bias', 'OK')})")

        # ML pattern matching on top candidates
        from enhanced_strategy import MLPatternMatcher
        ml = MLPatternMatcher()
        for stock in top_candidate_stocks[:15]:
            try:
                t = ta_results.get(stock, {})
                rsi = t.get("rsi", 50)
                macd_bull = t.get("macd_signal", "") == "BULLISH"
                above_ma50 = t.get("above_ma50", False)
                vol_spike = t.get("volume_spike", False)

                prediction = ml.predict(f"{stock}.NS", rsi, macd_bull, above_ma50, vol_spike)
                if prediction.get("confidence") in ("HIGH", "MEDIUM") and prediction.get("probability", 50) >= 65:
                    all_stocks_signals[stock]["ML_Pattern"] = {
                        "direction": "BULLISH", "score": int(prediction["probability"]),
                        "signal": f"ML: {prediction['probability']}% win prob ({prediction.get('sample_size', 0)} samples)",
                        "weight": 1.5
                    }
                elif prediction.get("confidence") in ("HIGH", "MEDIUM") and prediction.get("probability", 50) <= 35:
                    all_stocks_signals[stock]["ML_Pattern"] = {
                        "direction": "BEARISH", "score": int(prediction["probability"]),
                        "signal": f"ML: only {prediction['probability']}% win prob",
                        "weight": 1.5
                    }
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"  Enhanced Strategy ML skipped: {e}")

    # ── STEP 11: CONSENSUS ENGINE ─────────────────────────────────
    logger.info("\n🧠 STEP 11: Consensus Engine — Final verdict...")
    ce = ConsensusEngine()

    # Apply regime-based minimum score
    min_score = regime.get("min_score_override", 50)
    consensus_results = ce.evaluate_batch(all_stocks_signals)

    # Count how many agents contributed
    agent_counts = {}
    for stock, signals in all_stocks_signals.items():
        for agent_name in signals:
            agent_counts[agent_name] = agent_counts.get(agent_name, 0) + 1
    logger.info(f"  Active agents: {len(agent_counts)} — {list(agent_counts.keys())}")

    # ── STEP 12: RISK AGENT ───────────────────────────────────────
    logger.info("\n🛡️ STEP 12: Risk Agent — Position sizing...")
    risk = RiskAgent(capital=CAPITAL)

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
    print(f"  {ist} | Agents: {len(agent_counts)} | Regime: {regime['regime']}")
    print(f"  Pipeline: TA + FA + Social + News + Buzz + FII + Sector + ML → Consensus → Risk")
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
    print(f"\n  📊 ALL STOCKS CONSENSUS (top 20)")
    print("  " + "-" * 58)
    for r in consensus_results[:20]:
        icon = "🟢" if "BUY" in r["consensus"] else ("🔴" if "SELL" in r["consensus"] else "🟡")
        print(f"    {icon} {r['stock']:12s}  {r['consensus']:12s}  "
              f"Confidence={r['confidence']:.0f}%  "
              f"Bull={r['bullish_count']} Bear={r['bearish_count']}")

    # Critical news
    if critical_news:
        print(f"\n  🚨 CRITICAL NEWS ({len(critical_news)})")
        print("  " + "-" * 58)
        for n in critical_news[:3]:
            print(f"    [{n.get('category', '')}] {n.get('title', '')[:60]}")

    print(f"\n  ⚠️  DISCLAIMER: Agent output. Not financial advice. Use SL always.")
    print("=" * 65)

    # Save report
    Path("reports").mkdir(exist_ok=True)
    report = {
        "timestamp": ist,
        "capital": CAPITAL,
        "regime": regime.get("regime", "UNKNOWN"),
        "agents_active": len(agent_counts),
        "agent_names": list(agent_counts.keys()),
        "final_calls": final_calls,
        "consensus": [{"stock": r["stock"], "verdict": r["consensus"],
                       "confidence": r["confidence"]} for r in consensus_results],
        "critical_news": [n.get("title", "") for n in critical_news[:5]],
        "focus_stocks": focus_stocks[:10],
    }
    with open("reports/daily_calls_latest.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info("Report saved: reports/daily_calls_latest.json")

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Scan 200 stocks (market hours)")
    args = parser.parse_args()
    run_full_pipeline(quick=args.quick)
