"""
india_scraper.py
----------------
Scrapes India-focused financial media for NSE/BSE stock sentiment.
Sources (all FREE, working, no API key):
  1. Economic Times Markets & Industry RSS
  2. Mint Markets & Companies RSS
  3. NDTV Profit RSS
  4. Investing.com India RSS
  5. The Hindu Business RSS
  6. India Today Business RSS
  7. Google Trends India — pytrends geo=IN
"""

import re
import logging
import time
from datetime import datetime, timezone
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

# India financial RSS sources that work
INDIA_RSS_SOURCES = [
    {"name": "ET Markets",        "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",   "priority": "critical"},
    {"name": "ET Industry",       "url": "https://economictimes.indiatimes.com/industry/rssfeeds/13352306.cms",    "priority": "high"},
    {"name": "ET Stocks",         "url": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms","priority": "critical"},
    {"name": "Mint Markets",      "url": "https://www.livemint.com/rss/markets",                                   "priority": "critical"},
    {"name": "Mint Companies",    "url": "https://www.livemint.com/rss/companies",                                 "priority": "high"},
    {"name": "NDTV Profit",       "url": "https://feeds.feedburner.com/ndtvprofit-latest",                         "priority": "high"},
    {"name": "Investing.com India","url": "https://in.investing.com/rss/news_25.rss",                              "priority": "high"},
    {"name": "The Hindu Business","url": "https://www.thehindu.com/business/feeder/default.rss",                   "priority": "medium"},
    {"name": "India Today Biz",   "url": "https://www.indiatoday.in/rss/1206578",                                  "priority": "medium"},
]

INDIA_TREND_KEYWORDS = [
    "Nifty 50", "Sensex today", "Indian stock market",
    "NSE shares", "Zerodha", "mutual funds India",
]


class IndiaSocialScraper:
    """Scrapes India financial media RSS for NSE/BSE stock sentiment."""

    def __init__(self, config: dict = None):
        self.config = config or {}

    def fetch_rss_feeds(self) -> list:
        """Fetch all Indian financial RSS feeds."""
        posts = []
        for source in INDIA_RSS_SOURCES:
            try:
                resp = requests.get(source["url"], headers=HEADERS, timeout=10)
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
                        "platform": "rss_india_finance",
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

    def fetch_google_trends_india(self) -> dict:
        """Google Trends for Indian stock keywords."""
        if not PYTRENDS_AVAILABLE:
            return {}
        try:
            pytrends = TrendReq(hl="en-IN", tz=330)
            results  = {}
            pytrends.build_payload(INDIA_TREND_KEYWORDS[:5], geo="IN", timeframe="now 1-d")
            data = pytrends.interest_over_time()
            if not data.empty:
                for kw in INDIA_TREND_KEYWORDS[:5]:
                    if kw in data.columns:
                        results[kw] = int(data[kw].iloc[-1])
            logger.info(f"Google Trends India: {len(results)} keywords")
            return results
        except Exception as e:
            logger.warning(f"Google Trends India error: {e}")
            return {}

    def fetch_all(self) -> dict:
        """Fetch from all India sources."""
        logger.info("Fetching India financial media...")
        posts  = self.fetch_rss_feeds()
        trends = self.fetch_google_trends_india()
        logger.info(f"India total: {len(posts)} posts")
        return {
            "posts":         posts,
            "google_trends": trends,
            "trending_now":  [],
            "fetched_at":    datetime.utcnow().isoformat() + "Z",
        }
