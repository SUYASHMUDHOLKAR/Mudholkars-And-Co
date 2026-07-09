"""
fundamental_analyst.py
----------------------
MID Colleague #2: Deep Fundamental Analyst

Analyses the BUSINESS behind the stock (not just the chart).
Uses yfinance's fundamental data (free, no API key).

Analyses:
  - Valuation:  P/E, P/B, PEG, EV/EBITDA, Market Cap
  - Profitability: ROE, ROCE, Net Margin, Operating Margin
  - Growth: Revenue growth, Profit growth, EPS growth
  - Debt: Debt/Equity, Current Ratio, Interest Coverage
  - Quality: Promoter Holding, Dividend Yield, Book Value
  - Cash Flow: Operating CF, Free CF, CF-to-Profit ratio
  - Overall Fundamental Score (0-100)
  - VALUE / GROWTH / QUALITY / AVOID classification
"""

import logging
from typing import Optional
from datetime import datetime

import yfinance as yf

logger = logging.getLogger(__name__)


class FundamentalAnalyst:
    """
    Deep fundamental analysis on any stock.
    Call analyze() → full FA report + VALUE/GROWTH/QUALITY/AVOID label.
    """

    def analyze(self, symbol: str) -> Optional[dict]:
        """Full fundamental analysis. Returns dict with score 0-100."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if not info or info.get("regularMarketPrice") is None:
                return None

            price      = info.get("regularMarketPrice") or info.get("currentPrice", 0)
            mkt_cap    = info.get("marketCap", 0)
            sector     = info.get("sector", "Unknown")
            industry   = info.get("industry", "Unknown")
            name       = info.get("shortName", symbol)

            # -- VALUATION --
            pe        = info.get("trailingPE") or info.get("forwardPE")
            pb        = info.get("priceToBook")
            peg       = info.get("pegRatio")
            ev_ebitda = info.get("enterpriseToEbitda")
            div_yield = info.get("dividendYield", 0)
            if div_yield:
                div_yield *= 100  # to %

            # -- PROFITABILITY --
            roe          = info.get("returnOnEquity", 0)
            if roe: roe *= 100
            roa          = info.get("returnOnAssets", 0)
            if roa: roa *= 100
            net_margin   = info.get("profitMargins", 0)
            if net_margin: net_margin *= 100
            op_margin    = info.get("operatingMargins", 0)
            if op_margin: op_margin *= 100
            gross_margin = info.get("grossMargins", 0)
            if gross_margin: gross_margin *= 100

            # -- GROWTH --
            rev_growth     = info.get("revenueGrowth", 0)
            if rev_growth: rev_growth *= 100
            earnings_growth = info.get("earningsGrowth", 0)
            if earnings_growth: earnings_growth *= 100
            qtr_rev_growth  = info.get("quarterlyRevenueGrowth", 0)
            if qtr_rev_growth: qtr_rev_growth *= 100

            # -- DEBT --
            debt_equity   = info.get("debtToEquity", 0)
            if debt_equity: debt_equity /= 100  # yfinance gives as %
            current_ratio = info.get("currentRatio", 0)
            quick_ratio   = info.get("quickRatio", 0)

            # -- CASH FLOW --
            op_cf    = info.get("operatingCashflow", 0)
            free_cf  = info.get("freeCashflow", 0)
            total_rev = info.get("totalRevenue", 0)

            # -- SHAREHOLDING --
            insider_pct   = info.get("heldPercentInsiders", 0)
            if insider_pct: insider_pct *= 100
            inst_pct      = info.get("heldPercentInstitutions", 0)
            if inst_pct: inst_pct *= 100
            book_value    = info.get("bookValue", 0)

            # -- SCORING --
            score, signals = self._compute_score(
                pe, pb, peg, roe, net_margin, rev_growth,
                earnings_growth, debt_equity, current_ratio,
                div_yield, insider_pct, free_cf, op_cf
            )

            # -- CLASSIFICATION --
            classification = self._classify(score, pe, rev_growth, roe, div_yield)

            return {
                "symbol":         symbol.replace(".NS", ""),
                "name":           name,
                "price":          round(price, 2) if price else 0,
                "market_cap_cr":  round(mkt_cap / 1e7, 0) if mkt_cap else 0,
                "sector":         sector,
                "industry":       industry,
                "timestamp":      datetime.utcnow().isoformat() + "Z",
                "fundamental_score": score,
                "classification":    classification,
                "signals":           signals,
                "valuation": {
                    "pe":         round(pe, 2) if pe else None,
                    "pb":         round(pb, 2) if pb else None,
                    "peg":        round(peg, 2) if peg else None,
                    "ev_ebitda":  round(ev_ebitda, 2) if ev_ebitda else None,
                    "div_yield":  round(div_yield, 2) if div_yield else 0,
                    "book_value": round(book_value, 2) if book_value else None,
                },
                "profitability": {
                    "roe":          round(roe, 2) if roe else None,
                    "roa":          round(roa, 2) if roa else None,
                    "net_margin":   round(net_margin, 2) if net_margin else None,
                    "op_margin":    round(op_margin, 2) if op_margin else None,
                    "gross_margin": round(gross_margin, 2) if gross_margin else None,
                },
                "growth": {
                    "revenue_growth":   round(rev_growth, 2) if rev_growth else None,
                    "earnings_growth":  round(earnings_growth, 2) if earnings_growth else None,
                    "qtr_rev_growth":   round(qtr_rev_growth, 2) if qtr_rev_growth else None,
                },
                "debt": {
                    "debt_equity":   round(debt_equity, 3) if debt_equity else 0,
                    "current_ratio": round(current_ratio, 2) if current_ratio else None,
                    "quick_ratio":   round(quick_ratio, 2) if quick_ratio else None,
                },
                "cashflow": {
                    "operating_cf_cr": round(op_cf / 1e7, 0) if op_cf else 0,
                    "free_cf_cr":      round(free_cf / 1e7, 0) if free_cf else 0,
                    "cf_positive":     (free_cf or 0) > 0,
                },
                "shareholding": {
                    "insider_pct":      round(insider_pct, 2) if insider_pct else None,
                    "institution_pct":  round(inst_pct, 2) if inst_pct else None,
                },
            }
        except Exception as e:
            logger.debug(f"[{symbol}] Fundamental analysis error: {e}")
            return None

    def analyze_batch(self, symbols: list) -> list:
        """Analyze multiple stocks. Returns sorted by fundamental score."""
        results = []
        for sym in symbols:
            r = self.analyze(sym)
            if r:
                results.append(r)
        results.sort(key=lambda x: x["fundamental_score"], reverse=True)
        return results

    # ------------------------------------------------------------------
    # Scoring (0-100)
    # ------------------------------------------------------------------

    def _compute_score(self, pe, pb, peg, roe, margin, rev_g,
                       earn_g, de, cr, div_yield, insider, fcf, ocf) -> tuple:
        score = 50
        signals = []

        # PE valuation (±10)
        if pe:
            if pe < 15:
                score += 8; signals.append(f"Attractive PE={pe:.1f}")
            elif pe < 25:
                score += 4
            elif pe > 50:
                score -= 8; signals.append(f"Expensive PE={pe:.1f}")
            elif pe > 35:
                score -= 4

        # ROE (±10)
        if roe:
            if roe >= 20:
                score += 10; signals.append(f"Excellent ROE={roe:.1f}%")
            elif roe >= 15:
                score += 7
            elif roe >= 10:
                score += 3
            elif roe < 5:
                score -= 5; signals.append(f"Poor ROE={roe:.1f}%")

        # Net Margin (±8)
        if margin:
            if margin >= 20:
                score += 8; signals.append(f"High margin={margin:.1f}%")
            elif margin >= 10:
                score += 5
            elif margin < 0:
                score -= 8; signals.append("Company making losses")
            elif margin < 5:
                score -= 3

        # Revenue Growth (±8)
        if rev_g:
            if rev_g >= 20:
                score += 8; signals.append(f"Strong revenue growth={rev_g:.0f}%")
            elif rev_g >= 10:
                score += 5
            elif rev_g < 0:
                score -= 5; signals.append("Revenue declining")

        # Earnings Growth (±7)
        if earn_g:
            if earn_g >= 25:
                score += 7; signals.append(f"Earnings growing {earn_g:.0f}%")
            elif earn_g >= 10:
                score += 4
            elif earn_g < 0:
                score -= 5

        # Debt (±8)
        if de is not None:
            if de <= 0.3:
                score += 8; signals.append("Low debt company")
            elif de <= 0.7:
                score += 4
            elif de > 1.5:
                score -= 8; signals.append(f"High debt D/E={de:.2f}")
            elif de > 1.0:
                score -= 4

        # Dividend (±3)
        if div_yield and div_yield > 2:
            score += 3; signals.append(f"Dividend yield={div_yield:.1f}%")

        # Insider holding (±4)
        if insider:
            if insider >= 60:
                score += 4; signals.append(f"High promoter holding={insider:.0f}%")
            elif insider < 30:
                score -= 3

        # Free cash flow (±5)
        if fcf and fcf > 0:
            score += 5; signals.append("Positive free cash flow")
        elif fcf and fcf < 0:
            score -= 3; signals.append("Negative free cash flow")

        return max(0, min(100, score)), signals

    def _classify(self, score, pe, rev_g, roe, div_yield) -> str:
        """Classify stock into investment style."""
        if pe and pe < 15 and score >= 50:
            return "VALUE"
        elif rev_g and rev_g >= 20 and roe and roe >= 15:
            return "GROWTH"
        elif roe and roe >= 18 and score >= 60:
            return "QUALITY"
        elif div_yield and div_yield >= 3:
            return "DIVIDEND"
        elif score < 35:
            return "AVOID"
        else:
            return "NEUTRAL"
