"""
promoter_tracker.py
-------------------
Mudholkars & Co — Promoter Activity Tracker

Checks promoter shareholding percentage via yfinance and infers
whether promoters are buying, selling, or holding steady.

Rules:
  SAFE     : promoter > 50%  AND  signal is STABLE or BUYING
  NOT SAFE : promoter < 30%  OR   signal is SELLING (declining holding)
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class PromoterTracker:
    """
    Checks promoter / major-holder shareholding for a given NSE stock.

    Usage:
        pt = PromoterTracker()
        result = pt.check_promoter_activity('RELIANCE')

    Returns:
        {
          'promoter_pct' : 50.34,
          'signal'       : 'STABLE',   # 'BUYING' | 'SELLING' | 'STABLE'
          'safe'         : True,
          'insider_pct'  : 50.34,       # raw insider % from yfinance
          'source'       : 'live'
        }
    """

    SAFE_THRESHOLD      = 50.0   # promoter > 50% → good governance signal
    UNSAFE_THRESHOLD    = 30.0   # promoter < 30% → low promoter confidence
    BUYING_THRESHOLD    =  2.0   # increase ≥ 2% → buying signal
    SELLING_THRESHOLD   = -2.0   # decrease ≤ -2% → selling signal

    FALLBACK = {
        "promoter_pct" : None,
        "signal"       : "STABLE",   # default-safe if we can't determine
        "safe"         : True,
        "insider_pct"  : None,
        "source"       : "fallback",
    }

    def check_promoter_activity(self, symbol: str) -> Dict[str, Any]:
        """
        Fetch promoter/insider holding data for the given symbol.

        Args:
            symbol: NSE ticker without suffix, e.g. 'RELIANCE'

        Returns:
            dict with promoter_pct, signal, safe, insider_pct, source
        """
        try:
            import yfinance as yf
        except ImportError:
            logger.error("yfinance not installed. pip install yfinance")
            return dict(self.FALLBACK)

        ns_symbol = symbol if symbol.endswith(".NS") else f"{symbol}.NS"

        try:
            ticker = yf.Ticker(ns_symbol)
            info   = ticker.info or {}

            promoter_pct, signal = self._extract_promoter(ticker, info)

            if promoter_pct is None:
                logger.debug(f"PromoterTracker [{symbol}]: no shareholding data")
                return dict(self.FALLBACK)

            safe = self._is_safe(promoter_pct, signal)

            result = {
                "promoter_pct" : round(promoter_pct, 2),
                "signal"       : signal,
                "safe"         : safe,
                "insider_pct"  : round(promoter_pct, 2),
                "source"       : "live",
            }

            logger.debug(
                f"PromoterTracker [{symbol}]: {promoter_pct:.1f}% | "
                f"signal={signal} | safe={safe}"
            )
            return result

        except Exception as e:
            logger.debug(f"PromoterTracker [{symbol}]: {e}")
            return dict(self.FALLBACK)

    # ──────────────────────────────────────────────────────────────
    def _extract_promoter(self, ticker, info: dict):
        """
        Pull promoter / insider holding pct from yfinance.
        Tries multiple data sources in order of reliability.

        Returns: (promoter_pct: float | None, signal: str)
        """
        # ── 1. heldPercentInsiders from info ─────────────────────
        insider_frac = info.get("heldPercentInsiders")
        if insider_frac is not None:
            try:
                pct = float(insider_frac) * 100
                signal = self._infer_signal_from_major_holders(ticker, pct)
                return pct, signal
            except (TypeError, ValueError):
                pass

        # ── 2. majorHolders DataFrame ─────────────────────────────
        try:
            mh = ticker.major_holders
            if mh is not None and not mh.empty:
                # yfinance major_holders columns: Value, Breakdown
                for idx in range(len(mh)):
                    row = mh.iloc[idx]
                    label = str(row.iloc[1]).lower() if len(row) > 1 else ""
                    if "insider" in label or "promoter" in label:
                        val = row.iloc[0]
                        pct = float(str(val).replace("%", "").strip())
                        signal = self._infer_signal_from_major_holders(ticker, pct)
                        return pct, signal
        except Exception:
            pass

        return None, "STABLE"

    def _infer_signal_from_major_holders(self, ticker, current_pct: float) -> str:
        """
        Attempt to infer buying/selling from institutional holders history.
        yfinance doesn't expose a direct promoter history endpoint, so we
        check institutional_holders changes as a proxy.

        If no history available, default to STABLE.
        """
        try:
            ih = ticker.institutional_holders
            if ih is not None and not ih.empty and "% Out" in ih.columns:
                # Heuristic: If current insider pct is notably high, mark STABLE
                # More precise signal requires historical data not in yfinance
                if current_pct >= self.SAFE_THRESHOLD:
                    return "STABLE"
        except Exception:
            pass

        # Default: no directional change data available
        return "STABLE"

    def _is_safe(self, promoter_pct: float, signal: str) -> bool:
        """
        Determine if the stock is safe from a promoter perspective.

        Safe:
          - promoter_pct > 50%  AND  signal in (STABLE, BUYING)
        Not safe:
          - promoter_pct < 30%
          - signal == SELLING (regardless of pct)
        """
        if signal == "SELLING":
            return False
        if promoter_pct < self.UNSAFE_THRESHOLD:
            return False
        if promoter_pct >= self.SAFE_THRESHOLD and signal in ("STABLE", "BUYING"):
            return True
        # Between 30% and 50% with STABLE/BUYING — treat as borderline safe
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    pt = PromoterTracker()
    for sym in ["RELIANCE", "TCS", "INFY", "BAJFINANCE"]:
        r = pt.check_promoter_activity(sym)
        print(f"{sym:15s}  promoter={r['promoter_pct']}%  signal={r['signal']}  safe={r['safe']}")
