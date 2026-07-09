"""
india_impact_analyzer.py
------------------------
Scores market impact for each India-specific event.
Produces: impact_score (0-100), direction (BULLISH/BEARISH/MIXED),
          nifty_impact (expected Nifty % move), affected_stocks list.
"""

import logging

logger = logging.getLogger(__name__)

SEVERITY_BASE_SCORE = {
    "CRITICAL": 85,
    "HIGH":     60,
    "MEDIUM":   35,
    "LOW":      12,
}

# Default direction per India category
CATEGORY_DIRECTION = {
    "RBI_MONETARY_POLICY":    "MIXED",
    "UNION_BUDGET_TAXATION":  "MIXED",
    "SEBI_REGULATIONS":       "MIXED",
    "FII_DII_FLOWS":          "MIXED",
    "NIFTY_SENSEX_TECHNICAL": "MIXED",
    "CORPORATE_EARNINGS":     "MIXED",
    "INDIA_INFLATION_CPI":    "BEARISH",
    "INDIA_GDP_GROWTH":       "MIXED",
    "CRUDE_OIL_INDIA":        "MIXED",
    "RUPEE_FOREX":            "MIXED",
    "INDIA_GEOPOLITICS":      "BEARISH",
    "AGRICULTURE_MONSOON":    "MIXED",
    "BANKING_NPA":            "BEARISH",
    "IT_SECTOR_INDIA":        "MIXED",
    "INFRASTRUCTURE_CAPEX":   "BULLISH",
    "INDIA_EV_AUTO":          "MIXED",
    "REAL_ESTATE_INDIA":      "MIXED",
    "STARTUPS_IPO":           "BULLISH",
    "POWER_ENERGY_INDIA":     "BULLISH",
    "PHARMA_HEALTHCARE":      "MIXED",
    "INDIA_DEFENCE":          "BULLISH",
    "GST_TRADE_POLICY":       "MIXED",
    "INDIA_POLITICS":         "MIXED",
    "COMMODITY_METALS_INDIA": "MIXED",
    "BLACK_SWAN_INDIA":       "BEARISH",
}

# Expected Nifty move range per category + severity combo
NIFTY_IMPACT = {
    "RBI_MONETARY_POLICY":    {"CRITICAL": "-2% to +2%", "HIGH": "-1% to +1%", "MEDIUM": "-0.5% to +0.5%"},
    "UNION_BUDGET_TAXATION":  {"CRITICAL": "-3% to +4%", "HIGH": "-1.5% to +2%", "MEDIUM": "-0.5% to +1%"},
    "FII_DII_FLOWS":          {"CRITICAL": "-2% to +2%", "HIGH": "-1% to +1%", "MEDIUM": "Flat"},
    "INDIA_GEOPOLITICS":      {"CRITICAL": "-3% to -1%", "HIGH": "-2% to -0.5%", "MEDIUM": "-0.5% to Flat"},
    "BANKING_NPA":            {"CRITICAL": "-2% to -0.5%", "HIGH": "-1% to Flat", "MEDIUM": "Flat"},
    "BLACK_SWAN_INDIA":       {"CRITICAL": "-5% to -10%", "HIGH": "-3% to -5%", "MEDIUM": "-1% to -2%"},
    "CORPORATE_EARNINGS":     {"CRITICAL": "±3% on stock", "HIGH": "±1.5% on stock", "MEDIUM": "±0.5% on stock"},
    "CRUDE_OIL_INDIA":        {"CRITICAL": "-1.5% to -0.5%", "HIGH": "-1% to Flat", "MEDIUM": "Flat"},
    "INFRASTRUCTURE_CAPEX":   {"CRITICAL": "+1% to +2%", "HIGH": "+0.5% to +1%", "MEDIUM": "+0.2% to +0.5%"},
    "DEFAULT":                {"CRITICAL": "±1.5%", "HIGH": "±0.8%", "MEDIUM": "±0.3%"},
}

BULLISH_SIGNALS = [
    "rate cut", "stimulus", "capex", "ipo", "approved", "growth", "record",
    "beat", "outperform", "upgrade", "buy", "reform", "investment", "profit",
    "dividend", "buyback", "deal win", "order win", "approval", "surplus",
    "recovery", "expansion", "fii buying", "dii buying", "net buy"
]

BEARISH_SIGNALS = [
    "rate hike", "npa", "bad loan", "fraud", "scam", "ban", "warning",
    "shutdown", "recall", "strike", "miss", "loss", "downgrade", "sell",
    "outflow", "fii selling", "net sell", "slowdown", "crisis", "default",
    "bankruptcy", "penalty", "fine", "investigation", "probe", "raid"
]


class IndiaImpactAnalyzer:
    """Scores India-specific market impact for each event."""

    def __init__(self, config: dict):
        self.nse_stocks = config.get("nse_stocks", {})

    def analyze(self, article: dict) -> dict:
        text      = article.get("full_text", "").lower()
        severity  = article.get("severity", "LOW")
        category  = article.get("category", "NIFTY_SENSEX_TECHNICAL")
        priority  = article.get("priority", "medium")

        score = SEVERITY_BASE_SCORE.get(severity, 12)
        if priority == "critical":
            score = min(100, int(score * 1.15))

        direction    = self._direction(text, category)
        nifty_impact = self._nifty_impact(category, severity)
        stocks       = self._affected_stocks(text, category)

        article["impact_score"]  = score
        article["direction"]     = direction
        article["nifty_impact"]  = nifty_impact
        article["affected_stocks"] = stocks
        return article

    def analyze_all(self, articles: list) -> list:
        return [self.analyze(a) for a in articles]

    def get_top_events(self, articles: list, n: int = 10) -> list:
        scored = [a for a in articles if a.get("impact_score") is not None]
        scored.sort(key=lambda x: x["impact_score"], reverse=True)
        return scored[:n]

    def get_critical_only(self, articles: list) -> list:
        return [a for a in articles if a.get("severity") == "CRITICAL"]

    def _direction(self, text: str, category: str) -> str:
        bull = sum(1 for s in BULLISH_SIGNALS if s in text)
        bear = sum(1 for s in BEARISH_SIGNALS if s in text)
        base = CATEGORY_DIRECTION.get(category, "MIXED")
        if bull > bear + 1:
            return "BULLISH"
        elif bear > bull + 1:
            return "BEARISH"
        return base if base != "MIXED" else "MIXED"

    def _nifty_impact(self, category: str, severity: str) -> str:
        cat_map = NIFTY_IMPACT.get(category, NIFTY_IMPACT["DEFAULT"])
        return cat_map.get(severity, "±0.3%")

    def _affected_stocks(self, text: str, category: str) -> list:
        """Find NSE stocks mentioned in article text."""
        mentioned = []
        for sector, stocks in self.nse_stocks.items():
            for stock in stocks:
                if stock.lower() in text:
                    mentioned.append(stock)

        # If none found, return top 3 from primary sector
        if not mentioned:
            from india_event_classifier import CATEGORY_PRIMARY_SECTOR
            primary = CATEGORY_PRIMARY_SECTOR.get(category, "BANKING")
            mentioned = self.nse_stocks.get(primary, [])[:3]

        return list(dict.fromkeys(mentioned))[:5]  # deduplicate, max 5
