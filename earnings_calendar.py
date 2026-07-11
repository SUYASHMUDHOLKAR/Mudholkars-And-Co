"""
earnings_calendar.py
--------------------
Mudholkars & Co — Earnings Calendar

Checks upcoming earnings/results dates for NSE stocks via yfinance.
Flags stocks where results are within 5 days as unsafe to trade
(to avoid earnings surprise risk).
"""

import logging
from datetime import date, datetime, timedelta
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class EarningsCalendar:
    """
    Looks up upcoming earnings dates for a list of NSE symbols.

    Usage:
        cal = EarningsCalendar()
        result = cal.get_upcoming_results(['RELIANCE', 'TCS', 'INFY'])

    Returns:
        {
          'RELIANCE': {'days_to_results': 12, 'safe_to_trade': True,  'earnings_date': '2026-07-23'},
          'TCS':      {'days_to_results':  3, 'safe_to_trade': False, 'earnings_date': '2026-07-14'},
          ...
        }
    """

    # Stocks with results ≤ this many days away are unsafe
    SAFE_WINDOW_DAYS = 5

    # Fallback for a single symbol when data is unavailable
    FALLBACK_ENTRY = {
        "days_to_results": None,
        "safe_to_trade"  : True,   # default-safe if we cannot determine
        "earnings_date"  : None,
        "source"         : "fallback",
    }

    def get_upcoming_results(
        self, symbols: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch upcoming earnings dates for each symbol.

        Args:
            symbols: List of NSE ticker symbols WITHOUT the .NS suffix,
                     e.g. ['RELIANCE', 'TCS', 'HDFCBANK']

        Returns:
            Dict keyed by symbol with earnings proximity info.
        """
        try:
            import yfinance as yf
        except ImportError:
            logger.error("yfinance not installed. pip install yfinance")
            return {s: dict(self.FALLBACK_ENTRY) for s in symbols}

        today = date.today()
        results: Dict[str, Dict[str, Any]] = {}

        for symbol in symbols:
            results[symbol] = self._check_symbol(yf, symbol, today)

        # Summary log
        unsafe = [s for s, v in results.items() if not v["safe_to_trade"]]
        if unsafe:
            logger.info(
                f"EarningsCalendar: {len(unsafe)} stocks near results: {unsafe[:10]}"
            )
        else:
            logger.debug(f"EarningsCalendar: all {len(symbols)} symbols clear of results")

        return results

    # ──────────────────────────────────────────────────────────────
    def _check_symbol(
        self, yf, symbol: str, today: date
    ) -> Dict[str, Any]:
        """
        Check a single symbol's earnings date via yfinance Ticker.calendar.
        Returns a safe fallback dict on any error.
        """
        ns_symbol = symbol if symbol.endswith(".NS") else f"{symbol}.NS"
        try:
            ticker  = yf.Ticker(ns_symbol)
            cal     = ticker.calendar          # dict or DataFrame depending on yf version

            earnings_date = self._extract_earnings_date(cal)

            if earnings_date is None:
                return dict(self.FALLBACK_ENTRY)

            # Normalise to date object
            if isinstance(earnings_date, datetime):
                earnings_date = earnings_date.date()

            days_to = (earnings_date - today).days

            # Past earnings — treat as safe (result already announced)
            if days_to < 0:
                return {
                    "days_to_results": days_to,
                    "safe_to_trade"  : True,
                    "earnings_date"  : str(earnings_date),
                    "source"         : "live",
                }

            safe = days_to > self.SAFE_WINDOW_DAYS

            return {
                "days_to_results": days_to,
                "safe_to_trade"  : safe,
                "earnings_date"  : str(earnings_date),
                "source"         : "live",
            }

        except Exception as e:
            logger.debug(f"EarningsCalendar [{symbol}]: {e}")
            return dict(self.FALLBACK_ENTRY)

    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _extract_earnings_date(cal) -> Any:
        """
        yfinance returns calendar in different formats across versions.
        This handles dict, DataFrame, and None gracefully.
        """
        if cal is None:
            return None

        # ── Dict format (yfinance ≥ 0.2.x) ───────────────────────
        if isinstance(cal, dict):
            for key in ("Earnings Date", "earnings_date", "earningsDate"):
                val = cal.get(key)
                if val is not None:
                    # May be a list or scalar
                    if isinstance(val, (list, tuple)) and len(val) > 0:
                        return val[0]
                    return val
            return None

        # ── DataFrame format (older yfinance) ─────────────────────
        try:
            import pandas as pd
            if isinstance(cal, pd.DataFrame) and not cal.empty:
                for row_label in ("Earnings Date", "Earnings High", "Earnings Low"):
                    if row_label in cal.index:
                        val = cal.loc[row_label].iloc[0]
                        if pd.notna(val):
                            return val
        except Exception:
            pass

        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    test_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "WIPRO"]
    cal = EarningsCalendar()
    res = cal.get_upcoming_results(test_symbols)
    import json
    print(json.dumps(res, indent=2, default=str))
