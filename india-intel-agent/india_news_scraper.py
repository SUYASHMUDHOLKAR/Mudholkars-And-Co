"""
india_news_scraper.py
---------------------
Scrapes 25 India-focused RSS news sources.
Sources: Economic Times, Mint, MoneyControl, NDTV Profit,
         RBI, SEBI, BSE, PIB, Reuters India, Bloomberg India etc.
"""

import logging
import hashlib
import re
import time as _time
from datetime import datetime, timezone, timedelta
from typing import Optional

import feedparser
import requests

logger = logging.getLogger(__name__)

FETCH_TIMEOUT = 10
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; MudholkarsIndiaIntelBot/1.0)"
    )
}


class IndiaNewsScraper:
    """Fetches and parses RSS feeds from 25 Indian news sources."""

    def __init__(self, config: dict):
        self.sources     = config.get("news_sources", {}).get("rss_feeds", [])
        self.max_age_h   = config.get("reporting", {}).get("max_age_hours", 12)
        self.max_per_src = config.get("reporting", {}).get("max_articles_per_source", 10)
        self._seen       = set()

    def fetch_all(self) -> list:
        """Fetch all sources, return deduplicated article list newest-first."""
        all_articles = []
        self._seen.clear()
        for source in self.sources:
            arts = self._fetch_source(source)
            all_articles.extend(arts)
            logger.info(f"[{source['name']:35s}] {len(arts)} articles")
        all_articles.sort(key=lambda x: x["published_ts"], reverse=True)
        logger.info(f"Total India articles: {len(all_articles)}")
        return all_articles

    def _fetch_source(self, source: dict) -> list:
        url      = source.get("url", "")
        name     = source.get("name", "")
        priority = source.get("priority", "medium")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except requests.exceptions.Timeout:
            logger.warning(f"[{name}] Timeout")
            return []
        except requests.exceptions.RequestException as e:
            logger.warning(f"[{name}] Error: {e}")
            return []
        except Exception as e:
            logger.warning(f"[{name}] Parse error: {e}")
            return []

        cutoff   = datetime.now(timezone.utc) - timedelta(hours=self.max_age_h)
        articles = []
        for entry in feed.entries[: self.max_per_src]:
            art = self._parse_entry(entry, name, priority, cutoff)
            if art:
                articles.append(art)
        return articles

    def _parse_entry(self, entry, source_name: str,
                     priority: str, cutoff: datetime) -> Optional[dict]:
        try:
            title   = getattr(entry, "title", "").strip()
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            summary = self._clean(summary)
            link    = getattr(entry, "link", "").strip()

            pub_ts  = self._parse_time(entry) or datetime.now(timezone.utc)
            if pub_ts < cutoff or not title:
                return None

            h = hashlib.md5(title.lower().encode()).hexdigest()
            if h in self._seen:
                return None
            self._seen.add(h)

            full_text = f"{title} {summary}".lower()
            return {
                "id":           h,
                "title":        title,
                "summary":      summary[:500],
                "full_text":    full_text,
                "source":       source_name,
                "priority":     priority,
                "url":          link,
                "published_ts": pub_ts,
                "published":    pub_ts.strftime("%Y-%m-%d %H:%M IST"),
                "category":     None,
                "severity":     None,
                "impact_score": None,
                "direction":    None,
            }
        except Exception as e:
            logger.debug(f"Entry error: {e}")
            return None

    def _parse_time(self, entry) -> Optional[datetime]:
        for attr in ["published_parsed", "updated_parsed"]:
            val = getattr(entry, attr, None)
            if val:
                try:
                    return datetime.fromtimestamp(_time.mktime(val), tz=timezone.utc)
                except:
                    continue
        return None

    def _clean(self, text: str) -> str:
        return re.sub(r"<[^>]+>", "", text).strip()
