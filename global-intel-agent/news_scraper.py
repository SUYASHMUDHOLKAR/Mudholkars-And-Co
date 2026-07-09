"""
news_scraper.py
---------------
Scrapes RSS feeds from 25 global news sources.
Returns structured article list with title, summary, source, timestamp, URL.
No API keys needed — pure RSS parsing.
"""

import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional

import feedparser
import requests

logger = logging.getLogger(__name__)

# Timeout for each RSS fetch
FETCH_TIMEOUT = 10

# User-agent to avoid blocks
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; MudholkarsIntelBot/1.0; "
        "+https://mudholkars.co/bot)"
    )
}


class NewsScraper:
    """
    Fetches and parses RSS feeds from configured news sources.
    Returns clean, deduplicated article list.
    """

    def __init__(self, config: dict):
        self.sources    = config.get("news_sources", {}).get("rss_feeds", [])
        self.max_age_h  = config.get("reporting", {}).get("max_age_hours", 24)
        self.max_per_src = config.get("reporting", {}).get("max_articles_per_source", 10)
        self._seen_hashes = set()  # deduplication

    # ------------------------------------------------------------------
    # Public: fetch all sources
    # ------------------------------------------------------------------

    def fetch_all(self) -> list:
        """
        Fetch articles from all configured RSS sources.
        Returns list of article dicts, sorted newest first.
        """
        all_articles = []
        self._seen_hashes.clear()

        for source in self.sources:
            articles = self._fetch_source(source)
            all_articles.extend(articles)
            logger.info(
                f"[{source['name']:30s}] fetched {len(articles)} articles"
            )

        # Sort newest first
        all_articles.sort(key=lambda x: x["published_ts"], reverse=True)
        logger.info(f"Total articles fetched: {len(all_articles)}")
        return all_articles

    def fetch_priority(self, priority: str = "critical") -> list:
        """Fetch only sources matching a priority level."""
        all_articles = []
        self._seen_hashes.clear()
        for source in self.sources:
            if source.get("priority") == priority:
                all_articles.extend(self._fetch_source(source))
        all_articles.sort(key=lambda x: x["published_ts"], reverse=True)
        return all_articles

    # ------------------------------------------------------------------
    # Internal: fetch one source
    # ------------------------------------------------------------------

    def _fetch_source(self, source: dict) -> list:
        """Fetch and parse a single RSS feed."""
        url  = source.get("url", "")
        name = source.get("name", "Unknown")
        priority = source.get("priority", "low")

        try:
            # feedparser can handle requests directly but we add timeout via requests
            response = requests.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT)
            response.raise_for_status()
            feed = feedparser.parse(response.content)
        except requests.exceptions.Timeout:
            logger.warning(f"[{name}] Timeout after {FETCH_TIMEOUT}s")
            return []
        except requests.exceptions.RequestException as e:
            logger.warning(f"[{name}] Fetch error: {e}")
            return []
        except Exception as e:
            logger.warning(f"[{name}] Parse error: {e}")
            return []

        articles = []
        cutoff   = datetime.now(timezone.utc) - timedelta(hours=self.max_age_h)

        for entry in feed.entries[: self.max_per_src]:
            article = self._parse_entry(entry, name, priority, cutoff)
            if article:
                articles.append(article)

        return articles

    def _parse_entry(self, entry, source_name: str,
                     priority: str, cutoff: datetime) -> Optional[dict]:
        """Parse a single RSS feed entry into a clean article dict."""
        try:
            title   = getattr(entry, "title", "").strip()
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            summary = summary.strip()
            link    = getattr(entry, "link", "").strip()

            # Clean HTML tags from summary
            summary = self._strip_html(summary)

            # Parse published time
            pub_ts = self._parse_time(entry)
            if not pub_ts:
                pub_ts = datetime.now(timezone.utc)

            # Skip old articles
            if pub_ts < cutoff:
                return None

            if not title:
                return None

            # Deduplicate by title hash
            h = hashlib.md5(title.lower().encode()).hexdigest()
            if h in self._seen_hashes:
                return None
            self._seen_hashes.add(h)

            # Combined text for classification
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
                "published":    pub_ts.strftime("%Y-%m-%d %H:%M UTC"),
                # filled later by classifier
                "category":     None,
                "severity":     None,
                "india_relevant": None,
                "impact":       None,
            }
        except Exception as e:
            logger.debug(f"Entry parse error: {e}")
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_time(self, entry) -> Optional[datetime]:
        """Try multiple date fields on an RSS entry."""
        for attr in ["published_parsed", "updated_parsed", "created_parsed"]:
            val = getattr(entry, attr, None)
            if val:
                try:
                    import time as _time
                    ts = _time.mktime(val)
                    return datetime.fromtimestamp(ts, tz=timezone.utc)
                except Exception:
                    continue
        return None

    def _strip_html(self, text: str) -> str:
        """Remove basic HTML tags from text."""
        import re
        clean = re.compile(r"<[^>]+>")
        return clean.sub("", text).strip()
