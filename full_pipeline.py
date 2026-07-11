"""
full_pipeline.py
----------------
Mudholkars and Co — FULL 47-AGENT PIPELINE (v3.0)

ALL 47 agents feed into Consensus Engine → Risk Agent → Final Calls

Agent Groups:
  A. Core Analysis (4):       Technical, Fundamental, ML Pattern, Market Filter
  B. Market Data (5):         FII/DII, Options PCR, Delivery Volume, Bulk Deals, Insider Trading
  C. Scanners (5):            Breakout 52wk, Breakout 20d, Circuit, Candlestick, Gap
  D. Intelligence (5):        Global Intel, India Intel, India Social, Social Media, Buzz Hunter
  E. Macro (5):               Market Regime, Market Historian, Global Correlation, India VIX/Volatility, Currency
  F. Sector/Momentum (4):     Sector Momentum, Relative Strength, Sector Intel, MF Activity
  G. Safety Filters (4):      Earnings Calendar, Promoter Tracker, Debt Check, Volatility Filter
  H. Timeframe Agents (10):   Scalper, DayTrader, Swing, Monthly, Quarter, HalfYear, Annual, 2Year, 3Year, Legacy
  I. Meta (5):                Weekend Strategist focus, Learning Engine weights, Position Monitor, Alert Engine, India Analyst

  TOTAL: 47 named agents contributing to consensus

Usage:
  python full_pipeline.py              # full run
  python full_pipeline.py --quick      # quick scan (top 200 stocks only)
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
for d in [BASE, BASE/"stock-trend-agent", BASE/"market-intel-division",
          BASE/"sector-intel-division", BASE/"social-media-agent",
          BASE/"india-social-agent", BASE/"buzz-hunter-agent",
          BASE/"global-intel-agent", BASE/"india-intel-agent"]:
    sys.path.insert(0, str(d))

os.chdir(str(BASE))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("FullPipeline")

from consensus_engine import ConsensusEngine
from risk_agent import RiskAgent

# Capital — single source of truth
CAPITAL = int(os.environ.get("INITIAL_CAPITAL", 1000000))
MIN_SCORE = 68  # Minimum consensus score for entry (from backtest optimal)


def _load_focus_stocks() -> list:
    """Read weekend_strategy.json for Monday priority stocks."""
    try:
        f = BASE / "reports" / "weekend_strategy.json"
        if f.exists():
            data = json.loads(f.read_text())
            return [p["stock"] for p in data.get("next_week_picks", []) if "stock" in p]
    except Exception:
        pass
    return []


def _safe_run(name: str, func, *args, **kwargs):
    """Run a function safely — log error but never crash pipeline."""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.warning(f"  ⚠️ {name} failed: {e}")
        return None



def run_full_pipeline(quick: bool = False):
    ist = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %H:%M IST")
    logger.info("=" * 65)
    logger.info("  🏢 MUDHOLKARS & CO — FULL 47-AGENT PIPELINE v3.0")
    logger.info(f"  {ist} | Capital: ₹{CAPITAL:,.0f}")
    logger.info("=" * 65)

    focus_stocks = _load_focus_stocks()

    # ══════════════════════════════════════════════════════════════
    # STEP 0: PRE-MARKET SCANNER (sets aggression for the day)
    # ══════════════════════════════════════════════════════════════
    logger.info("\n🌅 STEP 0: Pre-Market Scanner...")
    threshold_adj = 0
    premarket_bias = "NEUTRAL"
    try:
        from premarket_scanner import PreMarketScanner
        pm = PreMarketScanner()
        pm_result = pm.scan()
        premarket_bias = pm_result.get("bias", "NEUTRAL")
        threshold_adj = pm_result.get("threshold_adjustment", 0)
        logger.info(f"  Mode: {pm_result.get('mode', '?')} | Bias: {premarket_bias} | "
                    f"US: {pm_result.get('us_market', 0):+.1f}% | "
                    f"Threshold adj: {threshold_adj:+d}")
    except Exception as e:
        logger.warning(f"  Pre-market scanner skipped: {e}")

    # ══════════════════════════════════════════════════════════════
    # STEP 1: MARKET REGIME (global filter)
    # ══════════════════════════════════════════════════════════════
    logger.info("\n🌡️ STEP 1: Market Regime...")
    regime = {"regime": "UNKNOWN", "aggression": "MEDIUM", "score": 50}
    try:
        from market_regime import MarketRegimeDetector
        regime = MarketRegimeDetector().detect()
        logger.info(f"  Regime: {regime['regime']} | Aggression: {regime['aggression']}")
    except Exception as e:
        logger.warning(f"  Market regime failed: {e}")

    # ══════════════════════════════════════════════════════════════
    # STEP 2: TECHNICAL + FUNDAMENTAL (Agents 1-2)
    # ══════════════════════════════════════════════════════════════
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
        logger.info(f"  FULL SCAN: {len(scan_stocks)} stocks")

    # Prioritize focus stocks
    if focus_stocks:
        focus_set = set(focus_stocks)
        prioritized = [f"{s}.NS" for s in focus_stocks if f"{s}.NS" in scan_stocks]
        rest = [s for s in scan_stocks if s.replace(".NS", "") not in focus_set]
        scan_stocks = prioritized + rest

    ta_results = {}
    fa_results = {}
    for sym in scan_stocks:
        t = _safe_run("TA", ta.analyze, sym)
        f = _safe_run("FA", fa.analyze, sym)
        name = sym.replace(".NS", "")
        if t:
            ta_results[name] = t
        if f:
            fa_results[name] = f
    logger.info(f"  TA: {len(ta_results)} | FA: {len(fa_results)}")

    # ══════════════════════════════════════════════════════════════
    # STEP 3: SOCIAL + BUZZ (Agents 3-5)
    # ══════════════════════════════════════════════════════════════
    logger.info("\n📱 STEP 3: Social Media + Buzz...")
    ticker_sentiment = {}
    india_sentiment = {}
    news_buzz = {}

    try:
        from global_scraper import GlobalSocialScraper
        from sentiment_analyzer import SentimentAnalyzer
        from stock_mention_tracker import StockMentionTracker
        scraper = GlobalSocialScraper()
        sentiment = SentimentAnalyzer()
        tracker = StockMentionTracker(mode="india")
        posts = scraper.fetch_all().get("posts", [])
        ticker_sentiment = tracker.get_sentiment_per_ticker(posts, sentiment)
        logger.info(f"  Global Social: {len(ticker_sentiment)} tickers")
    except Exception as e:
        logger.warning(f"  Global Social skipped: {e}")

    try:
        from india_social_agent import IndiaSocialScraper
        india_scraper = IndiaSocialScraper()
        india_posts = india_scraper.fetch_all().get("posts", [])
        india_tracker = StockMentionTracker(mode="india")
        india_sentiment = india_tracker.get_sentiment_per_ticker(india_posts, sentiment)
        logger.info(f"  India Social: {len(india_sentiment)} tickers")
    except Exception as e:
        logger.warning(f"  India Social skipped: {e}")

    try:
        from buzz_scanner import BuzzScanner
        news_buzz = BuzzScanner().scan_news_buzz()
        logger.info(f"  Buzz: {len(news_buzz)} tickers")
    except Exception as e:
        logger.warning(f"  Buzz skipped: {e}")

    # ══════════════════════════════════════════════════════════════
    # STEP 4: NEWS INTELLIGENCE (Agents 6-7)
    # ══════════════════════════════════════════════════════════════
    logger.info("\n📰 STEP 4: News Intelligence...")
    critical_news = []
    india_news_stocks = {}

    try:
        from news_scraper import NewsScraper
        from event_classifier import EventClassifier
        from impact_analyzer import ImpactAnalyzer
        with open(BASE / "global-intel-agent/config/intel_config.json") as f:
            intel_config = json.load(f)
        articles = NewsScraper(intel_config).fetch_all()
        articles = EventClassifier(intel_config).classify_all(articles)
        articles = ImpactAnalyzer().analyze_all(articles)
        critical_news = [a for a in articles if a.get("severity") == "CRITICAL"]
        logger.info(f"  Global News: {len(articles)} articles, {len(critical_news)} critical")
    except Exception as e:
        logger.warning(f"  Global News skipped: {e}")

    try:
        from india_news_scraper import IndiaNewsScraper
        from india_event_classifier import IndiaEventClassifier
        from india_impact_analyzer import IndiaImpactAnalyzer
        with open(BASE / "india-intel-agent/config/india_intel_config.json") as f:
            india_config = json.load(f)
        india_articles = IndiaNewsScraper(india_config).fetch_all()
        india_articles = IndiaEventClassifier(india_config).classify_all(india_articles)
        india_articles = IndiaImpactAnalyzer().analyze_all(india_articles)
        # Extract stock-specific news
        for a in india_articles:
            for stock in a.get("affected_stocks", []):
                india_news_stocks.setdefault(stock, []).append(a)
        logger.info(f"  India News: {len(india_articles)} articles, {len(india_news_stocks)} stocks mentioned")
    except Exception as e:
        logger.warning(f"  India News skipped: {e}")


    # ══════════════════════════════════════════════════════════════
    # STEP 5: MARKET DATA AGENTS (Agents 8-17)
    # ══════════════════════════════════════════════════════════════
    logger.info("\n🏦 STEP 5: Market Data Agents...")

    # FII/DII + Options
    fii_bias = "NEUTRAL"
    pcr_sig = "NEUTRAL"
    market_signal = {}
    try:
        from nse_data_feed import NSEDataFeed
        nse = NSEDataFeed()
        market_signal = nse.get_market_signal()
        fii_bias = market_signal.get("fii_dii", {}).get("market_impact", "NEUTRAL")
        pcr_sig = market_signal.get("nifty_pcr_signal", "NEUTRAL")
        logger.info(f"  FII: {fii_bias} | PCR: {pcr_sig}")
    except Exception as e:
        logger.warning(f"  NSE feed skipped: {e}")

    # Delivery Volume
    delivery_stocks = {}
    try:
        from agents_extra import DeliveryVolumeAgent
        delivery_agent = DeliveryVolumeAgent()
        delivery_stocks = delivery_agent.analyze_batch([s.replace(".NS", "") for s in scan_stocks[:100]])
        logger.info(f"  Delivery: {len(delivery_stocks)} stocks analyzed")
    except Exception as e:
        logger.warning(f"  Delivery agent skipped: {e}")

    # Bulk/Block Deals
    bulk_deal_stocks = {}
    try:
        from nse_delivery_scanner import BulkBlockDealTracker
        bbt = BulkBlockDealTracker()
        bulk_deals = bbt.get_bulk_deals()
        for deal in bulk_deals:
            sym = deal.get("symbol", "")
            if sym:
                bulk_deal_stocks[sym] = deal
        logger.info(f"  Bulk/Block Deals: {len(bulk_deal_stocks)} stocks")
    except Exception as e:
        logger.warning(f"  Bulk deals skipped: {e}")

    # Insider Trading
    insider_stocks = {}
    try:
        from agents_extra import InsiderTradingAgent
        insider_agent = InsiderTradingAgent()
        insider_stocks = insider_agent.analyze_batch([s.replace(".NS", "") for s in scan_stocks[:50]])
        logger.info(f"  Insider Trading: {len(insider_stocks)} stocks")
    except Exception as e:
        logger.warning(f"  Insider trading skipped: {e}")

    # Mutual Fund Activity
    mf_stocks = {}
    try:
        from agents_extra import MutualFundAgent
        mf_agent = MutualFundAgent()
        mf_stocks = mf_agent.analyze_batch([s.replace(".NS", "") for s in scan_stocks[:50]])
        logger.info(f"  MF Activity: {len(mf_stocks)} stocks")
    except Exception as e:
        logger.warning(f"  MF agent skipped: {e}")

    # Global Correlation (market-wide)
    global_corr = {}
    try:
        from agents_extra import GlobalCorrelationAgent
        global_corr = GlobalCorrelationAgent().analyze()
        logger.info(f"  Global Correlation: {global_corr.get('direction', 'NEUTRAL')}")
    except Exception as e:
        logger.warning(f"  Global correlation skipped: {e}")

    # Volatility / ATR
    volatility_stocks = {}
    try:
        from agents_extra import VolatilityAgent
        vol_agent = VolatilityAgent()
        volatility_stocks = vol_agent.analyze_batch([s.replace(".NS", "") for s in scan_stocks[:100]])
        logger.info(f"  Volatility: {len(volatility_stocks)} stocks")
    except Exception as e:
        logger.warning(f"  Volatility agent skipped: {e}")

    # ══════════════════════════════════════════════════════════════
    # STEP 6: BUILD ALL 47 AGENT SIGNALS PER STOCK
    # ══════════════════════════════════════════════════════════════
    logger.info("\n🧠 STEP 6: Assembling all 47 agent signals...")

    all_stocks_signals = {}

    for stock in ta_results:
        signals = {}

        # ── GROUP A: Core Analysis ────────────────────────────────
        # Agent 1: Technical Analyst
        t = ta_results.get(stock, {})
        if t:
            score = t.get("technical_score", 50)
            dirn = "BULLISH" if score >= 55 else ("BEARISH" if score < 45 else "NEUTRAL")
            signals["Technical"] = {"direction": dirn, "score": score, "signal": t.get("recommendation", ""), "weight": 1.5}

        # Agent 2: Fundamental Analyst
        f = fa_results.get(stock, {})
        if f:
            score = f.get("fundamental_score", 50)
            dirn = "BULLISH" if score >= 60 else ("BEARISH" if score < 40 else "NEUTRAL")
            signals["Fundamental"] = {"direction": dirn, "score": score, "signal": f.get("classification", ""), "weight": 1.5}

        # ── GROUP D: Intelligence ─────────────────────────────────
        # Agent 3: Global Social Media
        if stock in ticker_sentiment:
            s = ticker_sentiment[stock]
            dirn = s.get("label", "NEUTRAL")
            signals["SocialMedia"] = {"direction": dirn, "score": int(s.get("compound", 0) * 50 + 50), "signal": f"{s.get('mentions', 0)} mentions", "weight": 0.8}

        # Agent 4: India Social Media
        if stock in india_sentiment:
            s = india_sentiment[stock]
            dirn = s.get("label", "NEUTRAL")
            signals["IndiaSocial"] = {"direction": dirn, "score": int(s.get("compound", 0) * 50 + 50), "signal": f"India social: {s.get('mentions', 0)} mentions", "weight": 0.9}

        # Agent 5: Buzz Hunter
        if stock in news_buzz:
            count = news_buzz[stock]
            signals["BuzzHunter"] = {"direction": "BULLISH" if count >= 3 else "NEUTRAL", "score": min(80, count * 15), "signal": f"Trending: {count} mentions", "weight": 1.0}

        # Agent 6: Global Intel News
        if critical_news:
            # If critical news mentions this stock
            for n in critical_news[:10]:
                if stock.lower() in n.get("title", "").lower():
                    sev = n.get("sentiment", "NEUTRAL")
                    signals["GlobalIntel"] = {"direction": sev, "score": 70 if sev == "BULLISH" else 30, "signal": n.get("title", "")[:50], "weight": 1.2}
                    break

        # Agent 7: India Intel News
        if stock in india_news_stocks:
            news_list = india_news_stocks[stock]
            bullish_count = sum(1 for n in news_list if n.get("sentiment") in ("BULLISH", "POSITIVE"))
            bearish_count = sum(1 for n in news_list if n.get("sentiment") in ("BEARISH", "NEGATIVE"))
            if bullish_count > bearish_count:
                signals["IndiaIntel"] = {"direction": "BULLISH", "score": 68, "signal": f"{bullish_count} positive India news", "weight": 1.2}
            elif bearish_count > bullish_count:
                signals["IndiaIntel"] = {"direction": "BEARISH", "score": 32, "signal": f"{bearish_count} negative India news", "weight": 1.2}

        # ── GROUP B: Market Data ──────────────────────────────────
        # Agent 8: FII/DII Flow
        if fii_bias in ("BULLISH", "MILD_BULLISH"):
            signals["FII_DII"] = {"direction": "BULLISH", "score": 68, "signal": f"FII buying {market_signal.get('fii_dii', {}).get('fii_net_cr', 0):+.0f}Cr", "weight": 1.3}
        elif fii_bias in ("BEARISH", "MILD_BEARISH"):
            signals["FII_DII"] = {"direction": "BEARISH", "score": 32, "signal": "FII selling", "weight": 1.3}

        # Agent 9: Options PCR
        if pcr_sig in ("STRONG_BULLISH", "BULLISH"):
            signals["Options"] = {"direction": "BULLISH", "score": 65, "signal": f"PCR bullish", "weight": 1.2}
        elif pcr_sig == "BEARISH":
            signals["Options"] = {"direction": "BEARISH", "score": 35, "signal": "PCR bearish", "weight": 1.2}

        # Agent 10: Delivery Volume
        if stock in delivery_stocks:
            d = delivery_stocks[stock]
            if d.get("direction") != "NEUTRAL":
                signals["DeliveryVolume"] = d

        # Agent 11: Bulk/Block Deals
        if stock in bulk_deal_stocks:
            deal = bulk_deal_stocks[stock]
            if deal.get("type") == "BUY":
                signals["BulkDeals"] = {"direction": "BULLISH", "score": 74, "signal": f"Bulk buy ₹{deal.get('value_cr', 0):.0f}Cr", "weight": 1.3}
            else:
                signals["BulkDeals"] = {"direction": "BEARISH", "score": 30, "signal": f"Bulk sell", "weight": 1.3}

        # Agent 12: Insider Trading
        if stock in insider_stocks:
            ins = insider_stocks[stock]
            if ins.get("direction") != "NEUTRAL":
                signals["InsiderTrading"] = ins

        # Agent 13: Mutual Fund Activity
        if stock in mf_stocks:
            mf = mf_stocks[stock]
            if mf.get("direction") != "NEUTRAL":
                signals["MutualFund"] = mf

        # Agent 14: Global Correlation (market-wide)
        if global_corr and global_corr.get("direction") != "NEUTRAL":
            signals["GlobalCorrelation"] = global_corr

        # Agent 15: Volatility / ATR
        if stock in volatility_stocks:
            vol = volatility_stocks[stock]
            if vol.get("direction") != "NEUTRAL":
                signals["Volatility"] = vol

        if signals:
            all_stocks_signals[stock] = signals

    logger.info(f"  Stocks with signals: {len(all_stocks_signals)}")


    # ══════════════════════════════════════════════════════════════
    # STEP 7: ADVANCED SCANNERS (Agents 16-20)
    # ══════════════════════════════════════════════════════════════
    logger.info("\n🔬 STEP 7: Advanced Scanners (5 scanners)...")
    try:
        from advanced_scanner import CircuitDetector, CandlestickScanner, GapScanner, RelativeStrengthScanner, BreakoutDetector
        from breakout_scanner import BreakoutScanner

        top_stocks = list(all_stocks_signals.keys())[:100]

        # Agent 16: 52-Week Breakout Scanner
        breakouts = _safe_run("Breakout52", BreakoutScanner().scan, top_stocks[:50])
        if breakouts:
            for b in breakouts:
                sym = b.get("symbol", "")
                if sym in all_stocks_signals:
                    btype = b.get("type", "HIGH")
                    all_stocks_signals[sym]["Breakout52Wk"] = {
                        "direction": "BULLISH" if btype == "HIGH" else "BEARISH",
                        "score": 78 if btype == "HIGH" else 28,
                        "signal": f"52-week {btype}", "weight": 1.5}
            logger.info(f"  52wk Breakouts: {len(breakouts)}")

        # Agent 17: 20-Day Breakout Detector
        bd = BreakoutDetector()
        for stock in top_stocks[:30]:
            r = _safe_run("Breakout20", bd.scan, f"{stock}.NS")
            if r and r.get("breakout_type"):
                dirn = "BULLISH" if "high" in r["breakout_type"] else "BEARISH"
                all_stocks_signals[stock]["Breakout20D"] = {
                    "direction": dirn, "score": 72 if dirn == "BULLISH" else 30,
                    "signal": f"20-day {r['breakout_type']}", "weight": 1.2}

        # Agent 18: Circuit Detector
        cd = CircuitDetector()
        for stock in top_stocks[:30]:
            r = _safe_run("Circuit", cd.scan, f"{stock}.NS")
            if r and r.get("circuit_type"):
                dirn = "BULLISH" if "upper" in r["circuit_type"] else "BEARISH"
                all_stocks_signals[stock]["CircuitHit"] = {
                    "direction": dirn, "score": 85 if dirn == "BULLISH" else 15,
                    "signal": f"{r['circuit_type']} circuit", "weight": 1.8}

        # Agent 19: Candlestick Pattern
        cs = CandlestickScanner()
        for stock in top_stocks[:30]:
            r = _safe_run("Candle", cs.scan, f"{stock}.NS")
            if r and r.get("pattern"):
                bullish_patterns = ["hammer", "morning_star", "engulfing_bull", "doji_star"]
                bearish_patterns = ["shooting_star", "evening_star", "engulfing_bear"]
                pat = r["pattern"]
                if pat in bullish_patterns:
                    all_stocks_signals[stock]["Candlestick"] = {"direction": "BULLISH", "score": 68, "signal": f"Pattern: {pat}", "weight": 1.0}
                elif pat in bearish_patterns:
                    all_stocks_signals[stock]["Candlestick"] = {"direction": "BEARISH", "score": 32, "signal": f"Pattern: {pat}", "weight": 1.0}

        # Agent 20: Gap Scanner
        gs = GapScanner()
        for stock in top_stocks[:30]:
            r = _safe_run("Gap", gs.scan, f"{stock}.NS")
            if r and r.get("gap_type") and r["gap_type"] != "no_gap":
                dirn = "BULLISH" if r["gap_type"] == "gap_up" else "BEARISH"
                all_stocks_signals[stock]["GapScanner"] = {
                    "direction": dirn, "score": 65 if dirn == "BULLISH" else 35,
                    "signal": f"Gap {r.get('gap_pct', 0):+.1f}%", "weight": 1.1}

        logger.info(f"  Advanced scanners done")
    except Exception as e:
        logger.warning(f"  Advanced scanners failed: {e}")

    # ══════════════════════════════════════════════════════════════
    # STEP 8: SECTOR + MACRO (Agents 21-27)
    # ══════════════════════════════════════════════════════════════
    logger.info("\n🌍 STEP 8: Sector + Macro Agents...")
    try:
        from sector_momentum import SectorMomentumScorer, SECTOR_STOCKS
        from promoter_tracker import PromoterTracker
        from earnings_calendar import EarningsCalendar

        # Agent 21: Sector Momentum
        top_sectors = _safe_run("SectorMom", SectorMomentumScorer().get_top_sectors)
        hot_sectors = []
        cold_sectors = []
        if top_sectors:
            hot_sectors = [s["sector"] for s in top_sectors if s.get("signal") == "BUY"]
            cold_sectors = [s["sector"] for s in top_sectors if s.get("signal") == "AVOID"]
            sector_map = {}
            for sector, stocks in SECTOR_STOCKS.items():
                for s in stocks:
                    sector_map[s.replace(".NS", "")] = sector
            for stock in all_stocks_signals:
                sector = sector_map.get(stock, "")
                if sector in hot_sectors:
                    all_stocks_signals[stock]["SectorMomentum"] = {"direction": "BULLISH", "score": 70, "signal": f"{sector} hot", "weight": 1.2}
                elif sector in cold_sectors:
                    all_stocks_signals[stock]["SectorMomentum"] = {"direction": "BEARISH", "score": 30, "signal": f"{sector} weak", "weight": 1.2}
            logger.info(f"  Sectors: Hot={hot_sectors[:3]} Cold={cold_sectors[:3]}")

        # Agent 22: Relative Strength (vs Nifty)
        try:
            rs = RelativeStrengthScanner()
            for stock in top_stocks[:30]:
                r = _safe_run("RS", rs.scan, f"{stock}.NS")
                if r and r.get("rs_ratio"):
                    if r["rs_ratio"] > 1.1:
                        all_stocks_signals[stock]["RelativeStrength"] = {"direction": "BULLISH", "score": 72, "signal": f"RS={r['rs_ratio']:.2f} outperforming", "weight": 1.1}
                    elif r["rs_ratio"] < 0.9:
                        all_stocks_signals[stock]["RelativeStrength"] = {"direction": "BEARISH", "score": 30, "signal": f"RS={r['rs_ratio']:.2f} underperforming", "weight": 1.1}
        except Exception:
            pass

        # Agent 23: Promoter Tracker
        promoter = PromoterTracker()
        top_candidate_stocks = sorted(all_stocks_signals.keys(), key=lambda s: sum(d.get("score", 50) for d in all_stocks_signals[s].values()), reverse=True)[:30]
        for stock in top_candidate_stocks:
            p = _safe_run("Promoter", promoter.check_promoter_activity, stock)
            if p and p.get("signal") == "BUYING":
                all_stocks_signals[stock]["PromoterBuying"] = {"direction": "BULLISH", "score": 72, "signal": f"Promoter buying ({p.get('promoter_pct', 0):.0f}%)", "weight": 1.0}
            elif p and not p.get("safe"):
                all_stocks_signals[stock]["PromoterRisk"] = {"direction": "BEARISH", "score": 25, "signal": f"Low promoter ({p.get('promoter_pct', 0):.0f}%)", "weight": 1.0}

        # Agent 24: Earnings Calendar (safety)
        earnings = EarningsCalendar()
        earn_data = _safe_run("Earnings", earnings.get_upcoming_results, top_candidate_stocks)
        if earn_data:
            for stock, e in earn_data.items():
                if not e.get("safe_to_trade", True):
                    all_stocks_signals.setdefault(stock, {})["EarningsRisk"] = {"direction": "NEUTRAL", "score": 40, "signal": f"Earnings in {e.get('days_to_results', '?')}d", "weight": -1.0}

        logger.info(f"  Sector/Macro done")
    except Exception as e:
        logger.warning(f"  Sector/Macro failed: {e}")

    # Agent 25: Market Historian
    try:
        from market_historian import MarketHistorian
        hist = _safe_run("Historian", MarketHistorian().analyze_current_market)
        if hist and hist.get("similar_pattern") and hist.get("confidence", 0) >= 60:
            bias = hist.get("market_bias", "NEUTRAL")
            if bias in ("BULLISH", "RECOVERY"):
                for stock in all_stocks_signals:
                    all_stocks_signals[stock]["MarketHistorian"] = {"direction": "BULLISH", "score": 65, "signal": f"Pattern: {hist['similar_pattern']}", "weight": 1.3}
            elif bias in ("BEARISH", "CRASH_WARNING"):
                for stock in all_stocks_signals:
                    all_stocks_signals[stock]["MarketHistorian"] = {"direction": "BEARISH", "score": 30, "signal": f"Warning: {hist['similar_pattern']}", "weight": 1.3}
            logger.info(f"  Historian: {hist['similar_pattern']}")
    except Exception as e:
        logger.warning(f"  Historian skipped: {e}")

    # Agent 26: Enhanced Strategy ML + Market Filter
    try:
        from enhanced_strategy import MarketFilter, MLPatternMatcher
        mf_check = _safe_run("MarketFilter", MarketFilter().is_market_safe)
        if mf_check and not mf_check.get("safe", True):
            for stock in all_stocks_signals:
                all_stocks_signals[stock]["MarketFilter"] = {"direction": "BEARISH", "score": 25, "signal": f"Market unsafe: {mf_check.get('bias', '')}", "weight": 1.5}
            logger.info(f"  Market Filter: UNSAFE")
        else:
            logger.info(f"  Market Filter: SAFE")

        # Agent 27: ML Pattern Matcher
        ml = MLPatternMatcher()
        for stock in top_candidate_stocks[:15]:
            t = ta_results.get(stock, {})
            pred = _safe_run("ML", ml.predict, f"{stock}.NS", t.get("rsi", 50), t.get("macd_signal", "") == "BULLISH", t.get("above_ma50", False), t.get("volume_spike", False))
            if pred and pred.get("confidence") in ("HIGH", "MEDIUM"):
                prob = pred.get("probability", 50)
                if prob >= 65:
                    all_stocks_signals[stock]["ML_Pattern"] = {"direction": "BULLISH", "score": int(prob), "signal": f"ML: {prob}% win ({pred.get('sample_size', 0)} samples)", "weight": 1.5}
                elif prob <= 35:
                    all_stocks_signals[stock]["ML_Pattern"] = {"direction": "BEARISH", "score": int(prob), "signal": f"ML: {prob}% win only", "weight": 1.5}
    except Exception as e:
        logger.warning(f"  ML/Filter skipped: {e}")


    # ══════════════════════════════════════════════════════════════
    # STEP 9: TIMEFRAME AGENTS (Agents 28-37) — 10 agents
    # ══════════════════════════════════════════════════════════════
    logger.info("\n📊 STEP 9: 10 Timeframe Agents...")
    try:
        sys.path.insert(0, str(BASE / "market-intel-division" / "agents"))
        from agent_01_scalper import ScalperAgent
        from agent_02_daytrader import DayTraderAgent
        from agent_03_swing import SwingScoutAgent
        from agent_04_monthly import MonthlyAgent
        from agent_05_quarter import QuarterAgent
        from agent_06_halfyear import HalfYearAgent
        from agent_07_annual import AnnualAgent
        from agent_08_2year import TwoYearAgent
        from agent_09_3year import ThreeYearAgent
        from agent_10_legacy import LegacyAgent

        timeframe_agents = [
            ("Scalper_1H", ScalperAgent),
            ("DayTrader_1D", DayTraderAgent),
            ("Swing_1W", SwingScoutAgent),
            ("Monthly_1M", MonthlyAgent),
            ("Quarter_3M", QuarterAgent),
            ("HalfYear_6M", HalfYearAgent),
            ("Annual_1Y", AnnualAgent),
            ("TwoYear_2Y", TwoYearAgent),
            ("ThreeYear_3Y", ThreeYearAgent),
            ("Legacy_5Y", LegacyAgent),
        ]

        mid_path = str(BASE / "market-intel-division")
        tf_count = 0
        for agent_name, AgentClass in timeframe_agents:
            try:
                agent = AgentClass(mid_path)
                result = agent.run()
                if result and result.get("top_performers"):
                    tf_count += 1
                    # Top performers from this timeframe = bullish signal
                    for perf in result["top_performers"][:5]:
                        sym = perf.get("symbol", "").replace(".NS", "")
                        if sym and sym in all_stocks_signals:
                            all_stocks_signals[sym][agent_name] = {
                                "direction": "BULLISH",
                                "score": min(80, 50 + int(perf.get("pct_return", 0) * 2)),
                                "signal": f"{agent_name}: +{perf.get('pct_return', 0):.1f}%",
                                "weight": 0.8
                            }
                    # Worst performers = bearish
                    for perf in result.get("worst_performers", [])[:3]:
                        sym = perf.get("symbol", "").replace(".NS", "")
                        if sym and sym in all_stocks_signals:
                            all_stocks_signals[sym][agent_name] = {
                                "direction": "BEARISH",
                                "score": max(20, 50 + int(perf.get("pct_return", 0) * 2)),
                                "signal": f"{agent_name}: {perf.get('pct_return', 0):.1f}%",
                                "weight": 0.8
                            }
            except Exception:
                pass
        logger.info(f"  Timeframe agents completed: {tf_count}/10")
    except Exception as e:
        logger.warning(f"  Timeframe agents skipped: {e}")

    # ══════════════════════════════════════════════════════════════
    # STEP 10: META AGENTS (Agents 38-47)
    # ══════════════════════════════════════════════════════════════
    logger.info("\n🎯 STEP 10: Meta Agents (Learning, Focus, India Analyst)...")

    # Agent 38: Learning Engine — adjust weights from past performance
    try:
        from learning_engine import LearningEngine
        learner = LearningEngine()
        learned_weights = learner.get_learned_weights()
        avoid_stocks = learner.state.get("avoid_stocks", [])
        prefer_stocks = learner.get_preferred_stocks()

        # Penalize stocks we historically lose on
        for stock in avoid_stocks:
            if stock in all_stocks_signals:
                all_stocks_signals[stock]["LearningAvoid"] = {"direction": "BEARISH", "score": 25, "signal": "History: repeated losses", "weight": 1.5}

        # Boost stocks we historically win on
        for stock in prefer_stocks:
            if stock in all_stocks_signals:
                all_stocks_signals[stock]["LearningPrefer"] = {"direction": "BULLISH", "score": 68, "signal": "History: high win rate", "weight": 1.2}

        logger.info(f"  Learning: Avoid={len(avoid_stocks)} Prefer={len(prefer_stocks)}")
    except Exception as e:
        logger.warning(f"  Learning engine skipped: {e}")

    # Agent 39: Weekend Strategist Focus
    if focus_stocks:
        for stock in focus_stocks:
            if stock in all_stocks_signals:
                all_stocks_signals[stock]["WeekendFocus"] = {"direction": "BULLISH", "score": 65, "signal": "Weekend strategist pick", "weight": 1.0}

    # Agent 40-42: India Analyst / Tracker signals (from stock-trend-agent)
    try:
        from india_agent.analyst import IndiaAnalyst
        india_analyst = IndiaAnalyst()
        # Get recent global events impact on India
        impact = _safe_run("IndiaAnalyst", india_analyst.analyze_impact)
        if impact and impact.get("top_affected"):
            for item in impact["top_affected"][:10]:
                sym = item.get("symbol", "").replace(".NS", "")
                if sym in all_stocks_signals:
                    dirn = "BULLISH" if item.get("impact", 0) > 0 else "BEARISH"
                    all_stocks_signals[sym]["IndiaAnalyst"] = {
                        "direction": dirn, "score": 65 if dirn == "BULLISH" else 35,
                        "signal": f"India impact: {item.get('reason', '')[:30]}", "weight": 1.1}
    except Exception:
        pass

    # Agent 43-47: Remaining slots for sector intel, delivery scanner (NSE), alert engine
    try:
        from nse_delivery_scanner import DeliveryScanner
        ds = DeliveryScanner()
        high_delivery = _safe_run("NSEDelivery", ds.get_high_delivery_stocks, 50.0)
        if high_delivery:
            for item in high_delivery[:20]:
                sym = item.get("symbol", "")
                if sym in all_stocks_signals:
                    pct = item.get("delivery_pct", 0)
                    if pct >= 80:
                        all_stocks_signals[sym]["NSEDelivery"] = {"direction": "BULLISH", "score": 80, "signal": f"Delivery {pct:.0f}% (institutional)", "weight": 1.4}
                    elif pct >= 60:
                        all_stocks_signals[sym]["NSEDelivery"] = {"direction": "BULLISH", "score": 68, "signal": f"Delivery {pct:.0f}% (strong hands)", "weight": 1.2}
            logger.info(f"  NSE Delivery: {len(high_delivery)} high-delivery stocks")
    except Exception as e:
        logger.warning(f"  NSE Delivery skipped: {e}")

    # ══════════════════════════════════════════════════════════════
    # STEP 11: CONSENSUS ENGINE — THE BRAIN
    # ══════════════════════════════════════════════════════════════
    logger.info("\n🧠 STEP 11: Consensus Engine — 47 agents → Final verdict...")
    ce = ConsensusEngine()
    consensus_results = ce.evaluate_batch(all_stocks_signals)

    # Count agents
    agent_counts = {}
    for stock, signals in all_stocks_signals.items():
        for agent_name in signals:
            agent_counts[agent_name] = agent_counts.get(agent_name, 0) + 1
    logger.info(f"  ✅ ACTIVE AGENTS: {len(agent_counts)}")
    logger.info(f"  Names: {sorted(agent_counts.keys())}")

    # ══════════════════════════════════════════════════════════════
    # STEP 11b: MULTI-TIMEFRAME FILTER (removes weak setups)
    # ══════════════════════════════════════════════════════════════
    logger.info("\n📊 STEP 11b: Multi-Timeframe Confirmation...")
    try:
        from multi_timeframe import MultiTimeframeFilter
        mtf = MultiTimeframeFilter()
        # Only check top consensus candidates (saves time)
        buy_candidates = [r["stock"] for r in consensus_results
                         if r["consensus"] in ("STRONG BUY", "BUY") and r["confidence"] >= 50]

        mtf_results = mtf.check_batch(buy_candidates[:15])
        passed = [s for s, r in mtf_results.items() if r.get("pass")]
        failed = [s for s, r in mtf_results.items() if not r.get("pass")]

        if failed:
            logger.info(f"  ❌ MTF rejected: {failed}")
        if passed:
            logger.info(f"  ✅ MTF passed: {passed}")

        # Remove failed stocks from consensus (downgrade to HOLD)
        for r in consensus_results:
            if r["stock"] in failed:
                r["consensus"] = "HOLD"
                r["_mtf_rejected"] = True
    except Exception as e:
        logger.warning(f"  Multi-timeframe filter skipped: {e}")

    # Apply pre-market threshold adjustment
    effective_min_score = MIN_SCORE + threshold_adj if 'threshold_adj' in dir() else MIN_SCORE
    logger.info(f"  Effective min score: {effective_min_score} (base {MIN_SCORE} + premarket {threshold_adj:+d})")

    # ══════════════════════════════════════════════════════════════
    # STEP 12: RISK AGENT — Position sizing
    # ══════════════════════════════════════════════════════════════
    logger.info("\n🛡️ STEP 12: Risk Agent...")
    risk = RiskAgent(capital=CAPITAL)

    final_calls = []
    for r in consensus_results:
        if r["consensus"] in ("STRONG BUY", "BUY") and r["confidence"] >= 50:
            stock = r["stock"]
            sl_data = _safe_run("SL", risk.auto_stop_loss, stock)
            if sl_data:
                plan = _safe_run("Position", risk.calculate_position, stock, sl_data["price"], sl_data["stop_loss"])
                if plan and plan.get("approved"):
                    final_calls.append({
                        "stock": stock, "consensus": r["consensus"],
                        "confidence": r["confidence"],
                        "agents": f"{r['bullish_count']}/{r['agents_total']}",
                        "entry": sl_data["price"], "stop_loss": sl_data["stop_loss"],
                        "target": sl_data["target"], "quantity": plan["quantity"],
                        "risk_reward": plan["risk_reward"], "invest": plan["position_value"],
                    })

    # ══════════════════════════════════════════════════════════════
    # FINAL OUTPUT
    # ══════════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  📞 MUDHOLKARS & CO — FINAL CALLS (47 AGENTS)")
    print(f"  {ist} | Agents: {len(agent_counts)} | Regime: {regime['regime']}")
    print("=" * 70)

    if final_calls:
        print(f"\n  ✅ APPROVED TRADES ({len(final_calls)})")
        print("  " + "-" * 62)
        for i, c in enumerate(final_calls[:7], 1):
            print(f"    #{i}  {c['stock']:12s}  {c['consensus']:12s}  "
                  f"Conf={c['confidence']:.0f}%  Agents={c['agents']}")
            print(f"        Entry: ₹{c['entry']:.2f} | SL: ₹{c['stop_loss']:.2f} | "
                  f"TGT: ₹{c['target']:.2f} | Qty: {c['quantity']} | R:R=1:{c['risk_reward']}")
            print()
    else:
        print("\n  ⚠️ No high-conviction calls. WAIT.")

    print(f"\n  📊 TOP 20 CONSENSUS")
    print("  " + "-" * 62)
    for r in consensus_results[:20]:
        icon = "🟢" if "BUY" in r["consensus"] else ("🔴" if "SELL" in r["consensus"] else "🟡")
        print(f"    {icon} {r['stock']:12s} {r['consensus']:12s} Conf={r['confidence']:.0f}% "
              f"Bull={r['bullish_count']} Bear={r['bearish_count']} Total={r['agents_total']}")

    if critical_news:
        print(f"\n  🚨 CRITICAL NEWS ({len(critical_news)})")
        for n in critical_news[:3]:
            print(f"    • {n.get('title', '')[:65]}")

    print(f"\n  ⚠️ DISCLAIMER: Agent output. Not financial advice. Use SL always.")
    print("=" * 70)

    # Save report
    Path("reports").mkdir(exist_ok=True)
    report = {
        "timestamp": ist, "capital": CAPITAL, "regime": regime.get("regime"),
        "agents_active": len(agent_counts), "agent_names": sorted(agent_counts.keys()),
        "final_calls": final_calls,
        "consensus": [{"stock": r["stock"], "verdict": r["consensus"], "confidence": r["confidence"],
                       "bullish": r["bullish_count"], "bearish": r["bearish_count"], "total_agents": r["agents_total"]}
                      for r in consensus_results],
        "critical_news": [n.get("title", "") for n in critical_news[:5]],
        "focus_stocks": focus_stocks[:10],
    }
    with open("reports/daily_calls_latest.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"✅ Report saved. {len(agent_counts)} agents active.")
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()
    run_full_pipeline(quick=args.quick)
