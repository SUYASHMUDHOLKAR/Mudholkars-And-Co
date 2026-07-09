"""
impact_analyzer.py
------------------
Scores the market impact of each classified news event.
Produces:
  - impact_score   : 0-100 (how much this event moves markets)
  - direction      : BULLISH / BEARISH / MIXED / NEUTRAL
  - urgency        : IMMEDIATE / TODAY / THIS_WEEK / WATCH
  - summary_line   : one-line human readable impact statement
"""

import logging

logger = logging.getLogger(__name__)

# Impact score by severity
SEVERITY_BASE_SCORE = {
    "CRITICAL": 80,
    "HIGH":     55,
    "MEDIUM":   30,
    "LOW":      10,
}

# Category base direction tendencies
# BULLISH = generally positive for markets
# BEARISH = generally negative for markets
# MIXED   = depends on specifics
CATEGORY_DIRECTION = {
    "GEOPOLITICAL":       "BEARISH",
    "GOVERNMENT_POLICY":  "MIXED",
    "CENTRAL_BANK":       "MIXED",
    "NATURAL_DISASTER":   "BEARISH",
    "ENERGY_COMMODITIES": "MIXED",
    "PANDEMIC_HEALTH":    "BEARISH",
    "TECHNOLOGY_DISRUPTION": "MIXED",
    "AUTOMOBILE_EV":      "MIXED",
    "AVIATION_TRAVEL":    "MIXED",
    "CLIMATE_ESG":        "MIXED",
    "SUPPLY_CHAIN":       "BEARISH",
    "AGRICULTURE_FOOD":   "MIXED",
    "REAL_ESTATE":        "BEARISH",
    "LABOR_SOCIAL":       "BEARISH",
    "CURRENCY_DEBT":      "BEARISH",
    "CORPORATE_EVENTS":   "MIXED",
    "BANKING_FINANCE":    "BEARISH",
    "DEFENSE_SPACE":      "MIXED",
    "WATER_RESOURCES":    "MIXED",
    "LEGAL_REGULATION":   "MIXED",
    "INFRASTRUCTURE":     "BULLISH",
    "TRADE_ECONOMICS":    "MIXED",
    "SCIENCE_INNOVATION": "BULLISH",
    "ELECTION_POLITICS":  "MIXED",
    "BLACK_SWAN":         "BEARISH",
}

# Bullish signal words — shift direction to BULLISH
BULLISH_SIGNALS = [
    "rate cut", "stimulus", "bailout", "ceasefire", "peace deal",
    "vaccine approved", "breakthrough", "trade deal", "growth",
    "surplus", "profit", "beat expectations", "upgrade", "recovery",
    "expansion", "investment", "subsidy", "reform", "positive",
    "record high", "approved", "discovery", "merger approved"
]

# Bearish signal words — shift direction to BEARISH
BEARISH_SIGNALS = [
    "rate hike", "sanctions", "war", "invasion", "collapse", "crash",
    "bankruptcy", "default", "recall", "fraud", "scandal", "strike",
    "ban", "tariff", "shortage", "crisis", "pandemic", "lockdown",
    "downgrade", "miss", "loss", "negative", "cut", "layoff", "resign",
    "investigation", "fine", "penalty", "slowdown", "contraction"
]

# Urgency mapping
URGENCY_MAP = {
    "CRITICAL": "IMMEDIATE",
    "HIGH":     "TODAY",
    "MEDIUM":   "THIS_WEEK",
    "LOW":      "WATCH",
}

# One-line impact templates per category
IMPACT_TEMPLATES = {
    "GEOPOLITICAL":       "Geopolitical tension → risk-off, FII outflows, defensive stocks",
    "GOVERNMENT_POLICY":  "Policy change → sector-specific regulatory impact",
    "CENTRAL_BANK":       "Central bank action → rate-sensitive sectors (Banking, NBFC, Realty) react",
    "NATURAL_DISASTER":   "Natural disaster → supply chain disruption, insurance sector hit",
    "ENERGY_COMMODITIES": "Energy/commodity shift → Oil PSUs, Aviation, Paints affected",
    "PANDEMIC_HEALTH":    "Health crisis → Pharma gains, broad market risk-off",
    "TECHNOLOGY_DISRUPTION": "Tech shift → IT/semiconductor sector impact",
    "AUTOMOBILE_EV":      "Auto/EV news → Auto sector, battery suppliers react",
    "AVIATION_TRAVEL":    "Aviation event → airline stocks, hospitality sector impact",
    "CLIMATE_ESG":        "Climate policy → green energy, fossil fuel sector shift",
    "SUPPLY_CHAIN":       "Supply chain disruption → manufacturing, import-dependent sectors hurt",
    "AGRICULTURE_FOOD":   "Agriculture event → FMCG input costs, food inflation risk",
    "REAL_ESTATE":        "Real estate event → Realty, Banking, Cement sector impact",
    "LABOR_SOCIAL":       "Labor event → productivity, operating cost impact on sectors",
    "CURRENCY_DEBT":      "Currency/debt event → INR, import costs, FII flows affected",
    "CORPORATE_EVENTS":   "Corporate event → direct company/sector impact",
    "BANKING_FINANCE":    "Banking/finance event → systemic risk, financial sector contagion",
    "DEFENSE_SPACE":      "Defense/space event → defense contractors, satellite sector",
    "WATER_RESOURCES":    "Resource event → mining, commodity, agriculture impact",
    "LEGAL_REGULATION":   "Legal/regulatory event → compliance cost, sector headwind",
    "INFRASTRUCTURE":     "Infrastructure event → Construction, Cement, Capital goods",
    "TRADE_ECONOMICS":    "Trade/economic data → broad market direction signal",
    "SCIENCE_INNOVATION": "Scientific breakthrough → sector disruption, long-term opportunity",
    "ELECTION_POLITICS":  "Political event → policy uncertainty, sector rotation",
    "BLACK_SWAN":         "Black swan event → extreme volatility, all sectors impacted",
}


class ImpactAnalyzer:
    """Scores market impact and direction for each classified event."""

    def analyze(self, article: dict) -> dict:
        """
        Analyze impact of a single classified article.
        Adds: impact_score, direction, urgency, summary_line.
        """
        text      = article.get("full_text", "").lower()
        severity  = article.get("severity", "LOW")
        category  = article.get("category", "GEOPOLITICAL")
        india_rel = article.get("india_relevant", False)
        source_priority = article.get("priority", "low")

        # Base score from severity
        score = SEVERITY_BASE_SCORE.get(severity, 10)

        # Boost for India-relevant news
        if india_rel:
            score = min(100, int(score * 1.3))

        # Boost for critical sources
        if source_priority == "critical":
            score = min(100, int(score * 1.1))

        # Determine direction
        direction = self._determine_direction(text, category)

        # Urgency
        urgency = URGENCY_MAP.get(severity, "WATCH")

        # Summary line
        summary_line = IMPACT_TEMPLATES.get(category, "Market impact: monitor closely")

        article["impact_score"]  = score
        article["direction"]     = direction
        article["urgency"]       = urgency
        article["summary_line"]  = summary_line

        return article

    def analyze_all(self, articles: list) -> list:
        """Analyze impact for all articles."""
        return [self.analyze(a) for a in articles]

    def get_top_events(self, articles: list, n: int = 10) -> list:
        """Return top N events sorted by impact score descending."""
        scored = [a for a in articles if a.get("impact_score") is not None]
        scored.sort(key=lambda x: (x["impact_score"], x["severity"] == "CRITICAL"), reverse=True)
        return scored[:n]

    def get_critical_only(self, articles: list) -> list:
        """Return only CRITICAL severity events."""
        return [a for a in articles if a.get("severity") == "CRITICAL"]

    # ------------------------------------------------------------------
    # Direction detection
    # ------------------------------------------------------------------

    def _determine_direction(self, text: str, category: str) -> str:
        """Determine if event is bullish or bearish for markets."""
        base = CATEGORY_DIRECTION.get(category, "MIXED")

        bull_hits = sum(1 for s in BULLISH_SIGNALS if s in text)
        bear_hits = sum(1 for s in BEARISH_SIGNALS if s in text)

        if bull_hits > bear_hits + 1:
            return "BULLISH"
        elif bear_hits > bull_hits + 1:
            return "BEARISH"
        elif base != "MIXED":
            return base
        else:
            return "MIXED"
