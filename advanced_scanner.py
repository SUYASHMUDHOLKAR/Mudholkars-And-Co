"""
Advanced Stock Scanner Module
=============================
Production-ready scanners for Indian stock market signals.
Uses yfinance (free, no API keys required).

Classes:
    - CircuitDetector: Detects upper/lower circuit hits (5%/10%/20%)
    - CandlestickScanner: Detects key candlestick patterns from OHLC data
    - GapScanner: Detects gap up (>1.5%) and gap down (<-1.5%) openings
    - RelativeStrengthScanner: Compares stock performance vs Nifty50
    - BreakoutDetector: Detects 20-day high/low breakouts
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
import yfinance as yf

# Configure module logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

CIRCUIT_LIMITS = [0.05, 0.10, 0.20]


def _fetch_data(symbol: str, period: str = "30d", interval: str = "1d") -> Optional[object]:
    """Fetch OHLC data from yfinance with error handling."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return None
        return df
    except Exception as e:
        logger.error(f"Failed to fetch data for {symbol}: {e}")
        return None


class CircuitDetector:
    """
    Detects stocks hitting upper or lower circuit limits.
    Indian markets use 5%, 10%, and 20% circuit breakers.
    """

    def __init__(self):
        self.circuit_limits = CIRCUIT_LIMITS

    def scan(self, symbol: str) -> Dict:
        """Scan a single symbol for circuit hits."""
        result = {
            "symbol": symbol,
            "signal": "circuit",
            "circuit_hit": False,
            "direction": None,
            "limit_pct": None,
            "change_pct": None,
            "timestamp": datetime.now().isoformat(),
        }
        try:
            df = _fetch_data(symbol, period="5d")
            if df is None or len(df) < 2:
                result["error"] = "Insufficient data"
                return result

            prev_close = df["Close"].iloc[-2]
            current_close = df["Close"].iloc[-1]
            change_pct = (current_close - prev_close) / prev_close
            result["change_pct"] = round(change_pct * 100, 2)

            for limit in sorted(self.circuit_limits):
                if change_pct >= limit * 0.95:
                    result["circuit_hit"] = True
                    result["direction"] = "upper"
                    result["limit_pct"] = int(limit * 100)
                elif change_pct <= -limit * 0.95:
                    result["circuit_hit"] = True
                    result["direction"] = "lower"
                    result["limit_pct"] = int(limit * 100)

            logger.info(f"CircuitDetector: {symbol} change={result['change_pct']}% hit={result['circuit_hit']}")
        except Exception as e:
            logger.error(f"CircuitDetector error for {symbol}: {e}")
            result["error"] = str(e)
        return result

    def scan_all(self, symbols: List[str]) -> List[Dict]:
        """Scan multiple symbols for circuit hits."""
        return [self.scan(s) for s in symbols]


class CandlestickScanner:
    """
    Detects key candlestick patterns from OHLC data.
    Patterns: Hammer, Bullish Engulfing, Bearish Engulfing, Doji, Morning Star, Shooting Star
    """

    def __init__(self, doji_threshold: float = 0.01):
        self.doji_threshold = doji_threshold

    def _detect_hammer(self, o, h, l, c) -> bool:
        body = abs(c - o)
        total_range = h - l
        if total_range == 0:
            return False
        lower_shadow = min(o, c) - l
        upper_shadow = h - max(o, c)
        return lower_shadow >= 2 * body and upper_shadow <= body * 0.3 and body / total_range <= 0.35

    def _detect_shooting_star(self, o, h, l, c) -> bool:
        body = abs(c - o)
        total_range = h - l
        if total_range == 0:
            return False
        upper_shadow = h - max(o, c)
        lower_shadow = min(o, c) - l
        return upper_shadow >= 2 * body and lower_shadow <= body * 0.3 and body / total_range <= 0.35

    def _detect_doji(self, o, h, l, c) -> bool:
        total_range = h - l
        if total_range == 0:
            return True
        body = abs(c - o)
        return (body / total_range) <= self.doji_threshold * 10

    def _detect_bullish_engulfing(self, p_o, p_h, p_l, p_c, o, h, l, c) -> bool:
        prev_bearish = p_c < p_o
        curr_bullish = c > o
        engulfs = o <= p_c and c >= p_o
        return prev_bearish and curr_bullish and engulfs

    def _detect_bearish_engulfing(self, p_o, p_h, p_l, p_c, o, h, l, c) -> bool:
        prev_bullish = p_c > p_o
        curr_bearish = c < o
        engulfs = o >= p_c and c <= p_o
        return prev_bullish and curr_bearish and engulfs

    def _detect_morning_star(self, candles: List) -> bool:
        if len(candles) < 3:
            return False
        c1_o, _, _, c1_c = candles[0]
        c2_o, _, _, c2_c = candles[1]
        c3_o, _, _, c3_c = candles[2]
        c1_bearish = c1_c < c1_o and abs(c1_c - c1_o) > 0.005 * c1_o
        c2_small = abs(c2_c - c2_o) < abs(c1_c - c1_o) * 0.3
        c3_bullish = c3_c > c3_o
        c3_closes_above_mid = c3_c > (c1_o + c1_c) / 2
        return c1_bearish and c2_small and c3_bullish and c3_closes_above_mid

    def scan(self, symbol: str) -> Dict:
        """Scan a single symbol for candlestick patterns."""
        result = {
            "symbol": symbol,
            "signal": "candlestick",
            "patterns_detected": [],
            "bullish_count": 0,
            "bearish_count": 0,
            "timestamp": datetime.now().isoformat(),
        }
        try:
            df = _fetch_data(symbol, period="10d")
            if df is None or len(df) < 3:
                result["error"] = "Insufficient data"
                return result

            o, h, l, c = df["Open"].iloc[-1], df["High"].iloc[-1], df["Low"].iloc[-1], df["Close"].iloc[-1]
            p_o, p_h, p_l, p_c = df["Open"].iloc[-2], df["High"].iloc[-2], df["Low"].iloc[-2], df["Close"].iloc[-2]

            if self._detect_hammer(o, h, l, c):
                result["patterns_detected"].append("Hammer")
                result["bullish_count"] += 1
            if self._detect_shooting_star(o, h, l, c):
                result["patterns_detected"].append("Shooting Star")
                result["bearish_count"] += 1
            if self._detect_doji(o, h, l, c):
                result["patterns_detected"].append("Doji")
            if self._detect_bullish_engulfing(p_o, p_h, p_l, p_c, o, h, l, c):
                result["patterns_detected"].append("Bullish Engulfing")
                result["bullish_count"] += 1
            if self._detect_bearish_engulfing(p_o, p_h, p_l, p_c, o, h, l, c):
                result["patterns_detected"].append("Bearish Engulfing")
                result["bearish_count"] += 1

            if len(df) >= 3:
                candles = [
                    (df["Open"].iloc[-3], df["High"].iloc[-3], df["Low"].iloc[-3], df["Close"].iloc[-3]),
                    (df["Open"].iloc[-2], df["High"].iloc[-2], df["Low"].iloc[-2], df["Close"].iloc[-2]),
                    (df["Open"].iloc[-1], df["High"].iloc[-1], df["Low"].iloc[-1], df["Close"].iloc[-1]),
                ]
                if self._detect_morning_star(candles):
                    result["patterns_detected"].append("Morning Star")
                    result["bullish_count"] += 1

            logger.info(f"CandlestickScanner: {symbol} patterns={result['patterns_detected']}")
        except Exception as e:
            logger.error(f"CandlestickScanner error for {symbol}: {e}")
            result["error"] = str(e)
        return result

    def scan_all(self, symbols: List[str]) -> List[Dict]:
        """Scan multiple symbols for candlestick patterns."""
        return [self.scan(s) for s in symbols]


class GapScanner:
    """
    Detects gap up (>1.5%) and gap down (<-1.5%) openings.
    Compares today's open to previous day's close.
    """

    def __init__(self, gap_threshold: float = 1.5):
        self.gap_threshold = gap_threshold

    def scan(self, symbol: str) -> Dict:
        """Scan a single symbol for gap openings."""
        result = {
            "symbol": symbol,
            "signal": "gap",
            "gap_type": None,
            "gap_pct": None,
            "prev_close": None,
            "today_open": None,
            "timestamp": datetime.now().isoformat(),
        }
        try:
            df = _fetch_data(symbol, period="5d")
            if df is None or len(df) < 2:
                result["error"] = "Insufficient data"
                return result

            prev_close = df["Close"].iloc[-2]
            today_open = df["Open"].iloc[-1]
            gap_pct = ((today_open - prev_close) / prev_close) * 100

            result["prev_close"] = round(float(prev_close), 2)
            result["today_open"] = round(float(today_open), 2)
            result["gap_pct"] = round(gap_pct, 2)

            if gap_pct > self.gap_threshold:
                result["gap_type"] = "gap_up"
            elif gap_pct < -self.gap_threshold:
                result["gap_type"] = "gap_down"

            logger.info(f"GapScanner: {symbol} gap={result['gap_pct']}% type={result['gap_type']}")
        except Exception as e:
            logger.error(f"GapScanner error for {symbol}: {e}")
            result["error"] = str(e)
        return result

    def scan_all(self, symbols: List[str]) -> List[Dict]:
        """Scan multiple symbols for gap openings."""
        return [self.scan(s) for s in symbols]


class RelativeStrengthScanner:
    """
    Compares each stock's performance vs Nifty50 over 20 days.
    RS > 1 means the stock is outperforming the benchmark.
    """

    def __init__(self, benchmark: str = "^NSEI", lookback_days: int = 20):
        self.benchmark = benchmark
        self.lookback_days = lookback_days
        self._benchmark_return = None

    def _get_benchmark_return(self) -> Optional[float]:
        """Fetch Nifty50 return over the lookback period."""
        if self._benchmark_return is not None:
            return self._benchmark_return
        try:
            df = _fetch_data(self.benchmark, period="60d")
            if df is None or len(df) < self.lookback_days:
                return None
            start_price = df["Close"].iloc[-self.lookback_days]
            end_price = df["Close"].iloc[-1]
            self._benchmark_return = (end_price - start_price) / start_price
            return self._benchmark_return
        except Exception as e:
            logger.error(f"Failed to get benchmark return: {e}")
            return None

    def scan(self, symbol: str) -> Dict:
        """Scan a single symbol for relative strength vs Nifty50."""
        result = {
            "symbol": symbol,
            "signal": "relative_strength",
            "rs_ratio": None,
            "stock_return_pct": None,
            "benchmark_return_pct": None,
            "outperforming": False,
            "timestamp": datetime.now().isoformat(),
        }
        try:
            benchmark_return = self._get_benchmark_return()
            if benchmark_return is None:
                result["error"] = "Could not fetch benchmark data"
                return result

            df = _fetch_data(symbol, period="60d")
            if df is None or len(df) < self.lookback_days:
                result["error"] = "Insufficient stock data"
                return result

            start_price = df["Close"].iloc[-self.lookback_days]
            end_price = df["Close"].iloc[-1]
            stock_return = (end_price - start_price) / start_price

            if benchmark_return == 0:
                rs_ratio = 1.0 if stock_return == 0 else (2.0 if stock_return > 0 else 0.5)
            elif benchmark_return < 0:
                rs_ratio = 2.0 if stock_return >= 0 else benchmark_return / stock_return
            else:
                rs_ratio = (1 + stock_return) / (1 + benchmark_return)

            result["rs_ratio"] = round(float(rs_ratio), 3)
            result["stock_return_pct"] = round(float(stock_return * 100), 2)
            result["benchmark_return_pct"] = round(float(benchmark_return * 100), 2)
            result["outperforming"] = rs_ratio > 1.0

            logger.info(f"RSScanner: {symbol} RS={result['rs_ratio']} outperforming={result['outperforming']}")
        except Exception as e:
            logger.error(f"RelativeStrengthScanner error for {symbol}: {e}")
            result["error"] = str(e)
        return result

    def scan_all(self, symbols: List[str]) -> List[Dict]:
        """Scan multiple symbols for relative strength."""
        return [self.scan(s) for s in symbols]


class BreakoutDetector:
    """
    Detects when price breaks above 20-day high (resistance breakout)
    or below 20-day low (support breakdown).
    """

    def __init__(self, lookback_days: int = 20):
        self.lookback_days = lookback_days

    def scan(self, symbol: str) -> Dict:
        """Scan a single symbol for breakouts."""
        result = {
            "symbol": symbol,
            "signal": "breakout",
            "breakout_type": None,
            "current_price": None,
            "twenty_day_high": None,
            "twenty_day_low": None,
            "breakout_pct": None,
            "timestamp": datetime.now().isoformat(),
        }
        try:
            df = _fetch_data(symbol, period="60d")
            if df is None or len(df) < self.lookback_days + 1:
                result["error"] = "Insufficient data"
                return result

            lookback_data = df.iloc[-(self.lookback_days + 1):-1]
            twenty_day_high = float(lookback_data["High"].max())
            twenty_day_low = float(lookback_data["Low"].min())
            current_price = float(df["Close"].iloc[-1])
            today_high = float(df["High"].iloc[-1])
            today_low = float(df["Low"].iloc[-1])

            result["current_price"] = round(current_price, 2)
            result["twenty_day_high"] = round(twenty_day_high, 2)
            result["twenty_day_low"] = round(twenty_day_low, 2)

            if today_high > twenty_day_high:
                result["breakout_type"] = "resistance_breakout"
                result["breakout_pct"] = round(((current_price - twenty_day_high) / twenty_day_high) * 100, 2)
            elif today_low < twenty_day_low:
                result["breakout_type"] = "support_breakdown"
                result["breakout_pct"] = round(((current_price - twenty_day_low) / twenty_day_low) * 100, 2)

            logger.info(f"BreakoutDetector: {symbol} type={result['breakout_type']} price={result['current_price']}")
        except Exception as e:
            logger.error(f"BreakoutDetector error for {symbol}: {e}")
            result["error"] = str(e)
        return result

    def scan_all(self, symbols: List[str]) -> List[Dict]:
        """Scan multiple symbols for breakouts."""
        return [self.scan(s) for s in symbols]


def run_full_scan(symbols: List[str]) -> Dict[str, List[Dict]]:
    """Run all scanners on the given symbols and return consolidated results."""
    logger.info(f"Running full scan on {len(symbols)} symbols...")
    results = {
        "circuits": CircuitDetector().scan_all(symbols),
        "candlesticks": CandlestickScanner().scan_all(symbols),
        "gaps": GapScanner().scan_all(symbols),
        "relative_strength": RelativeStrengthScanner().scan_all(symbols),
        "breakouts": BreakoutDetector().scan_all(symbols),
        "scan_timestamp": datetime.now().isoformat(),
        "symbols_scanned": len(symbols),
    }
    logger.info("Full scan complete.")
    return results


if __name__ == "__main__":
    test_symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]
    results = run_full_scan(test_symbols)
    import json
    print(json.dumps(results, indent=2, default=str))
