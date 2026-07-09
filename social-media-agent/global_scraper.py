"""
global_scraper.py
-----------------
Scrapes global social/financial media for stock sentiment.
All FREE sources that work without API keys:
  1. Investing.com RSS — financial news with social commentary
  2. SeekingAlpha RSS — market currents, community driven
  3. MarketWatch RSS — market news & opinions  
  4. Google Trends — real-time search trends for stock keywords
  5. CNBC RSS — market sentiment news
"""

import re
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import requests
import feedparser

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}

# Working RSS sources for financial sentiment
FINANCIAL_RSS_SOURCES = [
    {"name": "Investing.com",      "url": "https://www.investing.com/rss/news.rss",                        "priority": "critical"},
    {"name": "SeekingAlpha",       "url": "https://seekingalpha.com/market_currents.xml",                  "priority": "critical"},
    {"name": "MarketWatch Top",    "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",   "priority": "high"},
    {"name": "MarketWatch Markets","url": "https://feeds.content.dowjones.io/public/rss/mw_marketpulse",  "priority": "high"},
    {"name": "CNBC Markets",       "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",        "priority": "high"},
    {"name": "CNBC World",         "url": "https://www.cnbc.com/id/100727362/device/rss/rss.html",        "priority": "medium"},
    {"name": "Bloomberg Markets",  "url": "https://feeds.bloomberg.com/markets/news.rss",                  "priority": "critical"},
    {"name": "FT Markets",         "url": "https://www.ft.com/markets?format=rss",                         "priority": "high"},
    {"name": "NYT Business",       "url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",    "priority": "medium"},
    {"name": "Guardian Business",  "url": "https://www.theguardian.com/business/rss",                      "priority": "medium"},
    {"name": "TechCrunch",         "url": "https://techcrunch.com/feed/",                                  "priority": "medium"},
    {"name": "Ars Technica",       "url": "http://feeds.arstechnica.com/arstechnica/index",               "priority": "low"},
]


class GlobalSocialScraper:
    """Scrapes financial media RSS feeds and Google Trends for stock sentiment."""

    def __init__(self, config: dict = None):
        self.config = config or {}

    # ------------------------------------------------------------------
    # RSS Feed scraping
    # ------------------------------------------------------------------

    def fetch_rss_feeds(self) -> list:
        """Fetch all financial RSS feeds."""
        posts = []
        for source in FINANCIAL_RSS_SOURCES:
            try:
                resp = requests.get(
                    source["url"], headers=HEADERS, timeout=10
                )
                if resp.status_code != 200:
                    logger.warning(f"[{source['name']}] HTTP {resp.status_code}")
                    continue

                feed = feedparser.parse(resp.content)
                count = 0
                for entry in feed.entries[:15]:
                    title   = getattr(entry, "title", "").strip()
                    summary = getattr(entry, "summary", "") or ""
                    summary = re.sub(r"<[^>]+>", "", summary).strip()
                    link    = getattr(entry, "link", "")

                    if not title:
                        continue

                    text = f"{title} {summary}"
                    posts.append({
                        "source":   source["name"],
                        "platform": "rss_financial",
                        "title":    title,
                        "text":     text[:800],
                        "url":      link,
                        "priority": source["priority"],
                        "timestamp": datetime.utcnow().isoformat() + "Z",
                    })
                    count += 1

                logger.info(f"[{source['name']:25s}] {count} posts")
                time.sleep(0.3)

            except Exception as e:
                logger.warning(f"[{source['name']}] Error: {e}")

        return posts

    # ------------------------------------------------------------------
    # Google Trends
    # ------------------------------------------------------------------

    def fetch_google_trends(self, keywords: list = None) -> dict:
        """Get Google Trends scores for finance keywords."""
        if not PYTRENDS_AVAILABLE:
            return {}

        keywords = keywords or [
            "stock market crash", "buy stocks", "sell stocks",
            "market rally", "recession", "inflation"
        ]
        try:
            pytrends = TrendReq(hl="en-US", tz=0)
            results  = {}
            for i in range(0, len(keywords), 5):
                chunk = keywords[i:i+5]
                pytrends.build_payload(chunk, timeframe="now 1-d")
                data = pytrends.interest_over_time()
                if not data.empty:
                    for kw in chunk:
                        if kw in data.columns:
                            results[kw] = int(data[kw].iloc[-1])
                time.sleep(1)
            logger.info(f"Google Trends: {len(results)} keywords")
            return results
        except Exception as e:
            logger.warning(f"Google Trends error: {e}")
            return {}

    # ------------------------------------------------------------------
    # Full fetch
    # ------------------------------------------------------------------

    def fetch_all(self) -> dict:
        """Fetch from all working sources."""
        logger.info("Fetching global financial media...")
        posts  = self.fetch_rss_feeds()
        trends = self.fetch_google_trends()

        logger.info(f"Total: {len(posts)} posts, {len(trends)} trend keywords")
        return {
            "posts":         posts,
            "google_trends": trends,
            "trending_now":  [],
            "fetched_at":    datetime.utcnow().isoformat() + "Z",
        }
