"""
multi_timeframe.py
------------------
Multi-timeframe alignment filter for trade entry decisions.

Checks DAILY, WEEKLY, and MONTHLY signals to ensure all timeframes
agree before allowing a trade. Uses yfinance for market data.

Usage:
    from multi_timeframe import MultiTimeframeFilter
    
    mtf = MultiTimeframeFilter()
    result = mtf.check("RELIANCE.NS")
    if result["pass"]:
        # proceed with trade
        ...
"""

import logging
import numpy as np
import yfinance as yf

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class MultiTimeframeFilter:
    """
    Checks if DAILY + WEEKLY + MONTHLY timeframes all agree before allowing a trade.
    
    Decision Logic:
        - DAILY: RSI rising last 3 days + MACD above signal line + price above EMA20
        - WEEKLY: Price above 100-day MA (proxy for 20-week MA)
        - MONTHLY: Price not within 5% of 52-week high AND RSI < 75
        - Pass: all 3 bullish (agreement >= 3) OR at least 2 bullish with none bearish
    """

    def __init__(self):
        """Initialize the MultiTimeframeFilter."""
        logger.info("MultiTimeframeFilter initialized")

    def _calculate_rsi(self, prices, period=14):
        """
        Calculate RSI for a given price series.

        Args:
            prices: pandas Series of closing prices.
            period: RSI lookback period (default 14).

        Returns:
            pandas Series of RSI values.
        """
        delta = prices.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _calculate_ema(self, prices, period):
        """
        Calculate Exponential Moving Average.

        Args:
            prices: pandas Series of closing prices.
            period: EMA period.

        Returns:
            pandas Series of EMA values.
        """
        return prices.ewm(span=period, adjust=False).mean()

    def _calculate_macd(self, prices):
        """
        Calculate MACD and signal line.

        Args:
            prices: pandas Series of closing prices.

        Returns:
            Tuple of (macd_line, signal_line) as pandas Series.
        """
        ema12 = self._calculate_ema(prices, 12)
        ema26 = self._calculate_ema(prices, 26)
        macd_line = ema12 - ema26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        return macd_line, signal_line

    def _check_daily(self, hist):
        """
        Check daily timeframe signals.

        Logic:
            - RSI rising over last 3 days
            - MACD above signal line
            - Price above EMA20

        Args:
            hist: DataFrame with at least 30 days of daily OHLCV data.

        Returns:
            str: "BULL", "BEAR", or "NEUTRAL"
        """
        try:
            close = hist["Close"]

            # RSI direction (rising last 3 days)
            rsi = self._calculate_rsi(close)
            rsi_values = rsi.dropna().tail(3)
            rsi_rising = len(rsi_values) >= 3 and rsi_values.iloc[-1] > rsi_values.iloc[0]

            # MACD above signal line
            macd_line, signal_line = self._calculate_macd(close)
            macd_bullish = macd_line.iloc[-1] > signal_line.iloc[-1]

            # Price above EMA20
            ema20 = self._calculate_ema(close, 20)
            price_above_ema = close.iloc[-1] > ema20.iloc[-1]

            bullish_count = sum([rsi_rising, macd_bullish, price_above_ema])

            if bullish_count >= 2:
                return "BULL"
            elif bullish_count == 0:
                return "BEAR"
            else:
                return "NEUTRAL"

        except Exception as e:
            logger.warning(f"Daily check error: {e}")
            return "NEUTRAL"

    def _check_weekly(self, hist):
        """
        Check weekly timeframe signals.

        Logic:
            - Price above 100-day MA (proxy for 20-week MA)

        Args:
            hist: DataFrame with at least 100 days of daily OHLCV data.

        Returns:
            str: "BULL", "BEAR", or "NEUTRAL"
        """
        try:
            close = hist["Close"]

            if len(close) < 100:
                logger.warning("Insufficient data for weekly check, need 100+ days")
                return "NEUTRAL"

            ma100 = close.rolling(window=100).mean()
            current_price = close.iloc[-1]
            ma_value = ma100.iloc[-1]

            if np.isnan(ma_value):
                return "NEUTRAL"

            # Check how far price is from the MA
            distance_pct = ((current_price - ma_value) / ma_value) * 100

            if current_price > ma_value:
                return "BULL"
            elif distance_pct < -5:
                return "BEAR"
            else:
                return "NEUTRAL"

        except Exception as e:
            logger.warning(f"Weekly check error: {e}")
            return "NEUTRAL"

    def _check_monthly(self, hist):
        """
        Check monthly timeframe signals.

        Logic:
            - Price NOT within 5% of 52-week high (not overbought at top)
            - RSI < 75

        Args:
            hist: DataFrame with at least 250 days (1 year) of daily OHLCV data.

        Returns:
            str: "BULL", "BEAR", or "NEUTRAL"
        """
        try:
            close = hist["Close"]

            # 52-week high check (approximately 252 trading days)
            high_52w = close.tail(252).max()
            current_price = close.iloc[-1]
            distance_from_high = ((high_52w - current_price) / high_52w) * 100

            # Price within 5% of 52-week high = overbought
            near_high = distance_from_high < 5

            # RSI check
            rsi = self._calculate_rsi(close)
            current_rsi = rsi.iloc[-1]
            rsi_overbought = current_rsi >= 75

            if near_high or rsi_overbought:
                # Overbought - not a good monthly signal
                if near_high and rsi_overbought:
                    return "BEAR"
                return "NEUTRAL"
            else:
                # Not overbought and RSI healthy
                # Additional: check if price is trending up (above 200-day MA)
                if len(close) >= 200:
                    ma200 = close.rolling(window=200).mean().iloc[-1]
                    if current_price > ma200:
                        return "BULL"
                    elif current_price < ma200 * 0.9:
                        return "BEAR"
                    else:
                        return "NEUTRAL"
                return "BULL"

        except Exception as e:
            logger.warning(f"Monthly check error: {e}")
            return "NEUTRAL"

    def check(self, symbol: str) -> dict:
        """
        Check multi-timeframe alignment for a given symbol.

        Args:
            symbol: Stock ticker symbol (e.g., "RELIANCE.NS", "AAPL").

        Returns:
            dict with keys:
                - pass: bool — whether the trade is allowed
                - daily: str — "BULL", "BEAR", or "NEUTRAL"
                - weekly: str — "BULL", "BEAR", or "NEUTRAL"
                - monthly: str — "BULL", "BEAR", or "NEUTRAL"
                - agreement: int — 0 to 3 (number of bullish timeframes)
                - signal: str — text reason for the decision
        """
        try:
            logger.info(f"Checking multi-timeframe alignment for {symbol}")

            # Download 1 year of daily data (covers all timeframes)
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1y")

            if hist.empty or len(hist) < 30:
                logger.warning(f"Insufficient data for {symbol}, defaulting to pass")
                return {
                    "pass": True,
                    "daily": "NEUTRAL",
                    "weekly": "NEUTRAL",
                    "monthly": "NEUTRAL",
                    "agreement": 0,
                    "signal": f"Insufficient data for {symbol}, allowing trade by default"
                }

            # Check each timeframe
            daily = self._check_daily(hist)
            weekly = self._check_weekly(hist)
            monthly = self._check_monthly(hist)

            # Count agreement
            signals = [daily, weekly, monthly]
            bull_count = signals.count("BULL")
            bear_count = signals.count("BEAR")
            agreement = bull_count

            # Decision logic:
            # Pass = all 3 agree bullish (agreement >= 3)
            # OR at least 2 agree bullish with none bearish
            if agreement >= 3:
                passed = True
                signal = f"All timeframes BULLISH — strong alignment for {symbol}"
            elif agreement >= 2 and bear_count == 0:
                passed = True
                signal = f"2/3 timeframes BULLISH, none BEARISH — acceptable alignment for {symbol}"
            else:
                passed = False
                reasons = []
                if daily == "BEAR":
                    reasons.append("daily bearish")
                if weekly == "BEAR":
                    reasons.append("weekly bearish")
                if monthly == "BEAR":
                    reasons.append("monthly bearish")
                if bull_count < 2:
                    reasons.append(f"only {bull_count}/3 bullish")
                signal = f"Timeframe disagreement for {symbol}: {', '.join(reasons)}"

            result = {
                "pass": passed,
                "daily": daily,
                "weekly": weekly,
                "monthly": monthly,
                "agreement": agreement,
                "signal": signal
            }

            logger.info(f"{symbol} MTF result: pass={passed}, agreement={agreement}/3")
            return result

        except Exception as e:
            logger.error(f"Error checking {symbol}: {e}")
            return {
                "pass": True,
                "daily": "NEUTRAL",
                "weekly": "NEUTRAL",
                "monthly": "NEUTRAL",
                "agreement": 0,
                "signal": f"Error checking {symbol}: {e}. Allowing trade by default."
            }

    def check_batch(self, symbols: list) -> dict:
        """
        Check multi-timeframe alignment for multiple symbols.

        Args:
            symbols: List of stock ticker symbols.

        Returns:
            dict mapping each symbol to its check result.
        """
        results = {}
        for symbol in symbols:
            try:
                results[symbol] = self.check(symbol)
            except Exception as e:
                logger.error(f"Batch check error for {symbol}: {e}")
                results[symbol] = {
                    "pass": True,
                    "daily": "NEUTRAL",
                    "weekly": "NEUTRAL",
                    "monthly": "NEUTRAL",
                    "agreement": 0,
                    "signal": f"Error: {e}. Allowing trade by default."
                }
        return results


if __name__ == "__main__":
    # Example usage
    mtf = MultiTimeframeFilter()

    # Single check
    result = mtf.check("RELIANCE.NS")
    print(f"\nSingle check result:")
    for k, v in result.items():
        print(f"  {k}: {v}")

    # Batch check
    symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]
    batch_results = mtf.check_batch(symbols)
    print(f"\nBatch results:")
    for sym, res in batch_results.items():
        print(f"  {sym}: pass={res['pass']}, agreement={res['agreement']}/3")
