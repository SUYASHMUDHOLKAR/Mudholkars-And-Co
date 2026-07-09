"""
technical_analyst.py
--------------------
MID Colleague #1: Deep Technical Analyst

When any of the 10 timeframe agents find a stock worth looking at,
this colleague does DEEP technical analysis on it.

Analyses:
  - Multi-timeframe RSI, MACD, EMA, Bollinger, ADX, Stochastic
  - Support & Resistance levels (from pivot points)
  - Fibonacci retracement levels
  - Trend detection (uptrend / downtrend / sideways)
  - Moving Average convergence (20/50/200)
  - Volume-Price relationship
  - Overall Technical Score (0-100)
  - BUY / SELL / HOLD recommendation
"""

import logging
from typing import Optional
from datetime import datetime

import yfinance as yf
import pandas as pd

from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator, ADXIndicator, SMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange

logger = logging.getLogger(__name__)


class TechnicalAnalyst:
    """
    Deep technical analysis on any stock.
    Call analyze() with a symbol → get full TA report + BUY/SELL/HOLD.
    """

    def analyze(self, symbol: str) -> Optional[dict]:
        """
        Full deep technical analysis on one stock.
        Returns comprehensive dict with score 0-100 and recommendation.
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="1y", interval="1d")
            if df.empty or len(df) < 50:
                return None

            df.columns = [c.lower() for c in df.columns]
            close = df["close"]
            high  = df["high"]
            low   = df["low"]
            vol   = df["volume"]
            price = float(close.iloc[-1])

            # -- INDICATORS --
            rsi_val     = self._rsi(close)
            macd_data   = self._macd(close)
            ema_data    = self._emas(close, price)
            bb_data     = self._bollinger(close, price)
            adx_val     = self._adx(high, low, close)
            stoch_data  = self._stochastic(high, low, close)
            atr_val     = self._atr(high, low, close)
            vol_analysis= self._volume_analysis(close, vol)
            support_res = self._support_resistance(high, low, close)
            fib_levels  = self._fibonacci(high, low)
            trend       = self._trend_detection(close, ema_data)

            # -- SCORING --
            score, signals = self._compute_score(
                rsi_val, macd_data, ema_data, bb_data,
                adx_val, stoch_data, trend, vol_analysis
            )

            # -- RECOMMENDATION --
            if score >= 70:
                recommendation = "STRONG BUY"
            elif score >= 55:
                recommendation = "BUY"
            elif score >= 45:
                recommendation = "HOLD"
            elif score >= 30:
                recommendation = "SELL"
            else:
                recommendation = "STRONG SELL"

            return {
                "symbol":          symbol.replace(".NS", ""),
                "price":           round(price, 2),
                "timestamp":       datetime.utcnow().isoformat() + "Z",
                "technical_score": score,
                "recommendation":  recommendation,
                "signals":         signals,
                "indicators": {
                    "rsi":         rsi_val,
                    "macd":        macd_data,
                    "ema":         ema_data,
                    "bollinger":   bb_data,
                    "adx":         adx_val,
                    "stochastic":  stoch_data,
                    "atr":         round(atr_val, 4),
                    "volume":      vol_analysis,
                },
                "levels": {
                    "support_resistance": support_res,
                    "fibonacci":          fib_levels,
                },
                "trend":           trend,
            }
        except Exception as e:
            logger.error(f"[{symbol}] Technical analysis error: {e}")
            return None

    def analyze_batch(self, symbols: list) -> list:
        """Analyze multiple stocks. Returns list sorted by technical score."""
        results = []
        for sym in symbols:
            r = self.analyze(sym)
            if r:
                results.append(r)
        results.sort(key=lambda x: x["technical_score"], reverse=True)
        return results

    # ------------------------------------------------------------------
    # Indicator calculations
    # ------------------------------------------------------------------

    def _rsi(self, close: pd.Series, period: int = 14) -> dict:
        rsi = RSIIndicator(close=close, window=period).rsi()
        val = float(rsi.dropna().iloc[-1])
        if val >= 70:
            signal = "OVERBOUGHT"
        elif val <= 30:
            signal = "OVERSOLD"
        else:
            signal = "NEUTRAL"
        return {"value": round(val, 2), "signal": signal}

    def _macd(self, close: pd.Series) -> dict:
        m = MACD(close=close)
        macd_line = float(m.macd().dropna().iloc[-1])
        signal_line = float(m.macd_signal().dropna().iloc[-1])
        histogram = float(m.macd_diff().dropna().iloc[-1])
        prev_macd = float(m.macd().dropna().iloc[-2])
        prev_sig  = float(m.macd_signal().dropna().iloc[-2])

        crossover = "NONE"
        if prev_macd < prev_sig and macd_line >= signal_line:
            crossover = "BULLISH"
        elif prev_macd > prev_sig and macd_line <= signal_line:
            crossover = "BEARISH"

        return {
            "macd": round(macd_line, 4), "signal": round(signal_line, 4),
            "histogram": round(histogram, 4), "crossover": crossover,
            "trend": "BULLISH" if macd_line > signal_line else "BEARISH"
        }

    def _emas(self, close: pd.Series, price: float) -> dict:
        ema20  = float(EMAIndicator(close=close, window=20).ema_indicator().dropna().iloc[-1])
        ema50  = float(EMAIndicator(close=close, window=50).ema_indicator().dropna().iloc[-1])
        ema200 = float(EMAIndicator(close=close, window=200).ema_indicator().dropna().iloc[-1]) if len(close) >= 200 else None

        return {
            "ema_20": round(ema20, 2), "ema_50": round(ema50, 2),
            "ema_200": round(ema200, 2) if ema200 else None,
            "price_above_20": price > ema20,
            "price_above_50": price > ema50,
            "price_above_200": (price > ema200) if ema200 else None,
            "golden_cross": (ema50 > ema200) if ema200 else None,
        }

    def _bollinger(self, close: pd.Series, price: float) -> dict:
        bb = BollingerBands(close=close, window=20, window_dev=2)
        upper  = float(bb.bollinger_hband().dropna().iloc[-1])
        middle = float(bb.bollinger_mavg().dropna().iloc[-1])
        lower  = float(bb.bollinger_lband().dropna().iloc[-1])
        width  = ((upper - lower) / middle * 100) if middle else 0

        position = "MIDDLE"
        if price >= upper:
            position = "ABOVE_UPPER"
        elif price <= lower:
            position = "BELOW_LOWER"
        elif price > middle:
            position = "UPPER_HALF"
        else:
            position = "LOWER_HALF"

        return {
            "upper": round(upper, 2), "middle": round(middle, 2), "lower": round(lower, 2),
            "width_pct": round(width, 2), "position": position,
        }

    def _adx(self, high, low, close) -> dict:
        adx = ADXIndicator(high=high, low=low, close=close, window=14)
        val = float(adx.adx().dropna().iloc[-1])
        strength = "WEAK" if val < 20 else ("MODERATE" if val < 25 else ("STRONG" if val < 50 else "VERY_STRONG"))
        return {"value": round(val, 2), "trend_strength": strength}

    def _stochastic(self, high, low, close) -> dict:
        stoch = StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
        k = float(stoch.stoch().dropna().iloc[-1])
        d = float(stoch.stoch_signal().dropna().iloc[-1])
        signal = "OVERBOUGHT" if k >= 80 else ("OVERSOLD" if k <= 20 else "NEUTRAL")
        return {"k": round(k, 2), "d": round(d, 2), "signal": signal}

    def _atr(self, high, low, close) -> float:
        atr = AverageTrueRange(high=high, low=low, close=close, window=14)
        return float(atr.average_true_range().dropna().iloc[-1])

    def _volume_analysis(self, close: pd.Series, vol: pd.Series) -> dict:
        avg_20 = float(vol.tail(20).mean())
        latest = float(vol.iloc[-1])
        ratio  = latest / avg_20 if avg_20 else 1.0

        # Volume-price alignment
        price_up = float(close.iloc[-1]) > float(close.iloc[-2])
        vol_up   = latest > avg_20
        alignment = "CONFIRMED" if (price_up and vol_up) else (
            "DIVERGENCE" if (price_up and not vol_up) else "NORMAL"
        )

        return {
            "latest": int(latest), "avg_20": int(avg_20),
            "ratio": round(ratio, 2), "alignment": alignment,
        }

    def _support_resistance(self, high, low, close) -> dict:
        """Calculate pivot point-based support/resistance."""
        h = float(high.iloc[-1])
        l = float(low.iloc[-1])
        c = float(close.iloc[-1])
        pivot = (h + l + c) / 3

        return {
            "pivot":  round(pivot, 2),
            "R1":     round(2 * pivot - l, 2),
            "R2":     round(pivot + (h - l), 2),
            "S1":     round(2 * pivot - h, 2),
            "S2":     round(pivot - (h - l), 2),
        }

    def _fibonacci(self, high, low) -> dict:
        """Fibonacci retracement levels from period high/low."""
        h = float(high.max())
        l = float(low.min())
        diff = h - l
        return {
            "high":     round(h, 2),
            "low":      round(l, 2),
            "fib_236":  round(h - diff * 0.236, 2),
            "fib_382":  round(h - diff * 0.382, 2),
            "fib_500":  round(h - diff * 0.500, 2),
            "fib_618":  round(h - diff * 0.618, 2),
            "fib_786":  round(h - diff * 0.786, 2),
        }

    def _trend_detection(self, close: pd.Series, ema_data: dict) -> dict:
        above_20  = ema_data.get("price_above_20", False)
        above_50  = ema_data.get("price_above_50", False)
        above_200 = ema_data.get("price_above_200")
        golden    = ema_data.get("golden_cross")

        if above_20 and above_50 and above_200:
            trend = "STRONG_UPTREND"
        elif above_20 and above_50:
            trend = "UPTREND"
        elif not above_20 and not above_50 and above_200 == False:
            trend = "STRONG_DOWNTREND"
        elif not above_20 and not above_50:
            trend = "DOWNTREND"
        else:
            trend = "SIDEWAYS"

        return {"direction": trend, "golden_cross": golden}

    # ------------------------------------------------------------------
    # Score computation (0-100)
    # ------------------------------------------------------------------

    def _compute_score(self, rsi, macd, ema, bb, adx, stoch, trend, vol) -> tuple:
        """Compute technical score 0-100 based on all indicators."""
        score = 50  # start neutral
        signals = []

        # RSI contribution (±15)
        rsi_val = rsi["value"]
        if 40 <= rsi_val <= 60:
            score += 5  # neutral is fine
        elif rsi_val <= 30:
            score += 10; signals.append("RSI oversold (potential bounce)")
        elif rsi_val <= 40:
            score += 5
        elif rsi_val >= 70:
            score -= 10; signals.append("RSI overbought (caution)")
        elif rsi_val >= 60:
            score += 3  # momentum

        # MACD contribution (±10)
        if macd["crossover"] == "BULLISH":
            score += 10; signals.append("MACD bullish crossover")
        elif macd["crossover"] == "BEARISH":
            score -= 10; signals.append("MACD bearish crossover")
        elif macd["trend"] == "BULLISH":
            score += 5

        # EMA trend (±10)
        if trend["direction"] == "STRONG_UPTREND":
            score += 10; signals.append("Strong uptrend (above all MAs)")
        elif trend["direction"] == "UPTREND":
            score += 7; signals.append("Uptrend")
        elif trend["direction"] == "STRONG_DOWNTREND":
            score -= 10; signals.append("Strong downtrend")
        elif trend["direction"] == "DOWNTREND":
            score -= 7; signals.append("Downtrend")

        # Bollinger (±5)
        if bb["position"] == "BELOW_LOWER":
            score += 5; signals.append("Below lower Bollinger (oversold)")
        elif bb["position"] == "ABOVE_UPPER":
            score -= 5; signals.append("Above upper Bollinger (stretched)")

        # ADX (±5)
        if adx["trend_strength"] in ("STRONG", "VERY_STRONG"):
            score += 5; signals.append(f"Strong trend (ADX={adx['value']})")

        # Volume (±5)
        if vol["alignment"] == "CONFIRMED":
            score += 5; signals.append("Volume confirms price move")
        elif vol["alignment"] == "DIVERGENCE":
            score -= 3; signals.append("Volume divergence (weak move)")

        # Golden cross bonus
        if trend.get("golden_cross"):
            score += 5; signals.append("Golden cross active")

        score = max(0, min(100, score))
        return score, signals
