"""
sector_analyzer.py
------------------
Analyses one sector deeply — all stocks in that sector.
Produces: sector performance, top/worst stocks, sector momentum,
          breadth (how many stocks are up), rotation signal.
"""

import logging
from datetime import datetime
from typing import Optional

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


class SectorAnalyzer:
    """Analyses all stocks in a single sector."""

    def analyze_sector(self, sector_name: str, stocks: list,
                       period: str = "1mo") -> dict:
        """
        Full sector analysis.
        Returns: sector performance, top/bottom stocks, breadth, momentum.
        """
        results = []
        for ticker in stocks:
            data = self._analyze_stock(f"{ticker}.NS", period)
            if data:
                data["ticker"] = ticker
                results.append(data)

        if not results:
            return {"sector": sector_name, "error": "no_data"}

        # Sector metrics
        returns = [r["pct_return"] for r in results]
        avg_return = sum(returns) / len(returns)
        positive   = sum(1 for r in returns if r > 0)
        negative   = sum(1 for r in returns if r <= 0)
        breadth    = positive / len(returns) * 100  # % of stocks green

        # Sort by return
        results.sort(key=lambda x: x["pct_return"], reverse=True)

        # Sector signal
        if breadth >= 70 and avg_return >= 3:
            signal = "STRONG_BULLISH"
        elif breadth >= 55 and avg_return >= 1:
            signal = "BULLISH"
        elif breadth <= 30 and avg_return <= -3:
            signal = "STRONG_BEARISH"
        elif breadth <= 45 and avg_return <= -1:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        return {
            "sector":          sector_name,
            "period":          period,
            "timestamp":       datetime.utcnow().isoformat() + "Z",
            "stocks_analyzed": len(results),
            "sector_return":   round(avg_return, 2),
            "breadth_pct":     round(breadth, 1),
            "positive_stocks": positive,
            "negative_stocks": negative,
            "sector_signal":   signal,
            "top_performers":  results[:5],
            "worst_performers": results[-5:][::-1],
            "all_stocks":      results,
        }

    def _analyze_stock(self, symbol: str, period: str) -> Optional[dict]:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval="1d")
            if hist.empty or len(hist) < 2:
                return None

            # Drop any rows with NaN close price
            hist = hist.dropna(subset=["Close"])
            if len(hist) < 2:
                return None

            first = float(hist["Close"].iloc[0])
            last  = float(hist["Close"].iloc[-1])
            high  = float(hist["High"].max())
            low   = float(hist["Low"].min())
            vol   = float(hist["Volume"].mean())
            pct   = ((last - first) / first * 100) if first else 0

            return {
                "price":      round(last, 2),
                "pct_return": round(pct, 2),
                "period_high": round(high, 2),
                "period_low":  round(low, 2),
                "avg_volume":  int(vol),
                "near_high":   (high - last) / high * 100 <= 3,
            }
        except:
            return None
