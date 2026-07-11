import os
"""
india_social_agent.py
---------------------
India Social Media Sentiment Agent — Mudholkars and Co

Scrapes Reddit (r/IndiaInvestments, r/DalalStreetBets, r/IndianStockMarket),
StockTwits India tickers, Google Trends India → NSE stock sentiment.

All FREE. No API keys.

Usage:
  python india_social_agent.py          # continuous (every 30 min)
  python india_social_agent.py --once   # single run
"""

import json
import time
import logging
import argparse
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

from india_scraper import IndiaSocialScraper
from sentiment_analyzer import SentimentAnalyzer
from stock_mention_tracker import StockMentionTracker

def setup_logging(logs_dir="logs"):
    Path(logs_dir).mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[
            logging.FileHandler(Path(logs_dir) / f"india_social_{date.today()}.log"),
            logging.StreamHandler(),
        ],
    )

logger = logging.getLogger("IndiaSocialAgent")


def run_cycle() -> dict:
    logger.info("=" * 60)
    logger.info("🇮🇳 INDIA SOCIAL MEDIA AGENT — Starting")
    logger.info("=" * 60)

    scraper   = IndiaSocialScraper()
    sentiment = SentimentAnalyzer()
    tracker   = StockMentionTracker(mode="india")

    # 1. Fetch
    data  = scraper.fetch_all()
    posts = data.get("posts", [])
    logger.info(f"Fetched {len(posts)} India posts")

    if not posts:
        logger.warning("No posts fetched")
        return {}

    # 2. Aggregate sentiment
    all_texts = [p.get("text", "") for p in posts if p.get("text")]
    overall   = sentiment.analyze_batch(all_texts)
    logger.info(f"India sentiment: {overall['label']} ({overall['compound']:+.3f})")

    # 3. Trending NSE tickers
    trending = tracker.get_trending(posts, top_n=15)
    logger.info(f"Trending India tickers: {', '.join(t['ticker'] for t in trending[:5])}")

    # 4. Per-ticker sentiment
    ticker_sentiment = tracker.get_sentiment_per_ticker(posts, sentiment)

    # 5. Report
    report = {
        "agent":            "IndiaSocialMediaAgent",
        "company":          "Mudholkars and Co",
        "timestamp":        datetime.utcnow().isoformat() + "Z",
        "generated_ist":    datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %H:%M IST"),
        "posts_analyzed":   len(posts),
        "overall_sentiment": overall,
        "trending_tickers": trending,
        "ticker_sentiment": ticker_sentiment,
        "google_trends":    data.get("google_trends", {}),
        "trending_searches": data.get("trending_now", []),
    }

    # Save
    Path("reports").mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"reports/india_social_{ts}.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    with open("reports/india_social_latest.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    _print_report(report)
    return report


def _print_report(report: dict):
    s = report.get("overall_sentiment", {})
    print("\n" + "=" * 60)
    print("  🇮🇳 INDIA SOCIAL MEDIA SENTIMENT — Mudholkars and Co")
    print(f"  {report.get('generated_ist', '')}")
    print("=" * 60)
    print(f"\n  Posts Analyzed : {report.get('posts_analyzed', 0)}")
    print(f"  Sentiment     : {s.get('label', 'N/A')} ({s.get('strength', '')}) | Score: {s.get('compound', 0):+.3f}")
    print(f"  Bullish       : {s.get('bullish_pct', 0):.0f}%  |  Bearish: {s.get('bearish_pct', 0):.0f}%")
    print(f"  Hype Level    : {s.get('hype_pct', 0):.0f}%  |  FUD Level: {s.get('fud_pct', 0):.0f}%")

    print(f"\n  TRENDING NSE TICKERS (Social Media Buzz)")
    print("  " + "-" * 45)
    for t in report.get("trending_tickers", [])[:10]:
        print(f"    #{t['rank']:2d}  {t['ticker']:12s} ({t['name']:20s})  mentions: {t['mentions']}")

    ts = report.get("ticker_sentiment", {})
    if ts:
        print(f"\n  NSE TICKER SENTIMENT")
        print("  " + "-" * 45)
        for ticker, data in list(ts.items())[:10]:
            label = data.get("label", "")
            comp  = data.get("compound", 0)
            mentions = data.get("mentions", 0)
            icon = "▲" if label == "BULLISH" else ("▼" if label == "BEARISH" else "◆")
            print(f"    {icon} {ticker:12s}: {label:8s} ({comp:+.3f}) | {mentions} mentions | Bull={data.get('bullish_pct',0):.0f}%")

    gt = report.get("google_trends", {})
    if gt:
        print(f"\n  GOOGLE TRENDS INDIA (Finance)")
        print("  " + "-" * 45)
        for kw, score in sorted(gt.items(), key=lambda x: x[1], reverse=True):
            bar = "█" * (score // 5)
            print(f"    {kw:30s}: {score:3d} {bar}")

    tn = report.get("trending_searches", [])
    if tn:
        print(f"\n  TRENDING SEARCHES IN INDIA")
        print("  " + "-" * 45)
        for i, topic in enumerate(tn[:10], 1):
            print(f"    {i:2d}. {topic}")

    print("\n" + "=" * 60)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(description="India Social Media Sentiment Agent")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    setup_logging()
    logger.info("India Social Media Sentiment Agent — Mudholkars and Co")

    if args.once:
        run_cycle()
    else:
        logger.info("Running every 30 minutes. Ctrl+C to stop.")
        while True:
            try:
                run_cycle()
            except Exception as e:
                logger.error(f"Cycle error: {e}")
            time.sleep(30 * 60)


if __name__ == "__main__":
    main()
