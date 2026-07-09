"""
event_classifier.py
-------------------
Classifies news articles into one of 25 event categories.
Assigns severity (CRITICAL / HIGH / MEDIUM / LOW).
Flags articles relevant to Indian markets.
Uses keyword matching — no external NLP dependency needed.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EventClassifier:
    """
    Classifies each article into one of 25 categories,
    assigns severity level, and flags India-relevant stories.
    """

    def __init__(self, config: dict):
        self.categories          = config.get("categories", {})
        self.severity_keywords   = config.get("severity_keywords", {})
        self.india_keywords      = config.get("india_relevance_keywords", [])

    # ------------------------------------------------------------------
    # Classify a single article
    # ------------------------------------------------------------------

    def classify(self, article: dict) -> dict:
        """
        Classify one article. Mutates and returns the article dict with:
          - category       : category name (e.g. ENERGY_COMMODITIES)
          - category_id    : int 1-25
          - severity       : CRITICAL / HIGH / MEDIUM / LOW
          - india_relevant : True / False
          - confidence     : keyword match score
        """
        text = article.get("full_text", "").lower()

        category, confidence = self._match_category(text)
        severity             = self._assess_severity(text, category)
        india_relevant       = self._is_india_relevant(text)

        article["category"]      = category
        article["category_id"]   = self.categories.get(category, {}).get("id", 0)
        article["severity"]      = severity
        article["india_relevant"]= india_relevant
        article["confidence"]    = confidence

        return article

    def classify_all(self, articles: list) -> list:
        """Classify a list of articles."""
        classified = []
        for article in articles:
            try:
                classified.append(self.classify(article))
            except Exception as e:
                logger.debug(f"Classify error on '{article.get('title','')}': {e}")
        logger.info(f"Classified {len(classified)} articles into 25 categories")
        return classified

    # ------------------------------------------------------------------
    # Category matching
    # ------------------------------------------------------------------

    def _match_category(self, text: str) -> tuple:
        """
        Score each category by keyword hits.
        Returns (best_category_name, confidence_score).
        """
        scores = {}

        for cat_name, cat_data in self.categories.items():
            keywords = cat_data.get("keywords", [])
            boost    = cat_data.get("severity_boost", 1.0)
            hits = sum(1 for kw in keywords if kw in text)
            if hits > 0:
                scores[cat_name] = hits * boost

        if not scores:
            return ("GEOPOLITICAL", 0)  # default fallback

        best = max(scores, key=scores.get)
        return (best, round(scores[best], 2))

    # ------------------------------------------------------------------
    # Severity assessment
    # ------------------------------------------------------------------

    def _assess_severity(self, text: str, category: str) -> str:
        """
        Determine severity from keyword presence.
        Category boost applied for market-critical categories.
        """
        # Count hits per severity tier
        hits = {tier: 0 for tier in self.severity_keywords}
        for tier, keywords in self.severity_keywords.items():
            hits[tier] = sum(1 for kw in keywords if kw in text)

        # Base severity from keyword hits
        if hits.get("CRITICAL", 0) >= 1:
            base = "CRITICAL"
        elif hits.get("HIGH", 0) >= 2:
            base = "HIGH"
        elif hits.get("HIGH", 0) >= 1:
            base = "MEDIUM"
        elif hits.get("MEDIUM", 0) >= 2:
            base = "MEDIUM"
        else:
            base = "LOW"

        # Boost severity for market-critical categories
        market_rel = self.categories.get(category, {}).get("market_relevance", "LOW")
        if market_rel == "CRITICAL" and base == "MEDIUM":
            base = "HIGH"
        elif market_rel == "CRITICAL" and base == "LOW":
            base = "MEDIUM"

        return base

    # ------------------------------------------------------------------
    # India relevance
    # ------------------------------------------------------------------

    def _is_india_relevant(self, text: str) -> bool:
        """Check if article is directly relevant to Indian markets."""
        return any(kw in text for kw in self.india_keywords)

    # ------------------------------------------------------------------
    # Summary stats
    # ------------------------------------------------------------------

    def get_stats(self, articles: list) -> dict:
        """Return classification summary statistics."""
        from collections import Counter
        cats      = Counter(a.get("category") for a in articles)
        sevs      = Counter(a.get("severity") for a in articles)
        india_cnt = sum(1 for a in articles if a.get("india_relevant"))

        return {
            "total":          len(articles),
            "india_relevant": india_cnt,
            "by_category":    dict(cats.most_common()),
            "by_severity": {
                "CRITICAL": sevs.get("CRITICAL", 0),
                "HIGH":     sevs.get("HIGH", 0),
                "MEDIUM":   sevs.get("MEDIUM", 0),
                "LOW":      sevs.get("LOW", 0),
            },
        }
