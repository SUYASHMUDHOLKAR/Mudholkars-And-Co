"""
market_regime.py
----------------
Mudholkars & Co — Market Regime Detector

Determines the current market regime (BULL/BEAR/SIDEWAYS) using:
  - Nifty50 vs 20MA, 50MA, 200MA
  - VIX level (^INDIAVIX)
  - Up/Down day count over last 20 trading sessions

Returns regime context used to calibrate trade aggression and
minimum consensus score thresholds across the pipeline.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class MarketRegimeDetector:
    """
    Detects market regime for NSE/Nifty50.

    Returns a dict with:
        regime          : 'BULL' | 'BEAR' | 'SIDEWAYS'
        score           : 0-100  (bull=high, bear=low)
        aggression      : 'HIGH' | 'MEDIUM' | 'LOW'
        min_score_override : int  (consensus threshold to use)
        vix             : float
        nifty_price     : float
        above_20ma      : bool
        above_50ma      : bool
        above_200ma     : bool
        up_days         : int (last 20 sessions)
        down_days       : int (last 20 sessions)
    """

    NIFTY_TICKER  = "^NSEI"
    VIX_TICKER    = "^INDIAVIX"
    LOOKBACK_DAYS = 250          # enough for 200MA + 20 recent days
    RECENT_DAYS   = 20           # window for up/down count

    # Regime thresholds
    BULL_VIX_MAX  = 15.0
    BEAR_VIX_MIN  = 20.0

    # Minimum consensus-score overrides per regime
    BULL_MIN_SCORE      = 62
    SIDEWAYS_MIN_SCORE  = 68
    BEAR_MIN_SCORE      = 78

    # ── Fallback when data is unavailable ──────────────────────────
    FALLBACK = {
        "regime"            : "SIDEWAYS",
        "score"             : 50,
        "aggression"        : "MEDIUM",
        "min_score_override": 68,
        "vix"               : None,
        "nifty_price"       : None,
        "above_20ma"        : None,
        "above_50ma"        : None,
        "above_200ma"       : None,
        "up_days"           : None,
        "down_days"         : None,
        "source"            : "fallback",
    }

    def detect(self) -> Dict[str, Any]:
        """
        Fetch live Nifty & VIX data and classify the current regime.

        Returns:
            dict with regime, score, aggression, min_score_override,
            and supporting data fields.
        """
        try:
            import yfinance as yf
            import pandas as pd
        except ImportError:
            logger.error("yfinance not installed. pip install yfinance")
            return dict(self.FALLBACK)

        # ── Download Nifty50 history ──────────────────────────────
        try:
            nifty_df = yf.download(
                self.NIFTY_TICKER,
                period="1y",
                interval="1d",
                progress=False,
                auto_adjust=True,
            )
            if nifty_df.empty or len(nifty_df) < 22:
                logger.warning("Nifty data insufficient; using fallback")
                return dict(self.FALLBACK)

            close = nifty_df["Close"].squeeze()
        except Exception as e:
            logger.warning(f"Nifty download failed: {e}")
            return dict(self.FALLBACK)

        # ── Moving averages ───────────────────────────────────────
        try:
            ma20  = float(close.rolling(20).mean().iloc[-1])
            ma50  = float(close.rolling(50).mean().iloc[-1])
            ma200 = float(close.rolling(200).mean().iloc[-1])
            nifty_price = float(close.iloc[-1])
        except Exception as e:
            logger.warning(f"MA calculation failed: {e}")
            return dict(self.FALLBACK)

        above_20ma  = nifty_price > ma20
        above_50ma  = nifty_price > ma50
        above_200ma = nifty_price > ma200

        # ── VIX ───────────────────────────────────────────────────
        vix = None
        try:
            vix_df = yf.download(
                self.VIX_TICKER,
                period="5d",
                interval="1d",
                progress=False,
                auto_adjust=True,
            )
            if not vix_df.empty:
                vix = float(vix_df["Close"].squeeze().iloc[-1])
        except Exception as e:
            logger.warning(f"VIX download failed: {e}")

        # ── Up / Down day count (last 20 sessions) ────────────────
        recent_close = close.iloc[-self.RECENT_DAYS :]
        daily_changes = recent_close.diff().iloc[1:]          # drop NaN first row
        up_days   = int((daily_changes > 0).sum())
        down_days = int((daily_changes < 0).sum())

        # ── Regime classification ─────────────────────────────────
        regime, aggression, min_score, score = self._classify(
            above_20ma, above_50ma, above_200ma, vix, up_days, down_days
        )

        result = {
            "regime"            : regime,
            "score"             : score,
            "aggression"        : aggression,
            "min_score_override": min_score,
            "vix"               : round(vix, 2) if vix is not None else None,
            "nifty_price"       : round(nifty_price, 2),
            "ma20"              : round(ma20, 2),
            "ma50"              : round(ma50, 2),
            "ma200"             : round(ma200, 2),
            "above_20ma"        : above_20ma,
            "above_50ma"        : above_50ma,
            "above_200ma"       : above_200ma,
            "up_days"           : up_days,
            "down_days"         : down_days,
            "source"            : "live",
        }

        logger.info(
            f"MarketRegime: {regime} | VIX={vix} | Nifty={nifty_price:.0f} "
            f"| 20MA↑={above_20ma} 50MA↑={above_50ma} 200MA↑={above_200ma} "
            f"| up={up_days} down={down_days} | aggression={aggression}"
        )
        return result

    # ──────────────────────────────────────────────────────────────
    def _classify(
        self,
        above_20ma: bool,
        above_50ma: bool,
        above_200ma: bool,
        vix,
        up_days: int,
        down_days: int,
    ):
        """
        Core regime logic.

        Priority order:
          1. BEAR  — below 50MA  AND  VIX ≥ 20
          2. BULL  — above all 3 MAs  AND  VIX < 15
          3. SIDEWAYS — everything else

        Score is derived from MA alignment + VIX + momentum.
        """
        mas_score = (
            (25 if above_20ma  else 0) +
            (30 if above_50ma  else 0) +
            (20 if above_200ma else 0)
        )  # max 75 from MAs

        momentum_score = min(25, max(0, int((up_days - down_days) / self.RECENT_DAYS * 50 + 12.5)))

        raw_score = mas_score + momentum_score  # 0–100

        # VIX adjustment: high VIX penalises, low VIX rewards
        if vix is not None:
            if vix > 25:
                raw_score = max(0, raw_score - 15)
            elif vix > 20:
                raw_score = max(0, raw_score - 8)
            elif vix < 12:
                raw_score = min(100, raw_score + 8)
            elif vix < 15:
                raw_score = min(100, raw_score + 4)

        # ── BEAR ──────────────────────────────────────────────────
        if not above_50ma and (vix is None or vix >= self.BEAR_VIX_MIN):
            return "BEAR", "LOW", self.BEAR_MIN_SCORE, min(35, raw_score)

        # ── Strong bear without VIX confirmation ──────────────────
        if not above_50ma and not above_200ma and down_days > up_days + 5:
            return "BEAR", "LOW", self.BEAR_MIN_SCORE, min(38, raw_score)

        # ── BULL ──────────────────────────────────────────────────
        if above_20ma and above_50ma and above_200ma and (vix is None or vix < self.BULL_VIX_MAX):
            return "BULL", "HIGH", self.BULL_MIN_SCORE, max(65, raw_score)

        # ── Mild bull (all MAs aligned but VIX elevated) ──────────
        if above_20ma and above_50ma and above_200ma:
            return "SIDEWAYS", "MEDIUM", self.SIDEWAYS_MIN_SCORE, max(55, raw_score)

        # ── SIDEWAYS default ──────────────────────────────────────
        return "SIDEWAYS", "MEDIUM", self.SIDEWAYS_MIN_SCORE, max(40, min(65, raw_score))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    r = MarketRegimeDetector().detect()
    import json
    print(json.dumps(r, indent=2, default=str))
