"""
india_event_classifier.py
--------------------------
Classifies news articles into 25 India-specific event categories.
Assigns severity and flags which NSE sector is primarily affected.
"""

import logging
from collections import Counter

logger = logging.getLogger(__name__)

# Urgency map
URGENCY_MAP = {
    "CRITICAL": "IMMEDIATE",
    "HIGH":     "TODAY",
    "MEDIUM":   "THIS_WEEK",
    "LOW":      "WATCH",
}

# Which category primarily affects which NSE sector
CATEGORY_PRIMARY_SECTOR = {
    "RBI_MONETARY_POLICY":    "BANKING",
    "UNION_BUDGET_TAXATION":  "BROAD_MARKET",
    "SEBI_REGULATIONS":       "BROAD_MARKET",
    "FII_DII_FLOWS":          "BROAD_MARKET",
    "NIFTY_SENSEX_TECHNICAL": "BROAD_MARKET",
    "CORPORATE_EARNINGS":     "COMPANY_SPECIFIC",
    "INDIA_INFLATION_CPI":    "FMCG",
    "INDIA_GDP_GROWTH":       "BROAD_MARKET",
    "CRUDE_OIL_INDIA":        "OIL_GAS",
    "RUPEE_FOREX":            "IT",
    "INDIA_GEOPOLITICS":      "DEFENCE",
    "AGRICULTURE_MONSOON":    "AGRI",
    "BANKING_NPA":            "BANKING",
    "IT_SECTOR_INDIA":        "IT",
    "INFRASTRUCTURE_CAPEX":   "INFRA",
    "INDIA_EV_AUTO":          "AUTO",
    "REAL_ESTATE_INDIA":      "REALTY",
    "STARTUPS_IPO":           "BROAD_MARKET",
    "POWER_ENERGY_INDIA":     "POWER",
    "PHARMA_HEALTHCARE":      "PHARMA",
    "INDIA_DEFENCE":          "DEFENCE",
    "GST_TRADE_POLICY":       "BROAD_MARKET",
    "INDIA_POLITICS":         "BROAD_MARKET",
    "COMMODITY_METALS_INDIA": "METALS",
    "BLACK_SWAN_INDIA":       "BROAD_MARKET",
}

# One-line summary per category
CATEGORY_SUMMARY = {
    "RBI_MONETARY_POLICY":    "RBI action → Banking, NBFC, Realty, rate-sensitive sectors react",
    "UNION_BUDGET_TAXATION":  "Budget/tax event → broad market and sector-specific impact",
    "SEBI_REGULATIONS":       "SEBI circular/rule → market structure, F&O, FPI flow impact",
    "FII_DII_FLOWS":          "FII/DII flow → direct buying/selling pressure on indices",
    "NIFTY_SENSEX_TECHNICAL": "Index technical move → trend confirmation, support/resistance",
    "CORPORATE_EARNINGS":     "Corporate results → individual stock + sector sentiment",
    "INDIA_INFLATION_CPI":    "Inflation data → RBI rate path, FMCG margins, consumer demand",
    "INDIA_GDP_GROWTH":       "GDP data → economic cycle, capex, credit growth outlook",
    "CRUDE_OIL_INDIA":        "Crude price → Aviation, Paints, Tyres hurt; Oil PSUs gain",
    "RUPEE_FOREX":            "INR move → IT/Pharma gain on weak INR; importers hurt",
    "INDIA_GEOPOLITICS":      "Geopolitical event → defence stocks gain; risk-off for broad market",
    "AGRICULTURE_MONSOON":    "Monsoon/crop → FMCG input costs, food inflation, rural demand",
    "BANKING_NPA":            "Banking NPA/merger → bank stock direct impact, credit outlook",
    "IT_SECTOR_INDIA":        "IT sector news → TCS, Infosys, Wipro direct impact",
    "INFRASTRUCTURE_CAPEX":   "Infra/PLI → L&T, Cement, Steel, Capital goods sector",
    "INDIA_EV_AUTO":          "Auto/EV news → Maruti, Tata Motors, M&M direct impact",
    "REAL_ESTATE_INDIA":      "Real estate → DLF, Godrej Properties, Housing sector",
    "STARTUPS_IPO":           "IPO/startup → listing day volatility, sector sentiment",
    "POWER_ENERGY_INDIA":     "Power sector → NTPC, Adani Green, Tata Power impact",
    "PHARMA_HEALTHCARE":      "Pharma USFDA/policy → Sun Pharma, Dr Reddy's, Cipla",
    "INDIA_DEFENCE":          "Defence → HAL, BEL, BHEL, DRDO-linked stocks",
    "GST_TRADE_POLICY":       "GST/trade → sector cost structure, export competitiveness",
    "INDIA_POLITICS":         "Political event → policy uncertainty, sector rotation",
    "COMMODITY_METALS_INDIA": "Metals/MCX → Tata Steel, Hindalco, Vedanta, Coal India",
    "BLACK_SWAN_INDIA":       "Black swan → extreme volatility, circuit breaker risk",
}


class IndiaEventClassifier:
    """Classifies articles into 25 India-specific categories."""

    def __init__(self, config: dict):
        self.categories        = config.get("categories", {})
        self.severity_keywords = config.get("severity_keywords", {})

    def classify(self, article: dict) -> dict:
        text = article.get("full_text", "").lower()
        category, confidence = self._match_category(text)
        severity             = self._assess_severity(text, category)
        urgency              = URGENCY_MAP.get(severity, "WATCH")
        primary_sector       = CATEGORY_PRIMARY_SECTOR.get(category, "BROAD_MARKET")
        summary_line         = CATEGORY_SUMMARY.get(category, "India market event — monitor closely")

        article["category"]       = category
        article["category_id"]    = self.categories.get(category, {}).get("id", 0)
        article["severity"]       = severity
        article["urgency"]        = urgency
        article["confidence"]     = confidence
        article["primary_sector"] = primary_sector
        article["summary_line"]   = summary_line
        return article

    def classify_all(self, articles: list) -> list:
        result = []
        for a in articles:
            try:
                result.append(self.classify(a))
            except Exception as e:
                logger.debug(f"Classify error: {e}")
        logger.info(f"Classified {len(result)} India articles")
        return result

    def get_stats(self, articles: list) -> dict:
        cats = Counter(a.get("category") for a in articles)
        sevs = Counter(a.get("severity") for a in articles)
        return {
            "total":       len(articles),
            "by_category": dict(cats.most_common()),
            "by_severity": {
                "CRITICAL": sevs.get("CRITICAL", 0),
                "HIGH":     sevs.get("HIGH", 0),
                "MEDIUM":   sevs.get("MEDIUM", 0),
                "LOW":      sevs.get("LOW", 0),
            },
        }

    def _match_category(self, text: str) -> tuple:
        scores = {}
        for name, data in self.categories.items():
            keywords = data.get("keywords", [])
            boost    = data.get("severity_boost", 1.0)
            hits     = sum(1 for kw in keywords if kw in text)
            if hits > 0:
                scores[name] = hits * boost
        if not scores:
            return ("NIFTY_SENSEX_TECHNICAL", 0)
        best = max(scores, key=scores.get)
        return (best, round(scores[best], 2))

    def _assess_severity(self, text: str, category: str) -> str:
        hits = {tier: sum(1 for kw in kws if kw in text)
                for tier, kws in self.severity_keywords.items()}

        if hits.get("CRITICAL", 0) >= 1:
            base = "CRITICAL"
        elif hits.get("HIGH", 0) >= 2:
            base = "HIGH"
        elif hits.get("HIGH", 0) >= 1:
            base = "MEDIUM"
        elif hits.get("MEDIUM", 0) >= 2:
            base = "MEDIUM"
        else:
            base = "LOW"

        # Boost for market-critical India categories
        mrel = self.categories.get(category, {}).get("market_relevance", "LOW")
        if mrel == "CRITICAL" and base == "LOW":
            base = "MEDIUM"
        elif mrel == "CRITICAL" and base == "MEDIUM":
            base = "HIGH"
        return base
