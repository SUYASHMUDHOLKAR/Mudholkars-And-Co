"""
sentiment_analyzer.py
---------------------
Shared sentiment analysis module using VADER (free, local, no API key).
VADER = Valence Aware Dictionary and sEntiment Reasoner.
Works perfectly on short social media text (Reddit posts, comments, tweets).

Sentiment scores:
  compound >= +0.05  → BULLISH
  compound <= -0.05  → BEARISH
  between            → NEUTRAL

Also detects: hype words, FUD words, stock-specific signals.
"""

import re
import logging
from typing import Optional

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Finance-specific word boosters
# Added on top of VADER's default lexicon
# -----------------------------------------------------------------------

BULLISH_WORDS = [
    "moon", "mooning", "bullish", "buy", "buying", "long", "calls",
    "breakout", "surge", "rally", "pump", "undervalued", "strong buy",
    "all time high", "ath", "going up", "rocket", "squeeze", "yolo",
    "accumulate", "hold", "hodl", "uptrend", "green", "gains",
    "beat estimates", "outperform", "upgrade", "dividend", "buyback",
    "strong results", "record profit", "order win", "deal win",
]

BEARISH_WORDS = [
    "crash", "dump", "bearish", "sell", "selling", "short", "puts",
    "overvalued", "bubble", "collapse", "fraud", "scam", "ponzi",
    "going down", "falling", "tank", "red", "loss", "miss estimates",
    "downgrade", "warning", "recall", "ban", "investigation", "probe",
    "bankruptcy", "default", "npa", "bad loans", "debt trap",
]

HYPE_WORDS = [
    "moon", "rocket", "yolo", "squeeze", "pump", "ath", "100x", "10x",
    "lambo", "diamond hands", "to the moon", "printing money",
]

FUD_WORDS = [
    "crash", "collapse", "bubble", "scam", "fraud", "ponzi", "dump",
    "manipulation", "fake", "worthless", "bankrupt", "dead",
]


class SentimentAnalyzer:
    """
    Analyses sentiment of social media text using VADER.
    Finance-tuned with custom bullish/bearish word weights.
    """

    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
        # Boost finance-specific words in VADER lexicon
        for word in BULLISH_WORDS:
            self.vader.lexicon[word] = 2.5
        for word in BEARISH_WORDS:
            self.vader.lexicon[word] = -2.5

    def analyze(self, text: str) -> dict:
        """
        Analyze sentiment of a single text.
        Returns: compound, label, pos, neg, neu, hype, fud flags.
        """
        if not text or not text.strip():
            return self._empty()

        clean = self._clean(text)
        scores = self.vader.polarity_scores(clean)
        compound = scores["compound"]

        if compound >= 0.05:
            label = "BULLISH"
        elif compound <= -0.05:
            label = "BEARISH"
        else:
            label = "NEUTRAL"

        text_lower = clean.lower()
        hype = any(w in text_lower for w in HYPE_WORDS)
        fud  = any(w in text_lower for w in FUD_WORDS)

        return {
            "compound":  round(compound, 4),
            "label":     label,
            "positive":  round(scores["pos"], 3),
            "negative":  round(scores["neg"], 3),
            "neutral":   round(scores["neu"], 3),
            "is_hype":   hype,
            "is_fud":    fud,
        }

    def analyze_batch(self, texts: list) -> dict:
        """
        Analyze a list of texts and return aggregate sentiment.
        Returns: avg compound, label, bull/bear/neutral counts, hype %, fud %.
        """
        if not texts:
            return {"label": "NEUTRAL", "compound": 0, "total": 0}

        results = [self.analyze(t) for t in texts if t]
        if not results:
            return {"label": "NEUTRAL", "compound": 0, "total": 0}

        compounds  = [r["compound"] for r in results]
        avg        = sum(compounds) / len(compounds)
        bull_count = sum(1 for r in results if r["label"] == "BULLISH")
        bear_count = sum(1 for r in results if r["label"] == "BEARISH")
        neut_count = sum(1 for r in results if r["label"] == "NEUTRAL")
        hype_count = sum(1 for r in results if r["is_hype"])
        fud_count  = sum(1 for r in results if r["is_fud"])
        total      = len(results)

        if avg >= 0.05:
            label = "BULLISH"
        elif avg <= -0.05:
            label = "BEARISH"
        else:
            label = "NEUTRAL"

        # Strength
        abs_avg = abs(avg)
        if abs_avg >= 0.5:
            strength = "STRONG"
        elif abs_avg >= 0.2:
            strength = "MODERATE"
        else:
            strength = "WEAK"

        return {
            "compound":      round(avg, 4),
            "label":         label,
            "strength":      strength,
            "total":         total,
            "bullish_count": bull_count,
            "bearish_count": bear_count,
            "neutral_count": neut_count,
            "bullish_pct":   round(bull_count / total * 100, 1),
            "bearish_pct":   round(bear_count / total * 100, 1),
            "hype_pct":      round(hype_count / total * 100, 1),
            "fud_pct":       round(fud_count  / total * 100, 1),
        }

    def _clean(self, text: str) -> str:
        """Remove URLs, special chars for cleaner analysis."""
        text = re.sub(r"http\S+", "", text)
        text = re.sub(r"[^\w\s$#@%.,!?'-]", " ", text)
        return text.strip()

    def _empty(self) -> dict:
        return {
            "compound": 0, "label": "NEUTRAL",
            "positive": 0, "negative": 0, "neutral": 1,
            "is_hype": False, "is_fud": False,
        }
