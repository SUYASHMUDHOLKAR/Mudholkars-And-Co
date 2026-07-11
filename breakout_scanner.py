"""
breakout_scanner.py
-------------------
Mudholkars & Co — 52-Week Breakout Scanner

Scans a list of NSE stocks for:
  1. 52-week HIGH breakouts  — price within 2% above 52-week high
     (momentum / strength signal)
  2. 52-week LOW bounce candidates — price within 5% above 52-week low
     (oversold reversal candidates)

Uses yfinance for all data (free, no API key required).
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class BreakoutScanner:
    """
    Scans NSE stocks for 52-week breakouts and oversold bounce setups.

    Usage:
        scanner = BreakoutScanner()
        results = scanner.scan(['RELIANCE', 'TCS', 'INFY', 'HDFCBANK'])

    Returns a list of dicts (one per qualifying stock).
    """

    # Price within this % above 52-week high → breakout
    BREAKOUT_WINDOW_PCT  = 2.0

    # Price within this % above 52-week low → oversold bounce candidate
    OVERSOLD_WINDOW_PCT  = 5.0

    def scan(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Screen each symbol for breakout / oversold signals.

        Args:
            symbols: List of NSE tickers WITHOUT .NS suffix,
                     e.g. ['RELIANCE', 'TCS', 'INFY']

        Returns:
            List of qualifying stocks sorted by signal type then breakout_pct.
            Each entry:
              {
                'symbol'      : 'RELIANCE',
                'price'       : 2945.60,
                'week52_high' : 2950.00,
                'week52_low'  : 2100.50,
                'breakout_pct': 0.15,       # % above 52-week high (negative = below)
                'signal'      : 'BREAKOUT'  # or 'OVERSOLD_BOUNCE'
              }
        """
        try:
            import yfinance as yf
        except ImportError:
            logger.error("yfinance not installed. pip install yfinance")
            return []

        if not symbols:
            return []

        results: List[Dict[str, Any]] = []

        # Batch download — faster than individual calls
        ns_symbols = [
            s if s.endswith(".NS") else f"{s}.NS"
            for s in symbols
        ]

        try:
            data = yf.download(
                ns_symbols,
                period="1y",
                interval="1d",
                progress=False,
                auto_adjust=True,
                group_by="ticker",
            )
        except Exception as e:
            logger.warning(f"BreakoutScanner batch download failed: {e}")
            # Fall back to individual downloads
            data = None

        for symbol, ns_sym in zip(symbols, ns_symbols):
            entry = self._check_one(symbol, ns_sym, data, yf)
            if entry:
                results.append(entry)

        # Sort: BREAKOUT first, then OVERSOLD_BOUNCE; within each by breakout_pct asc
        breakouts  = sorted(
            [r for r in results if r["signal"] == "BREAKOUT"],
            key=lambda x: x["breakout_pct"]
        )
        oversold   = sorted(
            [r for r in results if r["signal"] == "OVERSOLD_BOUNCE"],
            key=lambda x: x["breakout_pct"]
        )

        combined = breakouts + oversold

        logger.info(
            f"BreakoutScanner: {len(breakouts)} breakouts, "
            f"{len(oversold)} oversold bounce candidates "
            f"from {len(symbols)} symbols scanned"
        )
        return combined

    # ──────────────────────────────────────────────────────────────
    def _check_one(
        self,
        symbol: str,
        ns_sym: str,
        batch_data,
        yf,
    ) -> dict:
        """
        Check a single symbol.  Uses batch_data if available,
        otherwise falls back to individual yfinance download.
        """
        try:
            df = self._get_df(ns_sym, batch_data, yf)
            if df is None or df.empty or len(df) < 5:
                return None

            close_series = df["Close"].squeeze()
            high_series  = df["High"].squeeze()
            low_series   = df["Low"].squeeze()

            if close_series.empty:
                return None

            price      = float(close_series.iloc[-1])
            high_52w   = float(high_series.max())
            low_52w    = float(low_series.min())

            if price <= 0 or high_52w <= 0 or low_52w <= 0:
                return None

            # ── Breakout above 52-week high ───────────────────────
            breakout_pct = (price - high_52w) / high_52w * 100

            if breakout_pct >= -self.BREAKOUT_WINDOW_PCT:
                return {
                    "symbol"       : symbol,
                    "price"        : round(price, 2),
                    "week52_high"  : round(high_52w, 2),
                    "week52_low"   : round(low_52w, 2),
                    "breakout_pct" : round(breakout_pct, 2),
                    "signal"       : "BREAKOUT",
                }

            # ── Oversold bounce — near 52-week low ────────────────
            low_pct = (price - low_52w) / low_52w * 100

            if low_pct <= self.OVERSOLD_WINDOW_PCT:
                return {
                    "symbol"       : symbol,
                    "price"        : round(price, 2),
                    "week52_high"  : round(high_52w, 2),
                    "week52_low"   : round(low_52w, 2),
                    "breakout_pct" : round(low_pct, 2),   # distance from 52w low
                    "signal"       : "OVERSOLD_BOUNCE",
                }

        except Exception as e:
            logger.debug(f"BreakoutScanner [{symbol}]: {e}")

        return None

    def _get_df(self, ns_sym: str, batch_data, yf):
        """
        Extract a symbol's DataFrame from batch_data or download individually.
        """
        if batch_data is not None:
            try:
                import pandas as pd
                if isinstance(batch_data.columns, pd.MultiIndex):
                    # Multi-ticker batch download — columns are (field, ticker)
                    if ns_sym in batch_data.columns.get_level_values(1):
                        df = batch_data.xs(ns_sym, axis=1, level=1)
                        if not df.empty:
                            return df
                else:
                    # Single-ticker in batch (only one symbol passed)
                    if not batch_data.empty:
                        return batch_data
            except Exception:
                pass

        # Individual fallback
        try:
            df = yf.download(
                ns_sym,
                period="1y",
                interval="1d",
                progress=False,
                auto_adjust=True,
            )
            return df if not df.empty else None
        except Exception as e:
            logger.debug(f"BreakoutScanner individual download [{ns_sym}]: {e}")
            return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    symbols = [
        "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
        "WIPRO", "LT", "BAJFINANCE", "SBIN", "AXISBANK",
    ]
    scanner = BreakoutScanner()
    results = scanner.scan(symbols)
    if results:
        import json
        print(json.dumps(results, indent=2, default=str))
    else:
        print("No breakouts or oversold setups found in test batch.")
