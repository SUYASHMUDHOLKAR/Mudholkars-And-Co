"""
indicator_tracker.py
--------------------
Computes technical indicators LOCALLY using the 'ta' library + yfinance.
No API key. No rate limits. No daily quota. 100% free.

Indicators covered:
  - RSI  (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - EMA  (Exponential Moving Average)
  - Bollinger Bands
  - ADX  (Average Directional Index — trend strength)
  - Stochastic Oscillator
  - ATR  (Average True Range — volatility)
"""

import logging
from typing import Optional

import yfinance as yf
import pandas as pd

import ta
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator, ADXIndicator
from ta.volatility import BollingerBands, AverageTrueRange

logger = logging.getLogger(__name__)


class IndicatorTracker:
    """
    Computes RSI, MACD, EMA, Bollinger Bands, ADX, Stochastic, ATR
    locally from yfinance data using the 'ta' library. No API key required.
    """

    def __init__(self, config: dict):
        self.thresholds = config.get("alert_thresholds", {})
        self.rsi_thresh = self.thresholds.get("rsi", {})

    # ------------------------------------------------------------------
    # Internal: fetch OHLCV from yfinance
    # ------------------------------------------------------------------

    def _fetch_ohlcv(self, symbol: str, period: str = "6mo",
                     interval: str = "1d") -> Optional[pd.DataFrame]:
        """Fetch OHLCV bars from yfinance for local indicator computation."""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df.empty:
                logger.warning(f"[{symbol}] No OHLCV data returned.")
                return None
            df.columns = [c.lower() for c in df.columns]
            return df.dropna()
        except Exception as e:
            logger.error(f"[{symbol}] OHLCV fetch error: {e}")
            return None

    # ------------------------------------------------------------------
    # RSI
    # ------------------------------------------------------------------

    def get_rsi(self, symbol: str, period: int = 14,
                interval: str = "1d") -> Optional[dict]:
        """
        RSI > 70 = overbought (potential sell signal).
        RSI < 30 = oversold  (potential buy signal).
        """
        df = self._fetch_ohlcv(symbol, interval=interval)
        if df is None or len(df) < period + 1:
            return None
        try:
            rsi_series = RSIIndicator(close=df["close"], window=period).rsi()
            rsi = float(rsi_series.dropna().iloc[-1])
            date = str(df.index[-1].date())

            if rsi >= self.rsi_thresh.get("extreme_overbought", 80):
                signal = "EXTREME_OVERBOUGHT"
            elif rsi >= self.rsi_thresh.get("overbought", 70):
                signal = "OVERBOUGHT"
            elif rsi <= self.rsi_thresh.get("extreme_oversold", 20):
                signal = "EXTREME_OVERSOLD"
            elif rsi <= self.rsi_thresh.get("oversold", 30):
                signal = "OVERSOLD"
            else:
                signal = "NEUTRAL"

            return {"symbol": symbol, "date": date,
                    "rsi": round(rsi, 2), "signal": signal, "period": period}
        except Exception as e:
            logger.error(f"[{symbol}] RSI error: {e}")
            return None

    # ------------------------------------------------------------------
    # MACD
    # ------------------------------------------------------------------

    def get_macd(self, symbol: str, fast: int = 12, slow: int = 26,
                 signal_period: int = 9, interval: str = "1d") -> Optional[dict]:
        """
        MACD line crosses above signal line = bullish crossover.
        MACD line crosses below signal line = bearish crossover.
        """
        df = self._fetch_ohlcv(symbol, interval=interval)
        if df is None or len(df) < slow + signal_period:
            return None
        try:
            macd_ind = MACD(close=df["close"],
                            window_fast=fast,
                            window_slow=slow,
                            window_sign=signal_period)

            macd_line   = macd_ind.macd().dropna()
            signal_line = macd_ind.macd_signal().dropna()
            histogram   = macd_ind.macd_diff().dropna()

            macd_val   = float(macd_line.iloc[-1])
            signal_val = float(signal_line.iloc[-1])
            hist_val   = float(histogram.iloc[-1])

            prev_macd   = float(macd_line.iloc[-2])
            prev_signal = float(signal_line.iloc[-2])

            crossover = "NONE"
            if prev_macd < prev_signal and macd_val >= signal_val:
                crossover = "BULLISH_CROSSOVER"
            elif prev_macd > prev_signal and macd_val <= signal_val:
                crossover = "BEARISH_CROSSOVER"

            date = str(df.index[-1].date())
            return {
                "symbol":    symbol,
                "date":      date,
                "macd":      round(macd_val, 4),
                "signal":    round(signal_val, 4),
                "histogram": round(hist_val, 4),
                "trend":     "BULLISH" if macd_val > signal_val else "BEARISH",
                "momentum":  "INCREASING" if hist_val > 0 else "DECREASING",
                "crossover": crossover,
            }
        except Exception as e:
            logger.error(f"[{symbol}] MACD error: {e}")
            return None

    # ------------------------------------------------------------------
    # EMA
    # ------------------------------------------------------------------

    def get_ema(self, symbol: str, period: int = 20,
                interval: str = "1d") -> Optional[dict]:
        """Exponential Moving Average — reacts faster to recent price changes."""
        df = self._fetch_ohlcv(symbol, interval=interval)
        if df is None or len(df) < period:
            return None
        try:
            ema_series = EMAIndicator(close=df["close"], window=period).ema_indicator()
            val  = float(ema_series.dropna().iloc[-1])
            date = str(df.index[-1].date())
            return {"symbol": symbol, "date": date,
                    "ema": round(val, 4), "period": period}
        except Exception as e:
            logger.error(f"[{symbol}] EMA error: {e}")
            return None

    # ------------------------------------------------------------------
    # Bollinger Bands
    # ------------------------------------------------------------------

    def get_bollinger_bands(self, symbol: str, period: int = 20,
                            std: float = 2.0,
                            interval: str = "1d") -> Optional[dict]:
        """
        Price above upper band = potential overbought breakout.
        Price below lower band = potential oversold breakdown.
        Narrow bandwidth = low volatility, breakout likely soon.
        """
        df = self._fetch_ohlcv(symbol, interval=interval)
        if df is None or len(df) < period:
            return None
        try:
            bb = BollingerBands(close=df["close"], window=period, window_dev=std)
            upper  = float(bb.bollinger_hband().dropna().iloc[-1])
            middle = float(bb.bollinger_mavg().dropna().iloc[-1])
            lower  = float(bb.bollinger_lband().dropna().iloc[-1])
            width  = ((upper - lower) / middle * 100) if middle else 0

            date = str(df.index[-1].date())
            return {
                "symbol":         symbol,
                "date":           date,
                "upper_band":     round(upper, 4),
                "middle_band":    round(middle, 4),
                "lower_band":     round(lower, 4),
                "band_width_pct": round(width, 2),
                "period":         period,
            }
        except Exception as e:
            logger.error(f"[{symbol}] Bollinger Bands error: {e}")
            return None

    # ------------------------------------------------------------------
    # ADX — Trend Strength
    # ------------------------------------------------------------------

    def get_adx(self, symbol: str, period: int = 14,
                interval: str = "1d") -> Optional[dict]:
        """
        ADX > 25 = strong trend (trade with the trend).
        ADX < 20 = weak/no trend (avoid trend-following strategies).
        """
        df = self._fetch_ohlcv(symbol, interval=interval)
        if df is None or len(df) < period + 1:
            return None
        try:
            adx_ind = ADXIndicator(high=df["high"], low=df["low"],
                                   close=df["close"], window=period)
            adx = float(adx_ind.adx().dropna().iloc[-1])

            if adx >= 50:
                strength = "VERY_STRONG"
            elif adx >= 25:
                strength = "STRONG"
            elif adx >= 20:
                strength = "MODERATE"
            else:
                strength = "WEAK"

            date = str(df.index[-1].date())
            return {"symbol": symbol, "date": date, "adx": round(adx, 2),
                    "trend_strength": strength, "period": period}
        except Exception as e:
            logger.error(f"[{symbol}] ADX error: {e}")
            return None

    # ------------------------------------------------------------------
    # Stochastic Oscillator
    # ------------------------------------------------------------------

    def get_stochastic(self, symbol: str, k: int = 14, d: int = 3,
                       interval: str = "1d") -> Optional[dict]:
        """
        %K > 80 = overbought. %K < 20 = oversold.
        %K crossing above %D = bullish signal.
        """
        df = self._fetch_ohlcv(symbol, interval=interval)
        if df is None or len(df) < k + d:
            return None
        try:
            stoch = StochasticOscillator(high=df["high"], low=df["low"],
                                         close=df["close"], window=k, smooth_window=d)
            k_val = float(stoch.stoch().dropna().iloc[-1])
            d_val = float(stoch.stoch_signal().dropna().iloc[-1])

            if k_val >= 80:
                signal = "OVERBOUGHT"
            elif k_val <= 20:
                signal = "OVERSOLD"
            else:
                signal = "NEUTRAL"

            date = str(df.index[-1].date())
            return {"symbol": symbol, "date": date,
                    "stoch_k": round(k_val, 2),
                    "stoch_d": round(d_val, 2),
                    "signal": signal}
        except Exception as e:
            logger.error(f"[{symbol}] Stochastic error: {e}")
            return None

    # ------------------------------------------------------------------
    # ATR — Volatility
    # ------------------------------------------------------------------

    def get_atr(self, symbol: str, period: int = 14,
                interval: str = "1d") -> Optional[dict]:
        """
        Rising ATR = increasing volatility (big moves expected).
        Falling ATR = market calming down.
        """
        df = self._fetch_ohlcv(symbol, interval=interval)
        if df is None or len(df) < period + 1:
            return None
        try:
            atr_ind = AverageTrueRange(high=df["high"], low=df["low"],
                                       close=df["close"], window=period)
            val  = float(atr_ind.average_true_range().dropna().iloc[-1])
            date = str(df.index[-1].date())
            return {"symbol": symbol, "date": date,
                    "atr": round(val, 4), "period": period}
        except Exception as e:
            logger.error(f"[{symbol}] ATR error: {e}")
            return None

    # ------------------------------------------------------------------
    # Full snapshot — all indicators for one symbol, one call
    # ------------------------------------------------------------------

    def get_full_snapshot(self, symbol: str, interval: str = "1d") -> dict:
        """
        Compute all indicators locally. No API calls, no limits.
        """
        logger.info(f"[{symbol}] Computing indicators locally...")
        return {
            "symbol":     symbol,
            "rsi":        self.get_rsi(symbol, interval=interval),
            "macd":       self.get_macd(symbol, interval=interval),
            "ema_20":     self.get_ema(symbol, period=20, interval=interval),
            "bollinger":  self.get_bollinger_bands(symbol, interval=interval),
            "adx":        self.get_adx(symbol, interval=interval),
            "stochastic": self.get_stochastic(symbol, interval=interval),
            "atr":        self.get_atr(symbol, interval=interval),
        }
