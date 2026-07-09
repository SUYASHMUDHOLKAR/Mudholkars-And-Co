"""
price_tracker.py
----------------
Fetches real-time and historical OHLCV data using yfinance.
Tracks: current price, % change, high/low, volume, 52-week range, gap detection.
"""

import logging
from datetime import datetime
from typing import Optional

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


class PriceTracker:
    """Fetches and analyzes price data for a given ticker using yfinance."""

    def __init__(self, config: dict):
        self.config = config
        self.thresholds = config.get("alert_thresholds", {})
        self.price_thresholds = self.thresholds.get("price_change", {})
        self.gap_thresholds = self.thresholds.get("gap", {})
        self.week52_thresholds = self.thresholds.get("week_52", {})

    def fetch_current(self, symbol: str) -> Optional[dict]:
        """
        Fetch current snapshot for a symbol.
        Returns dict with price, change, volume, high/low, 52-week range.
        """
        try:
            ticker = yf.Ticker(symbol)

            hist_1d = ticker.history(period="1d", interval="1m")
            hist_5d = ticker.history(period="5d", interval="1d")
            hist_1y = ticker.history(period="1y", interval="1d")

            if hist_1d.empty or hist_5d.empty:
                logger.warning(f"[{symbol}] No intraday data returned.")
                return None

            latest = hist_1d.iloc[-1]
            prev_close = (
                float(hist_5d.iloc[-2]["Close"])
                if len(hist_5d) >= 2
                else float(hist_5d.iloc[-1]["Open"])
            )

            current_price = float(latest["Close"])
            open_price    = float(hist_1d.iloc[0]["Open"])
            day_high      = float(hist_1d["High"].max())
            day_low       = float(hist_1d["Low"].min())
            volume        = int(hist_1d["Volume"].sum())
            avg_vol_30    = int(hist_1y["Volume"].tail(30).mean()) if len(hist_1y) >= 30 else volume

            pct_change   = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0
            gap_pct      = ((open_price - prev_close) / prev_close) * 100 if prev_close else 0
            volume_ratio = volume / avg_vol_30 if avg_vol_30 > 0 else 1.0

            week52_high = float(hist_1y["High"].max()) if not hist_1y.empty else None
            week52_low  = float(hist_1y["Low"].min())  if not hist_1y.empty else None

            near_52w_high = False
            near_52w_low  = False
            if week52_high:
                near_52w_high = (
                    (week52_high - current_price) / week52_high * 100
                    <= self.week52_thresholds.get("near_high_pct", 2.0)
                )
            if week52_low:
                near_52w_low = (
                    (current_price - week52_low) / week52_low * 100
                    <= self.week52_thresholds.get("near_low_pct", 2.0)
                )

            result = {
                "symbol":         symbol,
                "timestamp":      datetime.utcnow().isoformat() + "Z",
                "current_price":  round(current_price, 4),
                "open":           round(open_price, 4),
                "day_high":       round(day_high, 4),
                "day_low":        round(day_low, 4),
                "prev_close":     round(prev_close, 4),
                "pct_change":     round(pct_change, 4),
                "gap_pct":        round(gap_pct, 4),
                "volume":         volume,
                "avg_volume_30d": avg_vol_30,
                "volume_ratio":   round(volume_ratio, 2),
                "week_52_high":   round(week52_high, 4) if week52_high else None,
                "week_52_low":    round(week52_low, 4)  if week52_low  else None,
                "near_52w_high":  near_52w_high,
                "near_52w_low":   near_52w_low,
                "flags":          self._compute_flags(pct_change, gap_pct, volume_ratio),
            }

            logger.info(
                f"[{symbol}] Price: {current_price:.4f} | "
                f"Change: {pct_change:+.2f}% | Vol ratio: {volume_ratio:.1f}x"
            )
            return result

        except Exception as e:
            logger.error(f"[{symbol}] Error fetching price data: {e}")
            return None

    def fetch_intraday_bars(self, symbol: str, interval: str = "15m") -> Optional[pd.DataFrame]:
        """Fetch intraday OHLCV bars. Intervals: 1m, 5m, 15m, 30m, 60m, 90m."""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="1d", interval=interval)
            if df.empty:
                logger.warning(f"[{symbol}] No bars for interval={interval}")
                return None
            return df
        except Exception as e:
            logger.error(f"[{symbol}] Error fetching intraday bars: {e}")
            return None

    def fetch_daily_history(self, symbol: str, days: int = 200) -> Optional[pd.DataFrame]:
        """Fetch daily OHLCV bars for the past N days."""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=f"{days}d", interval="1d")
            if df.empty:
                logger.warning(f"[{symbol}] No daily history found.")
                return None
            return df
        except Exception as e:
            logger.error(f"[{symbol}] Error fetching daily history: {e}")
            return None

    def fetch_all(self, symbols: list) -> dict:
        """Fetch current snapshot for multiple symbols."""
        results = {}
        for symbol in symbols:
            data = self.fetch_current(symbol)
            results[symbol] = data if data else {"symbol": symbol, "error": "fetch_failed"}
        return results

    def compute_moving_averages(self, symbol: str) -> Optional[dict]:
        """
        Compute 20, 50, 200-day MAs and detect golden/death cross.
        Golden cross: 50MA crosses above 200MA (bullish).
        Death cross:  50MA crosses below 200MA (bearish).
        """
        try:
            df = self.fetch_daily_history(symbol, days=210)
            if df is None or len(df) < 50:
                return None

            close = df["Close"]
            ma20  = float(close.rolling(20).mean().iloc[-1])
            ma50  = float(close.rolling(50).mean().iloc[-1])
            ma200 = float(close.rolling(200).mean().iloc[-1]) if len(df) >= 200 else None

            current    = float(close.iloc[-1])
            prev_ma50  = float(close.rolling(50).mean().iloc[-2])
            prev_ma200 = float(close.rolling(200).mean().iloc[-2]) if len(df) >= 200 else None

            golden_cross = bool(prev_ma50 < prev_ma200 and ma50 >= ma200) if (ma200 and prev_ma200) else False
            death_cross  = bool(prev_ma50 > prev_ma200 and ma50 <= ma200) if (ma200 and prev_ma200) else False

            return {
                "symbol":       symbol,
                "current":      round(current, 4),
                "ma_20":        round(ma20, 4),
                "ma_50":        round(ma50, 4),
                "ma_200":       round(ma200, 4) if ma200 else None,
                "above_ma20":   current > ma20,
                "above_ma50":   current > ma50,
                "above_ma200":  (current > ma200) if ma200 else None,
                "golden_cross": golden_cross,
                "death_cross":  death_cross,
            }
        except Exception as e:
            logger.error(f"[{symbol}] Error computing MAs: {e}")
            return None

    def _compute_flags(self, pct_change: float, gap_pct: float, volume_ratio: float) -> list:
        """Return alert flag strings based on thresholds."""
        flags = []
        warn  = self.price_thresholds.get("warning_pct", 1.5)
        crit  = self.price_thresholds.get("critical_pct", 3.0)
        ext   = self.price_thresholds.get("extreme_pct", 5.0)
        vol_s = self.thresholds.get("volume", {}).get("spike_multiplier", 2.0)
        vol_e = self.thresholds.get("volume", {}).get("extreme_spike_multiplier", 3.5)
        gap_u = self.gap_thresholds.get("gap_up_pct", 1.5)
        gap_d = self.gap_thresholds.get("gap_down_pct", -1.5)

        abs_chg = abs(pct_change)
        if abs_chg >= ext:
            flags.append("EXTREME_MOVE")
        elif abs_chg >= crit:
            flags.append("CRITICAL_MOVE")
        elif abs_chg >= warn:
            flags.append("WARNING_MOVE")

        if pct_change >= ext:
            flags.append("EXTREME_SURGE")
        elif pct_change <= -ext:
            flags.append("EXTREME_CRASH")

        if volume_ratio >= vol_e:
            flags.append("EXTREME_VOLUME_SPIKE")
        elif volume_ratio >= vol_s:
            flags.append("VOLUME_SPIKE")

        if gap_pct >= gap_u:
            flags.append("GAP_UP")
        elif gap_pct <= gap_d:
            flags.append("GAP_DOWN")

        return flags
