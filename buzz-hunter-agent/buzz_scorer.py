"""
buzz_scorer.py
--------------
Takes raw buzz data from buzz_scanner.py and computes a single
Buzz Score (0-100) for each stock detected.

Scoring formula:
  News Mentions    : max 30 points (more mentions = more buzz)
  Volume Spike     : max 25 points (higher ratio = hotter)
  Price Momentum   : max 20 points (bigger move = more attention)
  Google Interest  : max 15 points (search spike = crowd FOMO)
  Multi-Signal     : +10 bonus if 3+ signals fire together

Final: 90-100 = 🔥 ACT NOW | 70-89 = STRONG BUZZ | 50-69 = BUILDING | <50 = EARLY
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BuzzScorer:
    """Computes Buzz Score (0-100) for each stock from raw scan data."""

    def score_all(self, scan_data: dict) -> list:
        """
        Takes output from BuzzScanner.scan_all() and returns
        a ranked list of stocks with buzz scores.
        """
        news_mentions  = scan_data.get("news_mentions", {})
        volume_spikes  = scan_data.get("volume_spikes", [])
        price_data     = scan_data.get("price_momentum", {})
        google_buzz    = scan_data.get("google_search", {})

        gainers = price_data.get("top_gainers", [])
        losers  = price_data.get("top_losers", [])

        # Collect all tickers that appear anywhere
        all_tickers = set()
        all_tickers.update(news_mentions.keys())
        all_tickers.update(v["ticker"] for v in volume_spikes)
        all_tickers.update(g["ticker"] for g in gainers)
        all_tickers.update(l["ticker"] for l in losers)

        # Build per-ticker data
        volume_map = {v["ticker"]: v for v in volume_spikes}
        price_map  = {g["ticker"]: g for g in gainers + losers}
        google_map = {}
        for kw, score in google_buzz.items():
            # Extract ticker from keyword like "Suzlon share" → SUZLON
            word = kw.split()[0].upper()
            if word in all_tickers or any(word in t for t in all_tickers):
                google_map[word] = score

        # Score each ticker
        scored = []
        for ticker in all_tickers:
            score_breakdown = self._compute_score(
                ticker, news_mentions, volume_map, price_map, google_map
            )
            if score_breakdown["total"] >= 15:  # only include meaningful buzz
                scored.append(score_breakdown)

        # Sort by total score descending
        scored.sort(key=lambda x: x["total"], reverse=True)

        # Assign labels
        for item in scored:
            s = item["total"]
            if s >= 90:
                item["label"]    = "🔥 ACT NOW"
                item["priority"] = "CRITICAL"
            elif s >= 70:
                item["label"]    = "🔥 STRONG BUZZ"
                item["priority"] = "HIGH"
            elif s >= 50:
                item["label"]    = "📈 BUILDING"
                item["priority"] = "MEDIUM"
            else:
                item["label"]    = "👀 EARLY SIGNAL"
                item["priority"] = "LOW"

        logger.info(f"Scored {len(scored)} stocks with buzz")
        return scored

    def _compute_score(self, ticker: str, news: dict, volume: dict,
                       price: dict, google: dict) -> dict:
        """Compute individual scores per signal type."""
        signals = 0

        # 1. News Mentions (max 30 pts)
        mentions = news.get(ticker, 0)
        news_score = min(30, mentions * 6)  # 5 mentions = 30 pts
        if mentions > 0:
            signals += 1

        # 2. Volume Spike (max 25 pts)
        vol_data   = volume.get(ticker, {})
        vol_ratio  = vol_data.get("volume_ratio", 0) if vol_data else 0
        vol_score  = 0
        if vol_ratio >= 5:
            vol_score = 25
        elif vol_ratio >= 3:
            vol_score = 20
        elif vol_ratio >= 2:
            vol_score = 15
        if vol_ratio >= 2:
            signals += 1

        # 3. Price Momentum (max 20 pts)
        p_data    = price.get(ticker, {})
        pct_chg   = abs(p_data.get("pct_change", 0)) if p_data else 0
        price_score = 0
        if pct_chg >= 5:
            price_score = 20
        elif pct_chg >= 3:
            price_score = 15
        elif pct_chg >= 1.5:
            price_score = 10
        if pct_chg >= 1.5:
            signals += 1

        # 4. Google Interest (max 15 pts)
        g_score = google.get(ticker, 0)
        google_score = 0
        if g_score >= 75:
            google_score = 15
        elif g_score >= 50:
            google_score = 10
        elif g_score >= 25:
            google_score = 5
        if g_score >= 25:
            signals += 1

        # 5. Multi-signal bonus (+10 if 3+ signals)
        bonus = 10 if signals >= 3 else (5 if signals >= 2 else 0)

        total = min(100, news_score + vol_score + price_score + google_score + bonus)

        return {
            "ticker":        ticker,
            "total":         total,
            "signals_fired": signals,
            "breakdown": {
                "news_mentions":   news_score,
                "volume_spike":    vol_score,
                "price_momentum":  price_score,
                "google_interest": google_score,
                "multi_bonus":     bonus,
            },
            "raw": {
                "mentions":     mentions,
                "volume_ratio": vol_ratio,
                "pct_change":   p_data.get("pct_change", 0) if p_data else 0,
                "price":        p_data.get("price", 0) if p_data else 0,
                "google_score": g_score,
            },
            "label":    "",
            "priority": "",
        }
