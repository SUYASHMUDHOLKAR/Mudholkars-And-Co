"""
premarket_scanner.py
--------------------
Pre-market scanner that analyzes global market signals before Indian market opens.

Checks US markets, Asian markets, commodities, currency, and VIX to determine
market bias and recommend trading mode (AGGRESSIVE / NORMAL / DEFENSIVE).

Designed to run at 9:00 AM IST before Indian market opens at 9:15 AM.

Usage:
    from premarket_scanner import PreMarketScanner
    
    scanner = PreMarketScanner()
    result = scanner.scan()
    print(result["mode"])  # "AGGRESSIVE", "NORMAL", or "DEFENSIVE"
    print(result["bias"])  # "BULLISH", "BEARISH", or "NEUTRAL"
"""

import logging
from datetime import datetime, timedelta

import numpy as np
import yfinance as yf

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class PreMarketScanner:
    """
    Pre-market scanner that analyzes global signals before Indian market opens.

    Checks:
        - US Markets: S&P 500, Nasdaq
        - Asian Markets: Nikkei 225, Hang Seng
        - Commodities: Crude Oil, Gold
        - Currency: USD/INR
        - Volatility: India VIX

    Decision:
        - 5+ positive signals → AGGRESSIVE mode (lower threshold by 5)
        - 3-4 positive signals → NORMAL mode
        - 0-2 positive signals → DEFENSIVE mode (raise threshold by 5)
    """

    # Global market indicators to check
    INDICATORS = {
        "sp500": {"symbol": "^GSPC", "name": "S&P 500", "type": "us"},
        "nasdaq": {"symbol": "^IXIC", "name": "Nasdaq", "type": "us"},
        "nikkei": {"symbol": "^N225", "name": "Nikkei 225", "type": "asia"},
        "hangseng": {"symbol": "^HSI", "name": "Hang Seng", "type": "asia"},
        "crude": {"symbol": "CL=F", "name": "Crude Oil", "type": "commodity"},
        "gold": {"symbol": "GC=F", "name": "Gold", "type": "commodity"},
        "usdinr": {"symbol": "USDINR=X", "name": "USD/INR", "type": "currency"},
        "indiavix": {"symbol": "^INDIAVIX", "name": "India VIX", "type": "volatility"},
    }

    def __init__(self):
        """Initialize the PreMarketScanner."""
        logger.info("PreMarketScanner initialized")

    def _get_change_pct(self, symbol: str) -> float:
        """
        Get percentage change for a given symbol (last close vs previous close).

        Args:
            symbol: Ticker symbol.

        Returns:
            float: Percentage change, or 0.0 if data unavailable.
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5d")

            if hist.empty or len(hist) < 2:
                logger.warning(f"Insufficient data for {symbol}")
                return 0.0

            current = hist["Close"].iloc[-1]
            previous = hist["Close"].iloc[-2]

            if previous == 0:
                return 0.0

            change_pct = ((current - previous) / previous) * 100
            return round(change_pct, 2)

        except Exception as e:
            logger.warning(f"Error fetching {symbol}: {e}")
            return 0.0

    def _get_vix_level(self) -> float:
        """
        Get the current India VIX level.

        Returns:
            float: VIX level, or 15.0 (neutral default) if unavailable.
        """
        try:
            ticker = yf.Ticker("^INDIAVIX")
            hist = ticker.history(period="5d")

            if hist.empty:
                return 15.0

            return round(hist["Close"].iloc[-1], 2)

        except Exception as e:
            logger.warning(f"Error fetching India VIX: {e}")
            return 15.0

    def _is_positive_signal(self, key: str, change_pct: float, vix_level: float = None) -> bool:
        """
        Determine if a market signal is positive for Indian markets.

        Args:
            key: Indicator key (e.g., "sp500", "crude").
            change_pct: Percentage change.
            vix_level: VIX level (only used for VIX indicator).

        Returns:
            bool: True if the signal is positive.
        """
        # USD/INR: falling rupee is negative for markets
        if key == "usdinr":
            return change_pct < 0  # Rupee strengthening is positive

        # India VIX: low VIX is positive, high VIX is negative
        if key == "indiavix":
            if vix_level is not None:
                return vix_level < 18  # VIX below 18 is positive
            return change_pct < 0  # Falling VIX is positive

        # For everything else: positive change = positive signal
        return change_pct > 0

    def _find_gap_candidates(self, watchlist: list = None) -> list:
        """
        Identify stocks with >2% gap-up or gap-down from previous close.

        Args:
            watchlist: List of symbols to check. Defaults to Nifty 50 constituents.

        Returns:
            list of dicts with gap candidate information.
        """
        if watchlist is None:
            # Default watchlist - major Nifty stocks
            watchlist = [
                "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS",
                "ICICIBANK.NS", "HINDUNILVR.NS", "ITC.NS", "SBIN.NS",
                "BHARTIARTL.NS", "KOTAKBANK.NS", "LT.NS", "AXISBANK.NS",
                "BAJFINANCE.NS", "MARUTI.NS", "TITAN.NS", "WIPRO.NS",
                "ADANIENT.NS", "TATAMOTORS.NS", "TATASTEEL.NS", "SUNPHARMA.NS"
            ]

        gap_candidates = []

        for symbol in watchlist:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="5d")

                if hist.empty or len(hist) < 2:
                    continue

                prev_close = hist["Close"].iloc[-2]
                last_close = hist["Close"].iloc[-1]

                if prev_close == 0:
                    continue

                gap_pct = ((last_close - prev_close) / prev_close) * 100

                if abs(gap_pct) > 2:
                    gap_candidates.append({
                        "symbol": symbol,
                        "gap_pct": round(gap_pct, 2),
                        "direction": "UP" if gap_pct > 0 else "DOWN",
                        "prev_close": round(prev_close, 2),
                        "last_price": round(last_close, 2)
                    })

            except Exception as e:
                logger.debug(f"Error checking gap for {symbol}: {e}")
                continue

        # Sort by absolute gap percentage
        gap_candidates.sort(key=lambda x: abs(x["gap_pct"]), reverse=True)
        return gap_candidates

    def scan(self, watchlist: list = None) -> dict:
        """
        Run the pre-market scan and return market bias with trading mode.

        Args:
            watchlist: Optional list of symbols for gap scanning.

        Returns:
            dict with keys:
                - mode: str — "AGGRESSIVE", "NORMAL", or "DEFENSIVE"
                - bias: str — "BULLISH", "BEARISH", or "NEUTRAL"
                - us_market: float — US market change %
                - asia: float — Asian market change %
                - crude: float — Crude oil change %
                - gold: float — Gold change %
                - vix: float — India VIX level
                - threshold_adjustment: int — adjustment to trading score threshold
                - summary: str — human-readable summary
                - gap_candidates: list — stocks with >2% gaps
                - signals: dict — detailed signal breakdown
        """
        try:
            logger.info("Starting pre-market scan...")

            # Collect all market signals
            signals = {}
            changes = {}

            for key, info in self.INDICATORS.items():
                change = self._get_change_pct(info["symbol"])
                changes[key] = change
                logger.info(f"  {info['name']}: {change:+.2f}%")

            # Get VIX level separately
            vix_level = self._get_vix_level()
            logger.info(f"  India VIX level: {vix_level}")

            # Determine positive/negative signals
            positive_count = 0
            negative_count = 0
            signal_details = {}

            for key, change in changes.items():
                if key == "indiavix":
                    is_positive = self._is_positive_signal(key, change, vix_level)
                else:
                    is_positive = self._is_positive_signal(key, change)

                signal_details[key] = {
                    "name": self.INDICATORS[key]["name"],
                    "change_pct": change,
                    "positive": is_positive
                }

                if is_positive:
                    positive_count += 1
                else:
                    negative_count += 1

            # Determine mode and bias
            if positive_count >= 5:
                mode = "AGGRESSIVE"
                threshold_adjustment = -5
                bias = "BULLISH"
            elif positive_count >= 3:
                mode = "NORMAL"
                threshold_adjustment = 0
                if positive_count >= 4:
                    bias = "BULLISH"
                else:
                    bias = "NEUTRAL"
            else:
                mode = "DEFENSIVE"
                threshold_adjustment = 5
                bias = "BEARISH"

            # Calculate aggregated market metrics
            us_market = round((changes.get("sp500", 0) + changes.get("nasdaq", 0)) / 2, 2)
            asia = round((changes.get("nikkei", 0) + changes.get("hangseng", 0)) / 2, 2)
            crude = changes.get("crude", 0)
            gold = changes.get("gold", 0)

            # Find gap candidates
            gap_candidates = self._find_gap_candidates(watchlist)

            # Build summary
            summary_parts = [
                f"Mode: {mode} | Bias: {bias}",
                f"US: {us_market:+.2f}% | Asia: {asia:+.2f}%",
                f"Crude: {crude:+.2f}% | Gold: {gold:+.2f}%",
                f"VIX: {vix_level} | Signals: {positive_count}/8 positive",
            ]
            if gap_candidates:
                gap_str = ", ".join([f"{g['symbol']}({g['gap_pct']:+.1f}%)" for g in gap_candidates[:5]])
                summary_parts.append(f"Gaps: {gap_str}")

            summary = " | ".join(summary_parts)

            result = {
                "mode": mode,
                "bias": bias,
                "us_market": us_market,
                "asia": asia,
                "crude": crude,
                "gold": gold,
                "vix": vix_level,
                "threshold_adjustment": threshold_adjustment,
                "summary": summary,
                "gap_candidates": gap_candidates,
                "signals": signal_details,
                "positive_signals": positive_count,
                "negative_signals": negative_count,
                "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            logger.info(f"Pre-market scan complete: mode={mode}, bias={bias}, "
                       f"signals={positive_count}/8 positive")
            return result

        except Exception as e:
            logger.error(f"Pre-market scan error: {e}")
            return {
                "mode": "NORMAL",
                "bias": "NEUTRAL",
                "us_market": 0.0,
                "asia": 0.0,
                "crude": 0.0,
                "gold": 0.0,
                "vix": 15.0,
                "threshold_adjustment": 0,
                "summary": f"Scan failed: {e}. Using neutral defaults.",
                "gap_candidates": [],
                "signals": {},
                "positive_signals": 0,
                "negative_signals": 0,
                "scan_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }


if __name__ == "__main__":
    # Example usage
    print("=" * 70)
    print("Pre-Market Scanner")
    print(f"Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    scanner = PreMarketScanner()
    result = scanner.scan()

    print(f"\n{'─' * 70}")
    print(f"  MODE: {result['mode']}")
    print(f"  BIAS: {result['bias']}")
    print(f"{'─' * 70}")
    print(f"  US Markets:  {result['us_market']:+.2f}%")
    print(f"  Asia:        {result['asia']:+.2f}%")
    print(f"  Crude Oil:   {result['crude']:+.2f}%")
    print(f"  Gold:        {result['gold']:+.2f}%")
    print(f"  India VIX:   {result['vix']}")
    print(f"  Threshold:   {result['threshold_adjustment']:+d}")
    print(f"{'─' * 70}")

    if result.get("gap_candidates"):
        print(f"\n  Gap Candidates (>{2}% move):")
        for gap in result["gap_candidates"][:10]:
            print(f"    {gap['symbol']:>15s}: {gap['gap_pct']:+.2f}% "
                  f"({gap['direction']}) → {gap['last_price']}")
    else:
        print("\n  No significant gap candidates found.")

    print(f"\n{'─' * 70}")
    print(f"  Summary: {result['summary']}")
    print(f"{'─' * 70}")
