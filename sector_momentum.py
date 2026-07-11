"""
sector_momentum.py
------------------
Mudholkars & Co — Sector Momentum Scorer

Calculates 20-day price momentum for 8 key Indian market sectors
using representative NSE stocks via yfinance.

Top 3 sectors by momentum  → 'BUY'
Bottom 3 sectors           → 'AVOID'
Middle 2 sectors           → 'NEUTRAL'
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


# ── Sector → representative NSE stocks (2-3 per sector is enough) ─────────
SECTOR_STOCKS: Dict[str, List[str]] = {
    "Banking & Finance" : ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS",   "AXISBANK.NS"],
    "IT & Technology"   : ["TCS.NS",      "INFY.NS",      "WIPRO.NS",  "HCLTECH.NS"],
    "Energy & Oil"      : ["RELIANCE.NS",  "ONGC.NS",      "BPCL.NS"],
    "FMCG & Consumer"   : ["HINDUNILVR.NS","ITC.NS",       "NESTLEIND.NS"],
    "Auto & EV"         : ["TATAMOTORS.NS","MARUTI.NS",    "BAJAJ-AUTO.NS", "HEROMOTOCO.NS"],
    "Pharma & Healthcare": ["SUNPHARMA.NS","DRREDDY.NS",   "CIPLA.NS",  "DIVISLAB.NS"],
    "Metals & Mining"   : ["TATASTEEL.NS", "JSWSTEEL.NS",  "HINDALCO.NS","COALINDIA.NS"],
    "Infra & Capital Goods": ["LT.NS",     "ABB.NS",       "SIEMENS.NS","BHEL.NS"],
}


class SectorMomentumScorer:
    """
    Ranks Indian market sectors by 20-day price momentum.

    Usage:
        scorer = SectorMomentumScorer()
        sectors = scorer.get_top_sectors()

    Returns:
        [
          {'sector': 'IT & Technology', 'momentum': 5.32, 'rank': 1, 'signal': 'BUY'},
          {'sector': 'Banking & Finance', 'momentum': 3.10, 'rank': 2, 'signal': 'BUY'},
          ...
          {'sector': 'Metals & Mining', 'momentum': -2.45, 'rank': 8, 'signal': 'AVOID'},
        ]
    """

    LOOKBACK_DAYS    = 30     # days of history to fetch (need 20+ trading days)
    MOMENTUM_DAYS    = 20     # rolling window for momentum calculation
    BUY_TOP_N        = 3      # top N sectors = BUY
    AVOID_BOTTOM_N   = 3      # bottom N sectors = AVOID

    def get_top_sectors(self) -> List[Dict[str, Any]]:
        """
        Calculate 20-day momentum for each sector and return a ranked list.

        Returns:
            List of sector dicts sorted by rank (1 = highest momentum).
            Each dict:
              sector   : str
              momentum : float   (% change over 20 days, average across sector stocks)
              rank     : int     (1 = best)
              signal   : 'BUY' | 'NEUTRAL' | 'AVOID'
        """
        try:
            import yfinance as yf
        except ImportError:
            logger.error("yfinance not installed. pip install yfinance")
            return self._fallback_result()

        # Collect all unique tickers across sectors
        all_tickers = list({
            t for tickers in SECTOR_STOCKS.values() for t in tickers
        })

        prices = self._download_prices(yf, all_tickers)

        if prices is None or prices.empty:
            logger.warning("SectorMomentumScorer: price data unavailable; using fallback")
            return self._fallback_result()

        # ── Compute sector-level momentum ─────────────────────────
        sector_scores: Dict[str, float] = {}

        for sector, tickers in SECTOR_STOCKS.items():
            momentums = []
            for ticker in tickers:
                m = self._ticker_momentum(prices, ticker)
                if m is not None:
                    momentums.append(m)

            if momentums:
                sector_scores[sector] = round(sum(momentums) / len(momentums), 4)
            else:
                logger.debug(f"SectorMomentum [{sector}]: no data — assigned 0")
                sector_scores[sector] = 0.0

        # ── Rank sectors ──────────────────────────────────────────
        ranked = sorted(sector_scores.items(), key=lambda x: x[1], reverse=True)
        n = len(ranked)

        result = []
        for i, (sector, momentum) in enumerate(ranked):
            rank = i + 1
            if rank <= self.BUY_TOP_N:
                signal = "BUY"
            elif rank > n - self.AVOID_BOTTOM_N:
                signal = "AVOID"
            else:
                signal = "NEUTRAL"

            result.append({
                "sector"  : sector,
                "momentum": round(momentum, 2),
                "rank"    : rank,
                "signal"  : signal,
            })

        logger.info(
            f"SectorMomentum: top3={[r['sector'] for r in result[:3]]} | "
            f"bottom3={[r['sector'] for r in result[-3:]]}"
        )
        return result

    # ──────────────────────────────────────────────────────────────
    def _download_prices(self, yf, tickers: List[str]):
        """
        Download closing prices for all tickers in one batch call.
        Returns a DataFrame of Close prices (columns = tickers).
        Falls back to None on failure.
        """
        try:
            import pandas as pd

            raw = yf.download(
                tickers,
                period=f"{self.LOOKBACK_DAYS}d",
                interval="1d",
                progress=False,
                auto_adjust=True,
                group_by="ticker",
            )

            if raw.empty:
                return None

            # Extract Close column for each ticker
            if isinstance(raw.columns, pd.MultiIndex):
                close_df = raw.xs("Close", axis=1, level=0)
            else:
                # Single-ticker edge case
                close_df = raw[["Close"]].rename(columns={"Close": tickers[0]})

            return close_df

        except Exception as e:
            logger.warning(f"SectorMomentumScorer download failed: {e}")
            return None

    def _ticker_momentum(self, prices, ticker: str):
        """
        Calculate momentum as percentage change over MOMENTUM_DAYS
        for a single ticker.

        Returns float or None if insufficient data.
        """
        try:
            if ticker not in prices.columns:
                return None

            series = prices[ticker].dropna()
            if len(series) < self.MOMENTUM_DAYS + 1:
                return None

            start_price = float(series.iloc[-(self.MOMENTUM_DAYS + 1)])
            end_price   = float(series.iloc[-1])

            if start_price <= 0:
                return None

            return (end_price - start_price) / start_price * 100

        except Exception as e:
            logger.debug(f"SectorMomentum [{ticker}] momentum calc: {e}")
            return None

    def _fallback_result(self) -> List[Dict[str, Any]]:
        """
        Returns a neutral fallback when data is completely unavailable.
        All sectors get momentum=0, signal=NEUTRAL.
        """
        sectors = list(SECTOR_STOCKS.keys())
        return [
            {
                "sector"  : sector,
                "momentum": 0.0,
                "rank"    : i + 1,
                "signal"  : "NEUTRAL",
            }
            for i, sector in enumerate(sectors)
        ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    scorer = SectorMomentumScorer()
    sectors = scorer.get_top_sectors()
    print(f"\n{'Rank':<6} {'Sector':<25} {'Momentum':>10} {'Signal'}")
    print("-" * 55)
    for s in sectors:
        icon = "🟢" if s["signal"] == "BUY" else ("🔴" if s["signal"] == "AVOID" else "🟡")
        print(f"  #{s['rank']}  {s['sector']:<25} {s['momentum']:>+8.2f}%  {icon} {s['signal']}")
