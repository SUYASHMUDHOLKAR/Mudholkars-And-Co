"""
social_media_agent.py
---------------------
Global Social Media Sentiment Agent — Mudholkars and Co

Scrapes Reddit (WallStreetBets, r/stocks, r/investing), StockTwits,
Google Trends → sentiment analysis → trending tickers → report.

All FREE. No API keys.

Usage:
  python social_media_agent.py          # continuous (every 30 min)
  python social_media_agent.py --once   # single run
"""

import json
import time
import logging
import argparse
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

from global_scraper import GlobalSocialScraper
from sentiment_analyzer import SentimentAnalyzer
from stock_mention_tracker import StockMentionTracker

def setup_logging(logs_dir="logs"):
    Path(logs_dir).mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[
            logging.FileHandler(Path(logs_dir) / f"social_{date.today()}.log"),
            logging.StreamHandler(),
        ],
    )

logger = logging.getLogger("SocialMediaAgent")


def run_cycle() -> dict:
    logger.info("=" * 60)
    logger.info("GLOBAL SOCIAL MEDIA AGENT — Starting")
    logger.info("=" * 60)

    scraper   = GlobalSocialScraper()
    sentiment = SentimentAnalyzer()
    tracker   = StockMentionTracker(mode="global")

    # 1. Fetch all posts
    data = scraper.fetch_all()
    posts = data.get("posts", [])
    logger.info(f"Fetched {len(posts)} posts total")

    if not posts:
        logger.warning("No posts fetched")
        return {}

    # 2. Aggregate sentiment
    all_texts = [p.get("text", "") for p in posts if p.get("text")]
    overall_sentiment = sentiment.analyze_batch(all_texts)
    logger.info(f"Overall sentiment: {overall_sentiment['label']} (compound={overall_sentiment['compound']:.3f})")

    # 3. Trending tickers
    trending = tracker.get_trending(posts, top_n=15)
    logger.info(f"Trending tickers: {', '.join(t['ticker'] for t in trending[:5])}")

    # 4. Sentiment per ticker
    ticker_sentiment = tracker.get_sentiment_per_ticker(posts, sentiment)

    # 5. Build report
    report = {
        "agent":            "GlobalSocialMediaAgent",
        "company":          "Mudholkars and Co",
        "timestamp":        datetime.utcnow().isoformat() + "Z",
        "generated_ist":    datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %H:%M IST"),
        "posts_analyzed":   len(posts),
        "overall_sentiment": overall_sentiment,
        "trending_tickers": trending,
        "ticker_sentiment": ticker_sentiment,
        "google_trends":    data.get("google_trends", {}),
        "trending_searches": data.get("trending_now", []),
    }

    # Save
    Path("reports").mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"reports/social_{ts}.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    with open("reports/social_latest.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Print summary
    _print_report(report)
    return report


def _print_report(report: dict):
    s = report.get("overall_sentiment", {})
    print("\n" + "=" * 60)
    print("  📱 GLOBAL SOCIAL MEDIA SENTIMENT — Mudholkars and Co")
    print(f"  {report.get('generated_ist', '')}")
    print("=" * 60)
    print(f"\n  Posts Analyzed : {report.get('posts_analyzed', 0)}")
    print(f"  Sentiment     : {s.get('label', 'N/A')} ({s.get('strength', '')}) | Score: {s.get('compound', 0):+.3f}")
    print(f"  Bullish       : {s.get('bullish_pct', 0):.0f}%  |  Bearish: {s.get('bearish_pct', 0):.0f}%  |  Neutral: {100-s.get('bullish_pct',0)-s.get('bearish_pct',0):.0f}%")
    print(f"  Hype Level    : {s.get('hype_pct', 0):.0f}%  |  FUD Level: {s.get('fud_pct', 0):.0f}%")

    print(f"\n  TRENDING TICKERS (Social Media)")
    print("  " + "-" * 40)
    for t in report.get("trending_tickers", [])[:10]:
        print(f"    #{t['rank']:2d}  {t['ticker']:8s} ({t['name']:20s})  mentions: {t['mentions']}")

    # Per-ticker sentiment
    ts = report.get("ticker_sentiment", {})
    if ts:
        print(f"\n  TICKER SENTIMENT")
        print("  " + "-" * 40)
        for ticker, data in list(ts.items())[:8]:
            label = data.get("label", "")
            comp  = data.get("compound", 0)
            mentions = data.get("mentions", 0)
            icon = "▲" if label == "BULLISH" else ("▼" if label == "BEARISH" else "◆")
            print(f"    {icon} {ticker:8s} : {label:8s} ({comp:+.3f})  |  {mentions} mentions | Bull={data.get('bullish_pct',0):.0f}% Bear={data.get('bearish_pct',0):.0f}%")

    # Google Trends
    gt = report.get("google_trends", {})
    if gt:
        print(f"\n  GOOGLE TRENDS (Finance)")
        print("  " + "-" * 40)
        for kw, score in sorted(gt.items(), key=lambda x: x[1], reverse=True):
            bar = "█" * (score // 5)
            print(f"    {kw:30s}: {score:3d} {bar}")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Global Social Media Sentiment Agent")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    setup_logging()
    logger.info("Global Social Media Sentiment Agent — Mudholkars and Co")

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
