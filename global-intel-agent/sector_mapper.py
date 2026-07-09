"""
sector_mapper.py
----------------
Maps classified global events to affected Indian market sectors and specific stocks.
Every category has defined sector impacts with direction and reason.
"""

import logging

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# All NSE stocks grouped by sector
# -----------------------------------------------------------------------

SECTOR_STOCKS = {
    "IT":            ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "LTIM.NS"],
    "PHARMA":        ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "LUPIN.NS"],
    "BANKING":       ["HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "SBIN.NS"],
    "NBFC":          ["BAJFINANCE.NS", "BAJAJFINSV.NS", "CHOLAFIN.NS", "MUTHOOTFIN.NS"],
    "OIL_GAS":       ["RELIANCE.NS", "ONGC.NS", "IOC.NS", "BPCL.NS", "HINDPETRO.NS", "OIL.NS"],
    "METALS":        ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "VEDL.NS", "SAIL.NS", "NMDC.NS"],
    "AVIATION":      ["INDIGO.NS", "SPICEJET.NS"],
    "AUTO":          ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS", "EICHERMOT.NS"],
    "FMCG":          ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS", "MARICO.NS"],
    "REALTY":        ["DLF.NS", "GODREJPROP.NS", "OBEROIRLTY.NS", "PRESTIGE.NS"],
    "CEMENT":        ["ULTRACEMCO.NS", "SHREECEM.NS", "AMBUJACEMENT.NS", "ACC.NS"],
    "INFRA":         ["LT.NS", "KNR.NS", "NCC.NS", "IRB.NS"],
    "POWER":         ["NTPC.NS", "POWERGRID.NS", "TATAPOWER.NS", "ADANIPOWER.NS", "TORNTPOWER.NS"],
    "JEWELLERY":     ["TITAN.NS", "KALYAN.NS", "SENCO.NS"],
    "PAINTS":        ["ASIANPAINT.NS", "BERGER.NS", "INDIGO.NS"],
    "TELECOM":       ["BHARTIARTL.NS", "IDEA.NS"],
    "DEFENCE":       ["HAL.NS", "BEL.NS", "BHEL.NS", "MIDHANI.NS"],
    "AGRI":          ["UPL.NS", "PIIND.NS", "COROMANDEL.NS", "RALLIS.NS"],
    "INSURANCE":     ["HDFCLIFE.NS", "SBILIFE.NS", "ICICIGI.NS", "STARHEALTH.NS"],
    "GREEN_ENERGY":  ["ADANIGREEN.NS", "TATAPOWER.NS", "GREENKO.NS", "INOXWIND.NS"],
}

# -----------------------------------------------------------------------
# Category → sector impact rules
# Each entry: { sector, direction, reason, confidence }
# -----------------------------------------------------------------------

CATEGORY_SECTOR_MAP = {

    "GEOPOLITICAL": [
        {"sector": "IT",       "direction": "BEARISH", "reason": "FII risk-off → IT selling"},
        {"sector": "METALS",   "direction": "BEARISH", "reason": "Commodity demand uncertainty"},
        {"sector": "DEFENCE",  "direction": "BULLISH", "reason": "Defense spending increases in conflicts"},
        {"sector": "FMCG",     "direction": "NEUTRAL",  "reason": "Domestic demand insulated"},
        {"sector": "PHARMA",   "direction": "NEUTRAL",  "reason": "Defensive sector holds value"},
    ],

    "CENTRAL_BANK": [
        {"sector": "BANKING",  "direction": "MIXED",   "reason": "Rate changes directly impact NIMs"},
        {"sector": "NBFC",     "direction": "BEARISH", "reason": "Higher rates = higher borrowing cost"},
        {"sector": "REALTY",   "direction": "BEARISH", "reason": "Higher EMIs reduce home demand"},
        {"sector": "AUTO",     "direction": "BEARISH", "reason": "Higher loan rates slow auto sales"},
        {"sector": "IT",       "direction": "BEARISH", "reason": "Rate hike = FII exits EM markets"},
        {"sector": "FMCG",     "direction": "NEUTRAL",  "reason": "Resilient to rate cycles"},
    ],

    "ENERGY_COMMODITIES": [
        {"sector": "OIL_GAS",  "direction": "BULLISH", "reason": "Higher crude = upstream gains"},
        {"sector": "AVIATION", "direction": "BEARISH", "reason": "Jet fuel (ATF) is 35% of airline cost"},
        {"sector": "PAINTS",   "direction": "BEARISH", "reason": "Petrochemical-based inputs get costlier"},
        {"sector": "AUTO",     "direction": "BEARISH", "reason": "Fuel costs affect vehicle demand"},
        {"sector": "FMCG",     "direction": "BEARISH", "reason": "Packaging and transport costs rise"},
        {"sector": "POWER",    "direction": "MIXED",   "reason": "Gas-based plants hurt, coal neutral"},
        {"sector": "GREEN_ENERGY", "direction": "BULLISH", "reason": "Oil spike accelerates green shift"},
    ],

    "PANDEMIC_HEALTH": [
        {"sector": "PHARMA",   "direction": "BULLISH", "reason": "Drug demand, vaccine orders surge"},
        {"sector": "FMCG",     "direction": "BULLISH", "reason": "Hygiene, health products demand up"},
        {"sector": "AVIATION", "direction": "BEARISH", "reason": "Travel bans, lockdowns kill demand"},
        {"sector": "REALTY",   "direction": "BEARISH", "reason": "Construction halts, WFH trend"},
        {"sector": "IT",       "direction": "BULLISH", "reason": "WFH infrastructure demand rises"},
        {"sector": "BANKING",  "direction": "BEARISH", "reason": "NPA fears, loan moratoriums"},
    ],

    "TECHNOLOGY_DISRUPTION": [
        {"sector": "IT",       "direction": "MIXED",   "reason": "AI = opportunity + displacement risk"},
        {"sector": "TELECOM",  "direction": "BULLISH", "reason": "5G/6G rollout drives capex"},
        {"sector": "AUTO",     "direction": "MIXED",   "reason": "Autonomous driving disrupts traditional auto"},
        {"sector": "BANKING",  "direction": "BULLISH", "reason": "Fintech integration creates efficiency"},
    ],

    "AUTOMOBILE_EV": [
        {"sector": "AUTO",     "direction": "MIXED",   "reason": "EV transition disrupts ICE makers"},
        {"sector": "METALS",   "direction": "BULLISH", "reason": "Lithium, cobalt, aluminium demand"},
        {"sector": "OIL_GAS",  "direction": "BEARISH", "reason": "Long-term fuel demand decline"},
        {"sector": "POWER",    "direction": "BULLISH", "reason": "EV charging needs electricity"},
        {"sector": "BANKING",  "direction": "BULLISH", "reason": "EV loans, green financing grows"},
    ],

    "AVIATION_TRAVEL": [
        {"sector": "AVIATION", "direction": "MIXED",   "reason": "Direct sector impact"},
        {"sector": "OIL_GAS",  "direction": "MIXED",   "reason": "ATF demand linked to flight volume"},
        {"sector": "FMCG",     "direction": "NEUTRAL",  "reason": "Travel retail marginal impact"},
    ],

    "TRADE_ECONOMICS": [
        {"sector": "IT",       "direction": "MIXED",   "reason": "Global GDP affects IT deal flows"},
        {"sector": "METALS",   "direction": "MIXED",   "reason": "Trade flows affect commodity demand"},
        {"sector": "AUTO",     "direction": "MIXED",   "reason": "Export markets crucial for Tata, M&M"},
        {"sector": "FMCG",     "direction": "NEUTRAL",  "reason": "Domestic demand driven"},
        {"sector": "PHARMA",   "direction": "MIXED",   "reason": "US/EU export markets critical"},
    ],

    "CURRENCY_DEBT": [
        {"sector": "IT",       "direction": "BULLISH", "reason": "Weak INR = better USD realisation"},
        {"sector": "PHARMA",   "direction": "BULLISH", "reason": "Export earnings in USD"},
        {"sector": "AVIATION", "direction": "BEARISH", "reason": "Dollar-denominated fuel costs"},
        {"sector": "OIL_GAS",  "direction": "BEARISH", "reason": "Crude imports costlier in weak INR"},
        {"sector": "BANKING",  "direction": "BEARISH", "reason": "FII outflows = banking sector pressure"},
    ],

    "BANKING_FINANCE": [
        {"sector": "BANKING",  "direction": "BEARISH", "reason": "Contagion risk, NPA concerns"},
        {"sector": "NBFC",     "direction": "BEARISH", "reason": "Liquidity dries up for NBFCs"},
        {"sector": "REALTY",   "direction": "BEARISH", "reason": "Credit squeeze hurts developers"},
        {"sector": "AUTO",     "direction": "BEARISH", "reason": "Vehicle loans harder to get"},
    ],

    "ELECTION_POLITICS": [
        {"sector": "INFRA",    "direction": "BULLISH", "reason": "Election capex, infra promises"},
        {"sector": "CEMENT",   "direction": "BULLISH", "reason": "Infrastructure spending benefits"},
        {"sector": "POWER",    "direction": "BULLISH", "reason": "Rural electrification promises"},
        {"sector": "BANKING",  "direction": "MIXED",   "reason": "Policy uncertainty affects credit"},
        {"sector": "OIL_GAS",  "direction": "MIXED",   "reason": "Fuel price politics"},
    ],

    "CLIMATE_ESG": [
        {"sector": "GREEN_ENERGY", "direction": "BULLISH", "reason": "Clean energy mandates boost sector"},
        {"sector": "OIL_GAS",  "direction": "BEARISH", "reason": "Fossil fuel divestment pressure"},
        {"sector": "AUTO",     "direction": "MIXED",   "reason": "ICE phase-out pressure, EV opportunity"},
        {"sector": "CEMENT",   "direction": "BEARISH", "reason": "Carbon emission penalties"},
        {"sector": "METALS",   "direction": "BEARISH", "reason": "High carbon footprint sectors penalised"},
    ],

    "AGRICULTURE_FOOD": [
        {"sector": "FMCG",     "direction": "BEARISH", "reason": "Input cost inflation squeezes margins"},
        {"sector": "AGRI",     "direction": "MIXED",   "reason": "Fertilizer, pesticide demand changes"},
        {"sector": "BANKING",  "direction": "MIXED",   "reason": "Agri NPA risk in rural credit"},
    ],

    "CORPORATE_EVENTS": [
        {"sector": "IT",       "direction": "MIXED",   "reason": "M&A and earnings impact IT majors"},
        {"sector": "BANKING",  "direction": "MIXED",   "reason": "Financial sector consolidation"},
        {"sector": "AUTO",     "direction": "MIXED",   "reason": "Recall, merger affect auto names"},
    ],

    "LEGAL_REGULATION": [
        {"sector": "IT",       "direction": "BEARISH", "reason": "Data privacy regulations increase cost"},
        {"sector": "BANKING",  "direction": "MIXED",   "reason": "RBI/SEBI actions"},
        {"sector": "PHARMA",   "direction": "BEARISH", "reason": "Drug pricing regulation risk"},
        {"sector": "TELECOM",  "direction": "MIXED",   "reason": "Spectrum, license regulations"},
    ],

    "SUPPLY_CHAIN": [
        {"sector": "AUTO",     "direction": "BEARISH", "reason": "Chip shortages hurt production"},
        {"sector": "IT",       "direction": "BEARISH", "reason": "Hardware supply impacts tech cos"},
        {"sector": "FMCG",     "direction": "BEARISH", "reason": "Packaging, distribution disrupted"},
        {"sector": "METALS",   "direction": "MIXED",   "reason": "Steel/aluminium logistics impacted"},
    ],

    "INFRASTRUCTURE": [
        {"sector": "INFRA",    "direction": "BULLISH", "reason": "Direct beneficiary"},
        {"sector": "CEMENT",   "direction": "BULLISH", "reason": "Construction material demand"},
        {"sector": "METALS",   "direction": "BULLISH", "reason": "Steel demand for projects"},
        {"sector": "POWER",    "direction": "BULLISH", "reason": "Grid expansion projects"},
        {"sector": "BANKING",  "direction": "BULLISH", "reason": "Project financing opportunities"},
    ],

    "NATURAL_DISASTER": [
        {"sector": "INSURANCE", "direction": "BEARISH", "reason": "Large claim payouts"},
        {"sector": "INFRA",    "direction": "BULLISH", "reason": "Reconstruction spending"},
        {"sector": "CEMENT",   "direction": "BULLISH", "reason": "Rebuilding demand"},
        {"sector": "FMCG",     "direction": "MIXED",   "reason": "Supply disruption in affected areas"},
    ],

    "DEFENSE_SPACE": [
        {"sector": "DEFENCE",  "direction": "BULLISH", "reason": "Defense orders for HAL, BEL, BHEL"},
        {"sector": "IT",       "direction": "BULLISH", "reason": "Defence tech, cybersecurity demand"},
        {"sector": "METALS",   "direction": "BULLISH", "reason": "Steel, aluminium for defense"},
    ],

    "SCIENCE_INNOVATION": [
        {"sector": "PHARMA",   "direction": "BULLISH", "reason": "Biotech breakthroughs benefit sector"},
        {"sector": "IT",       "direction": "BULLISH", "reason": "Tech innovation = long-term growth"},
        {"sector": "GREEN_ENERGY", "direction": "BULLISH", "reason": "Fusion/clean tech breakthroughs"},
    ],

    "BLACK_SWAN": [
        {"sector": "BANKING",  "direction": "BEARISH", "reason": "Systemic risk, credit crunch"},
        {"sector": "IT",       "direction": "BEARISH", "reason": "FII mass exit"},
        {"sector": "METALS",   "direction": "BEARISH", "reason": "Commodity demand collapse"},
        {"sector": "FMCG",     "direction": "NEUTRAL",  "reason": "Defensive, domestic demand holds"},
        {"sector": "PHARMA",   "direction": "NEUTRAL",  "reason": "Defensive sector"},
        {"sector": "GOLD",     "direction": "BULLISH", "reason": "Safe-haven rush"},
    ],
}


class SectorMapper:
    """Maps classified events to Indian sectors and stocks."""

    def map_event(self, article: dict) -> dict:
        """
        Add sector impacts to a classified, analyzed article.
        Returns article with 'sector_impacts' key added.
        """
        category = article.get("category", "GEOPOLITICAL")
        impacts  = CATEGORY_SECTOR_MAP.get(category, [])

        enriched = []
        for impact in impacts:
            sector = impact["sector"]
            stocks = SECTOR_STOCKS.get(sector, [])[:4]
            enriched.append({
                "sector":    sector,
                "direction": impact["direction"],
                "reason":    impact["reason"],
                "stocks":    [s.replace(".NS", "") for s in stocks],
            })

        article["sector_impacts"] = enriched
        return article

    def map_all(self, articles: list) -> list:
        """Map sectors for all articles."""
        return [self.map_event(a) for a in articles]

    def get_aggregate_sector_view(self, articles: list) -> dict:
        """
        Aggregate all article impacts into one sector-level view.
        Returns dict: sector → { net_direction, score, top_drivers }
        """
        sector_scores = {}

        SCORE_MAP = {"BULLISH": 2, "NEUTRAL": 0, "MIXED": 0, "BEARISH": -2}

        for article in articles:
            imp_score = article.get("impact_score", 10)
            weight    = imp_score / 100.0

            for impact in article.get("sector_impacts", []):
                sector = impact["sector"]
                dirn   = impact["direction"]
                delta  = SCORE_MAP.get(dirn, 0) * weight

                if sector not in sector_scores:
                    sector_scores[sector] = {
                        "score": 0.0,
                        "drivers": [],
                        "stocks": SECTOR_STOCKS.get(sector, [])[:4]
                    }

                sector_scores[sector]["score"] += delta
                sector_scores[sector]["drivers"].append({
                    "title":     article.get("title", "")[:80],
                    "direction": dirn,
                    "impact":    imp_score,
                })

        # Assign final direction label
        for sector, data in sector_scores.items():
            s = data["score"]
            if s >= 1.5:
                data["direction"] = "BULLISH"
            elif s >= 0.3:
                data["direction"] = "MILD_BULLISH"
            elif s <= -1.5:
                data["direction"] = "BEARISH"
            elif s <= -0.3:
                data["direction"] = "MILD_BEARISH"
            else:
                data["direction"] = "NEUTRAL"

            data["score"]   = round(s, 2)
            data["drivers"] = sorted(
                data["drivers"], key=lambda x: x["impact"], reverse=True
            )[:3]

        return dict(
            sorted(sector_scores.items(),
                   key=lambda x: x[1]["score"], reverse=True)
        )
