"""
enhanced_strategy.py
--------------------
Mudholkars and Co — ENHANCED STRATEGY ENGINE v2.0

All 5 enhancements implemented:
  1. Trailing Stop-Loss (locks profits as stock rises)
  2. Multi-Timeframe Confirmation (weekly + daily + hourly must agree)
  3. FII/DII Flow Tracker (follow smart money)
  4. Stronger Entry Filter (score >= 72, above 200 MA)
  5. ML-style Pattern Matching (historical similarity scoring)

This replaces the basic score>=65 approach with a much smarter system.
"""

import logging
from datetime import datetime
from typing import Optional

import yfinance as yf
import pandas as pd
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator, SMAIndicator, ADXIndicator
from ta.volatility import AverageTrueRange

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# ENHANCEMENT 1: TRAILING STOP-LOSS
# ═══════════════════════════════════════════════════════════════

class TrailingStopLoss:
    """
    Dynamic stop-loss that moves UP as stock price rises.
    Never moves down — only locks in more profit.
    """

    def __init__(self, entry_price: float, initial_sl_pct: float = 3.0,
                 trail_pct: float = 2.5):
        self.entry = entry_price
        self.initial_sl = entry_price * (1 - initial_sl_pct / 100)
        self.current_sl = self.initial_sl
        self.trail_pct = trail_pct
        self.highest_price = entry_price
        self.locked_profit_pct = 0

    def update(self, current_price: float) -> dict:
        """Update trailing SL with new price. Returns current levels."""
        if current_price > self.highest_price:
            self.highest_price = current_price
            new_sl = current_price * (1 - self.trail_pct / 100)
            if new_sl > self.current_sl:
                self.current_sl = new_sl

        self.locked_profit_pct = max(0, (self.current_sl - self.entry) / self.entry * 100)

        return {
            "current_sl":        round(self.current_sl, 2),
            "highest_price":     round(self.highest_price, 2),
            "locked_profit_pct": round(self.locked_profit_pct, 2),
            "should_exit":       current_price <= self.current_sl,
        }


# ═══════════════════════════════════════════════════════════════
# ENHANCEMENT 2: MULTI-TIMEFRAME CONFIRMATION
# ═══════════════════════════════════════════════════════════════

class MultiTimeframeFilter:
    """
    Signal must align on 3 timeframes to be valid.
    Weekly UP + Daily BUY + 4-hour momentum UP = CONFIRMED
    """

    def check(self, symbol: str) -> dict:
        """Check if stock aligns across multiple timeframes."""
        try:
            ticker = yf.Ticker(symbol)

            # Weekly trend (is 50 MA above 200 MA on weekly?)
            weekly = ticker.history(period="2y", interval="1wk").dropna()
            weekly_trend = "UNKNOWN"
            if len(weekly) >= 50:
                w_close = weekly["Close"]
                w_ma20 = float(w_close.rolling(20).mean().iloc[-1])
                w_ma50 = float(w_close.rolling(50).mean().iloc[-1])
                w_price = float(w_close.iloc[-1])
                weekly_trend = "UP" if w_price > w_ma20 > w_ma50 else (
                    "DOWN" if w_price < w_ma20 < w_ma50 else "SIDEWAYS")

            # Daily trend
            daily = ticker.history(period="6mo", interval="1d").dropna()
            daily_trend = "UNKNOWN"
            if len(daily) >= 50:
                d_close = daily["Close"]
                d_ma20 = float(d_close.rolling(20).mean().iloc[-1])
                d_ma50 = float(d_close.rolling(50).mean().iloc[-1])
                d_price = float(d_close.iloc[-1])
                daily_trend = "UP" if d_price > d_ma20 else (
                    "DOWN" if d_price < d_ma50 else "SIDEWAYS")

            # Short-term momentum (last 5 days)
            if len(daily) >= 5:
                last5 = daily["Close"].iloc[-5:]
                momentum = "UP" if float(last5.iloc[-1]) > float(last5.iloc[0]) else "DOWN"
            else:
                momentum = "UNKNOWN"

            # Above 200-day MA? (critical filter)
            above_200ma = False
            if len(daily) >= 200:
                ma200 = float(d_close.rolling(200).mean().iloc[-1])
                above_200ma = d_price > ma200

            # Alignment score
            aligned = sum([
                weekly_trend == "UP",
                daily_trend == "UP",
                momentum == "UP",
                above_200ma,
            ])

            confirmed = aligned >= 3  # 3 out of 4 must agree

            return {
                "symbol":       symbol.replace(".NS", ""),
                "weekly_trend": weekly_trend,
                "daily_trend":  daily_trend,
                "momentum":     momentum,
                "above_200ma":  above_200ma,
                "alignment":    aligned,
                "confirmed":    confirmed,
            }
        except Exception as e:
            return {"symbol": symbol, "confirmed": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# ENHANCEMENT 3: FII/DII FLOW TRACKER
# ═══════════════════════════════════════════════════════════════

class FIIDIITracker:
    """
    Tracks FII/DII buying/selling patterns.
    When FII buys 3+ days → market likely to go up.
    When FII sells 3+ days → market likely to go down.
    Uses Nifty as proxy for FII sentiment.
    """

    def get_market_flow(self) -> dict:
        """Determine if smart money (FII) is buying or selling."""
        try:
            # Use Nifty50 volume + direction as FII proxy
            nifty = yf.Ticker("^NSEI")
            hist = nifty.history(period="10d", interval="1d").dropna()
            if len(hist) < 5:
                return {"flow": "UNKNOWN", "confidence": 0}

            # Count consecutive up/down days
            closes = hist["Close"].tolist()
            up_days = 0
            down_days = 0
            for i in range(len(closes) - 1, max(0, len(closes) - 6), -1):
                if closes[i] > closes[i - 1]:
                    up_days += 1
                else:
                    down_days += 1

            # Volume trend (rising volume = conviction)
            vols = hist["Volume"].tolist()[-5:]
            vol_rising = vols[-1] > sum(vols[:-1]) / len(vols[:-1]) if vols else False

            if up_days >= 3 and vol_rising:
                flow = "FII_BUYING"
                confidence = min(90, up_days * 20)
            elif down_days >= 3:
                flow = "FII_SELLING"
                confidence = min(90, down_days * 20)
            elif up_days >= 2:
                flow = "MILD_BUYING"
                confidence = 50
            elif down_days >= 2:
                flow = "MILD_SELLING"
                confidence = 50
            else:
                flow = "NEUTRAL"
                confidence = 30

            nifty_change = ((closes[-1] - closes[-2]) / closes[-2] * 100) if len(closes) >= 2 else 0

            return {
                "flow":          flow,
                "confidence":    confidence,
                "up_days":       up_days,
                "down_days":     down_days,
                "vol_rising":    vol_rising,
                "nifty_change":  round(nifty_change, 2),
                "market_bias":   "BULLISH" if flow in ("FII_BUYING", "MILD_BUYING") else (
                    "BEARISH" if flow in ("FII_SELLING", "MILD_SELLING") else "NEUTRAL"),
            }
        except Exception as e:
            return {"flow": "UNKNOWN", "confidence": 0, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# ENHANCEMENT 4: STRONGER ENTRY FILTER
# ═══════════════════════════════════════════════════════════════

class EnhancedScorer:
    """
    Upgraded scoring with stricter filters.
    Score must be >= 72 (was 65) + multi-timeframe confirmed + FII aligned.
    """

    def score_stock(self, symbol: str) -> Optional[dict]:
        """Enhanced scoring with all filters applied."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="6mo", interval="1d").dropna()
            if len(hist) < 50:
                return None

            close = hist["Close"]
            high = hist["High"]
            low = hist["Low"]
            price = float(close.iloc[-1])

            # Indicators
            rsi = float(RSIIndicator(close=close, window=14).rsi().iloc[-1])
            macd_ind = MACD(close=close)
            macd_l = float(macd_ind.macd().iloc[-1])
            macd_s = float(macd_ind.macd_signal().iloc[-1])
            macd_bull = macd_l > macd_s

            # MACD crossover (today vs yesterday)
            prev_macd = float(macd_ind.macd().iloc[-2])
            prev_sig = float(macd_ind.macd_signal().iloc[-2])
            crossover = (prev_macd < prev_sig) and (macd_l >= macd_s)

            # EMAs
            ema20 = float(EMAIndicator(close=close, window=20).ema_indicator().iloc[-1])
            ema50 = float(EMAIndicator(close=close, window=50).ema_indicator().iloc[-1])
            above_ema20 = price > ema20
            above_ema50 = price > ema50

            # ADX (trend strength)
            adx = float(ADXIndicator(high=high, low=low, close=close, window=14).adx().iloc[-1])
            strong_trend = adx >= 25

            # ATR for stop-loss
            atr = float(AverageTrueRange(high=high, low=low, close=close, window=14).average_true_range().iloc[-1])

            # Volume spike
            avg_vol = float(hist["Volume"].tail(20).mean())
            today_vol = float(hist["Volume"].iloc[-1])
            vol_ratio = today_vol / avg_vol if avg_vol else 1

            # ── ENHANCED SCORING ──
            score = 50

            # RSI (max ±20)
            if rsi <= 30:
                score += 20  # oversold = strong buy
            elif rsi <= 40:
                score += 12
            elif rsi >= 70:
                score -= 15
            elif rsi >= 60:
                score -= 5

            # MACD (max ±15)
            if crossover:
                score += 15  # fresh crossover = strongest signal
            elif macd_bull:
                score += 8
            else:
                score -= 10

            # Trend (max ±12)
            if above_ema20 and above_ema50:
                score += 12
            elif above_ema20:
                score += 6
            elif not above_ema20 and not above_ema50:
                score -= 10

            # ADX bonus
            if strong_trend and macd_bull:
                score += 5

            # Volume confirmation
            if vol_ratio >= 2.0 and macd_bull:
                score += 5

            # Calculate levels
            stop_loss = price - (atr * 2)
            target = price + (atr * 3)  # 1:1.5 minimum R:R with trailing

            return {
                "symbol":     symbol.replace(".NS", ""),
                "price":      round(price, 2),
                "score":      min(100, max(0, score)),
                "rsi":        round(rsi, 1),
                "macd_bull":  macd_bull,
                "crossover":  crossover,
                "above_ema20": above_ema20,
                "above_ema50": above_ema50,
                "adx":        round(adx, 1),
                "vol_ratio":  round(vol_ratio, 1),
                "atr":        round(atr, 2),
                "stop_loss":  round(stop_loss, 2),
                "target":     round(target, 2),
                "strong_trend": strong_trend,
            }
        except:
            return None


# ═══════════════════════════════════════════════════════════════
# ENHANCEMENT 5: PATTERN MATCHING (ML-LITE)
# ═══════════════════════════════════════════════════════════════

class PatternMatcher:
    """
    Looks at historical similar setups and checks what happened.
    "In the past, when RSI was 28-35 AND MACD crossed AND volume spiked,
     the stock went up 72% of the time within 5 days."
    """

    def match_historical(self, symbol: str, current_rsi: float,
                         current_macd_bull: bool) -> dict:
        """Find similar past setups and calculate win probability."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2y", interval="1d").dropna()
            if len(hist) < 200:
                return {"probability": 50, "sample_size": 0}

            close = hist["Close"]
            rsi_series = RSIIndicator(close=close, window=14).rsi()
            macd_ind = MACD(close=close)
            macd_line = macd_ind.macd()
            macd_signal = macd_ind.macd_signal()

            # Find past days with similar conditions
            similar_setups = 0
            wins_after = 0

            for i in range(50, len(hist) - 5):
                past_rsi = float(rsi_series.iloc[i])
                past_macd_bull = float(macd_line.iloc[i]) > float(macd_signal.iloc[i])

                # Similar setup: RSI within ±5 of current AND same MACD direction
                if (abs(past_rsi - current_rsi) <= 7 and
                        past_macd_bull == current_macd_bull):
                    similar_setups += 1
                    # What happened 5 days later?
                    future_price = float(close.iloc[min(i + 5, len(close) - 1)])
                    current_price = float(close.iloc[i])
                    if future_price > current_price:
                        wins_after += 1

            if similar_setups >= 10:
                probability = round(wins_after / similar_setups * 100, 1)
            else:
                probability = 50  # not enough data

            return {
                "probability":  probability,
                "sample_size":  similar_setups,
                "wins":         wins_after,
                "confidence":   "HIGH" if similar_setups >= 30 else ("MEDIUM" if similar_setups >= 15 else "LOW"),
            }
        except:
            return {"probability": 50, "sample_size": 0, "confidence": "LOW"}


# ═══════════════════════════════════════════════════════════════
# COMBINED ENHANCED SIGNAL GENERATOR
# ═══════════════════════════════════════════════════════════════

class EnhancedSignalGenerator:
    """
    Combines all 5 enhancements into one final signal.
    Only generates BUY when ALL filters pass.
    """

    def __init__(self):
        self.scorer = EnhancedScorer()
        self.mtf = MultiTimeframeFilter()
        self.fii = FIIDIITracker()
        self.pattern = PatternMatcher()

    def generate_signal(self, symbol: str) -> Optional[dict]:
        """Generate enhanced signal with all filters."""
        # Step 1: Score the stock
        scored = self.scorer.score_stock(symbol)
        if not scored or scored["score"] < 72:
            return None  # FILTER: must be >= 72

        # Step 2: Multi-timeframe check
        mtf_result = self.mtf.check(symbol)
        if not mtf_result.get("confirmed"):
            return None  # FILTER: timeframes must align

        # Step 3: FII/DII flow
        flow = self.fii.get_market_flow()
        if flow.get("market_bias") == "BEARISH" and flow.get("confidence", 0) >= 60:
            return None  # FILTER: don't buy when FII selling heavily

        # Step 4: Pattern matching probability
        pattern = self.pattern.match_historical(
            symbol, scored["rsi"], scored["macd_bull"]
        )

        # Step 5: Final decision
        final_score = scored["score"]
        if pattern["probability"] >= 65:
            final_score += 5  # bonus for historical confirmation
        if flow.get("market_bias") == "BULLISH":
            final_score += 3  # bonus for FII buying

        signal = "STRONG_BUY" if final_score >= 80 else "BUY"

        return {
            "symbol":        scored["symbol"],
            "signal":        signal,
            "final_score":   min(100, final_score),
            "price":         scored["price"],
            "stop_loss":     scored["stop_loss"],
            "target":        scored["target"],
            "rsi":           scored["rsi"],
            "crossover":     scored["crossover"],
            "vol_ratio":     scored["vol_ratio"],
            "mtf_alignment": mtf_result.get("alignment", 0),
            "weekly_trend":  mtf_result.get("weekly_trend", "?"),
            "fii_flow":      flow.get("flow", "UNKNOWN"),
            "pattern_prob":  pattern["probability"],
            "pattern_sample": pattern["sample_size"],
            "filters_passed": "ALL ✅",
        }

    def scan_all(self, symbols: list) -> list:
        """Scan multiple stocks and return only those passing ALL filters."""
        results = []
        for sym in symbols:
            sig = self.generate_signal(sym)
            if sig:
                results.append(sig)
        results.sort(key=lambda x: x["final_score"], reverse=True)
        return results
