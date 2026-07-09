"""
timeframe_analyzer.py
---------------------
Shared analysis engine for all 10 timeframe agents.
Each agent just calls this with a different period parameter.
Computes: returns, CAGR, rank, momentum, breakouts for ANY timeframe.
"""

import logging
from datetime import datetime
from typing import Optional

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


class TimeframeAnalyzer:
    """
    Analyses stocks over any timeframe.
    Used by all 10 MID agents with different period parameters.
    """

    def analyze_stock(self, symbol: str, period: str = "1y",
                      interval: str = "1d") -> Optional[dict]:
        """
        Analyze a single stock over a given period.
        period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 3y, 5y, 10y, max
        interval: 1m, 5m, 15m, 1h, 1d, 1wk, 1mo

        Returns comprehensive analysis dict.
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)

            if df.empty or len(df) < 2:
                return None

            close = df["Close"]
            volume = df["Volume"]
            high = df["High"]
            low = df["Low"]

            first_price = float(close.iloc[0])
            last_price  = float(close.iloc[-1])
            period_high = float(high.max())
            period_low  = float(low.min())
            avg_volume  = float(volume.mean())
            latest_vol  = float(volume.iloc[-1])

            # Returns
            abs_return    = last_price - first_price
            pct_return    = ((last_price - first_price) / first_price) * 100
            from_high_pct = ((last_price - period_high) / period_high) * 100
            from_low_pct  = ((last_price - period_low) / period_low) * 100

            # CAGR (if period > 1 year)
            days = (df.index[-1] - df.index[0]).days
            years = days / 365.25
            cagr = None
            if years >= 1 and first_price > 0:
                cagr = ((last_price / first_price) ** (1 / years) - 1) * 100

            # Volatility
            daily_returns = close.pct_change().dropna()
            volatility = float(daily_returns.std() * 100)

            # Momentum (% change in recent portion)
            recent_n = max(int(len(close) * 0.2), 2)
            recent_start = float(close.iloc[-recent_n])
            recent_momentum = ((last_price - recent_start) / recent_start * 100) if recent_start else 0

            # Near high/low detection
            near_period_high = (period_high - last_price) / period_high * 100 <= 3
            near_period_low  = (last_price - period_low) / period_low * 100 <= 3

            # Volume trend
            vol_first_half = float(volume.iloc[:len(volume)//2].mean())
            vol_second_half = float(volume.iloc[len(volume)//2:].mean())
            volume_trend = "INCREASING" if vol_second_half > vol_first_half * 1.2 else (
                "DECREASING" if vol_second_half < vol_first_half * 0.8 else "STABLE"
            )

            # Consistency (% of periods with positive returns)
            if interval in ("1wk", "1mo"):
                period_returns = close.pct_change().dropna()
            else:
                period_returns = close.resample("W").last().pct_change().dropna()
            positive_weeks = float((period_returns > 0).sum())
            total_weeks    = float(len(period_returns))
            consistency    = (positive_weeks / total_weeks * 100) if total_weeks else 0

            return {
                "symbol":           symbol,
                "period":           period,
                "first_price":      round(first_price, 2),
                "last_price":       round(last_price, 2),
                "period_high":      round(period_high, 2),
                "period_low":       round(period_low, 2),
                "pct_return":       round(pct_return, 2),
                "abs_return":       round(abs_return, 2),
                "cagr":             round(cagr, 2) if cagr else None,
                "volatility":       round(volatility, 3),
                "recent_momentum":  round(recent_momentum, 2),
                "near_period_high": near_period_high,
                "near_period_low":  near_period_low,
                "from_high_pct":    round(from_high_pct, 2),
                "from_low_pct":     round(from_low_pct, 2),
                "avg_volume":       int(avg_volume),
                "volume_trend":     volume_trend,
                "consistency_pct":  round(consistency, 1),
                "data_points":      len(df),
                "days_analyzed":    days,
            }
        except Exception as e:
            logger.debug(f"[{symbol}] Analysis error: {e}")
            return None

    def analyze_batch(self, symbols: list, period: str = "1y",
                      interval: str = "1d", max_stocks: int = 500) -> list:
        """
        Analyze multiple stocks and return ranked results.
        Processes up to max_stocks for performance.
        """
        results = []
        symbols = symbols[:max_stocks]
        total   = len(symbols)

        for i, symbol in enumerate(symbols):
            if i % 50 == 0 and i > 0:
                logger.info(f"  Progress: {i}/{total} stocks analyzed...")

            data = self.analyze_stock(symbol, period=period, interval=interval)
            if data:
                results.append(data)

        # Rank by return
        results.sort(key=lambda x: x["pct_return"], reverse=True)
        for rank, item in enumerate(results, 1):
            item["rank"] = rank

        logger.info(f"Analyzed {len(results)}/{total} stocks for period={period}")
        return results

    def get_top_performers(self, results: list, n: int = 20) -> list:
        """Top N stocks by % return."""
        return results[:n]

    def get_worst_performers(self, results: list, n: int = 20) -> list:
        """Bottom N stocks by % return."""
        return results[-n:][::-1]

    def get_near_highs(self, results: list) -> list:
        """Stocks near their period high (within 3%)."""
        return [r for r in results if r.get("near_period_high")]

    def get_near_lows(self, results: list) -> list:
        """Stocks near their period low (within 3%)."""
        return [r for r in results if r.get("near_period_low")]

    def get_high_momentum(self, results: list, n: int = 15) -> list:
        """Stocks with strongest recent momentum."""
        return sorted(results, key=lambda x: x.get("recent_momentum", 0), reverse=True)[:n]

    def get_consistent_performers(self, results: list, n: int = 15) -> list:
        """Stocks with highest consistency (green weeks %)."""
        return sorted(results, key=lambda x: x.get("consistency_pct", 0), reverse=True)[:n]

    def get_multibaggers(self, results: list) -> list:
        """Stocks that 2x'd or more in the period."""
        return [r for r in results if r.get("pct_return", 0) >= 100]
