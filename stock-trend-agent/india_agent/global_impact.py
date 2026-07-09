"""
global_impact.py
----------------
Maps global market events (from Scout Agent) to Indian market sectors.
Every global event has a known, predictable impact on specific Indian sectors.

Rules engine:
  - US markets up/down   → IT, Pharma, Metals follow
  - Crude oil up         → Aviation, Paints, Tyres hurt | Oil PSUs gain
  - USD/INR moves        → IT gains on weak INR | Importers hurt
  - Gold up              → Jewelry stocks, safe-haven buying
  - VIX high             → FII selling, market-wide fall
  - China markets        → Metals, commodities sector impact
  - Fed rate signals     → Banking, NBFC, rate-sensitive sectors
"""

# -----------------------------------------------------------------------
# Sector → stocks mapping (major NSE-listed companies)
# -----------------------------------------------------------------------

SECTOR_STOCKS = {
    "IT": [
        "TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS",
        "TECHM.NS", "LTIM.NS", "MPHASIS.NS", "COFORGE.NS"
    ],
    "PHARMA": [
        "SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS",
        "AUROPHARMA.NS", "LUPIN.NS", "BIOCON.NS"
    ],
    "BANKING": [
        "HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS",
        "SBIN.NS", "BANKBARODA.NS", "INDUSINDBK.NS", "FEDERALBNK.NS"
    ],
    "NBFC": [
        "BAJFINANCE.NS", "BAJAJFINSV.NS", "CHOLAFIN.NS",
        "MUTHOOTFIN.NS", "MANAPPURAM.NS"
    ],
    "OIL_GAS": [
        "RELIANCE.NS", "ONGC.NS", "IOC.NS", "BPCL.NS",
        "HINDPETRO.NS", "GAIL.NS", "OIL.NS"
    ],
    "METALS": [
        "TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "VEDL.NS",
        "NATIONALUM.NS", "SAIL.NS", "NMDC.NS"
    ],
    "AVIATION": [
        "INDIGO.NS", "SPICEJET.NS"
    ],
    "AUTO": [
        "MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "BAJAJ-AUTO.NS",
        "HEROMOTOCO.NS", "EICHERMOT.NS", "ASHOKLEY.NS"
    ],
    "FMCG": [
        "HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS",
        "DABUR.NS", "MARICO.NS", "COLPAL.NS"
    ],
    "REALTY": [
        "DLF.NS", "GODREJPROP.NS", "OBEROIRLTY.NS",
        "PRESTIGE.NS", "BRIGADE.NS"
    ],
    "INFRA_CEMENT": [
        "ULTRACEMCO.NS", "SHREECEM.NS", "AMBUJACEMENT.NS",
        "LARSEN.NS", "KNR.NS"
    ],
    "POWER": [
        "NTPC.NS", "POWERGRID.NS", "TATAPOWER.NS",
        "ADANIPOWER.NS", "TORNTPOWER.NS"
    ],
    "JEWELLERY": [
        "TITAN.NS", "KALYAN.NS", "SENCO.NS", "RAJESHEXPO.NS"
    ],
    "PAINTS_TYRES": [
        "ASIANPAINT.NS", "BERGER.NS", "APOLLOTYRE.NS",
        "MRF.NS", "CEATLTD.NS"
    ],
    "TELECOM": [
        "BHARTIARTL.NS", "IDEA.NS"
    ],
}

# -----------------------------------------------------------------------
# Global event → Indian sector impact rules
# Each rule has:
#   trigger      : what condition from Scout data triggers this
#   direction    : POSITIVE / NEGATIVE / NEUTRAL impact on India
#   sectors      : which Indian sectors are affected
#   magnitude    : LOW / MEDIUM / HIGH / EXTREME
#   reason       : human-readable explanation
# -----------------------------------------------------------------------

GLOBAL_IMPACT_RULES = [

    # ── US MARKETS ──────────────────────────────────────────────────────
    {
        "id": "US_MARKET_CRASH",
        "trigger": "us_index_down_critical",
        "description": "US markets (S&P500/NASDAQ) fall >3%",
        "direction": "NEGATIVE",
        "magnitude": "HIGH",
        "sectors_impacted": {
            "NEGATIVE": ["IT", "PHARMA", "METALS", "BANKING", "AUTO"],
            "POSITIVE": [],
            "NEUTRAL":  ["FMCG", "POWER"]
        },
        "india_reason": (
            "FIIs (Foreign Institutional Investors) sell Indian equities when US crashes. "
            "IT sector hit hardest — 60%+ revenue from US clients. "
            "Risk-off sentiment triggers broad market selloff."
        ),
        "expected_nifty_move": "-1.5% to -3.5%",
        "lag": "Same day open or next day if US closes after India"
    },
    {
        "id": "US_MARKET_SURGE",
        "trigger": "us_index_up_critical",
        "description": "US markets (S&P500/NASDAQ) rise >3%",
        "direction": "POSITIVE",
        "magnitude": "HIGH",
        "sectors_impacted": {
            "POSITIVE": ["IT", "PHARMA", "METALS", "BANKING"],
            "NEGATIVE": [],
            "NEUTRAL":  ["FMCG", "REALTY"]
        },
        "india_reason": (
            "FII buying increases. Global risk-on sentiment. "
            "IT stocks rally on strong US economic signals. "
            "Metal stocks follow commodity price surge."
        ),
        "expected_nifty_move": "+1% to +2.5%",
        "lag": "Next trading day open (SGX Nifty signals it overnight)"
    },

    # ── CRUDE OIL ────────────────────────────────────────────────────────
    {
        "id": "CRUDE_OIL_SPIKE",
        "trigger": "crude_oil_up_warning",
        "description": "Crude Oil rises >2%",
        "direction": "MIXED",
        "magnitude": "HIGH",
        "sectors_impacted": {
            "NEGATIVE": ["AVIATION", "PAINTS_TYRES", "FMCG", "AUTO"],
            "POSITIVE": ["OIL_GAS"],
            "NEUTRAL":  ["IT", "BANKING"]
        },
        "india_reason": (
            "India imports ~85% of its oil. Crude spike raises input costs for "
            "aviation (ATF prices), paints (petrochemical inputs), tyre companies. "
            "OMCs (IOC, BPCL, HPCL) get squeezed on margins. "
            "Upstream players like ONGC, Oil India benefit. "
            "INR weakens → inflation risk → RBI rate pressure."
        ),
        "expected_nifty_move": "-0.5% to -1.5%",
        "lag": "Immediate, same session"
    },
    {
        "id": "CRUDE_OIL_CRASH",
        "trigger": "crude_oil_down_warning",
        "description": "Crude Oil falls >2%",
        "direction": "POSITIVE",
        "magnitude": "MEDIUM",
        "sectors_impacted": {
            "POSITIVE": ["AVIATION", "PAINTS_TYRES", "FMCG", "AUTO", "BANKING"],
            "NEGATIVE": ["OIL_GAS"],
            "NEUTRAL":  ["IT"]
        },
        "india_reason": (
            "Lower oil = lower import bill = CAD improvement = INR strengthens. "
            "Aviation stocks surge on lower ATF costs. "
            "Paint companies see margin expansion. "
            "Overall market bullish — reduces India's fiscal pressure."
        ),
        "expected_nifty_move": "+0.5% to +1.5%",
        "lag": "Immediate to next session"
    },

    # ── US DOLLAR / INR ──────────────────────────────────────────────────
    {
        "id": "INR_WEAKENS",
        "trigger": "usdinr_up_warning",
        "description": "USD/INR rises (Rupee weakens)",
        "direction": "MIXED",
        "magnitude": "MEDIUM",
        "sectors_impacted": {
            "POSITIVE": ["IT", "PHARMA"],
            "NEGATIVE": ["AVIATION", "OIL_GAS", "AUTO", "REALTY"],
            "NEUTRAL":  ["FMCG", "TELECOM"]
        },
        "india_reason": (
            "Weak INR boosts IT and Pharma — they earn in USD, report in INR. "
            "Every 1 Re depreciation adds ~3-4% to IT earnings. "
            "Importers (crude, electronics) hurt. "
            "FIIs may pull out → broader market pressure."
        ),
        "expected_nifty_move": "Flat to -0.5% (sector rotation, not broad fall)",
        "lag": "Immediate"
    },
    {
        "id": "INR_STRENGTHENS",
        "trigger": "usdinr_down_warning",
        "description": "USD/INR falls (Rupee strengthens)",
        "direction": "MIXED",
        "magnitude": "MEDIUM",
        "sectors_impacted": {
            "POSITIVE": ["AVIATION", "AUTO", "REALTY", "BANKING"],
            "NEGATIVE": ["IT", "PHARMA"],
            "NEUTRAL":  ["FMCG"]
        },
        "india_reason": (
            "Strong INR means lower import costs. FII inflows likely. "
            "IT/Pharma earnings in USD translate to less in INR — "
            "negative for their reported profits."
        ),
        "expected_nifty_move": "+0.3% to +0.8%",
        "lag": "Immediate to next session"
    },

    # ── VIX / FEAR ───────────────────────────────────────────────────────
    {
        "id": "VIX_EXTREME_FEAR",
        "trigger": "vix_extreme",
        "description": "VIX crosses 40 (extreme fear)",
        "direction": "NEGATIVE",
        "magnitude": "EXTREME",
        "sectors_impacted": {
            "NEGATIVE": ["BANKING", "METALS", "IT", "AUTO", "REALTY"],
            "POSITIVE": ["GOLD_ETF"],
            "NEUTRAL":  ["FMCG", "PHARMA"]
        },
        "india_reason": (
            "VIX >40 = global panic. FIIs dump emerging market equities first. "
            "India sees massive FII outflows. Circuit breakers possible. "
            "Only defensive plays (FMCG, Pharma, Gold) hold up."
        ),
        "expected_nifty_move": "-3% to -8%",
        "lag": "Next India session open — often gap down"
    },
    {
        "id": "VIX_HIGH_FEAR",
        "trigger": "vix_high",
        "description": "VIX crosses 30 (high fear)",
        "direction": "NEGATIVE",
        "magnitude": "HIGH",
        "sectors_impacted": {
            "NEGATIVE": ["BANKING", "METALS", "REALTY"],
            "POSITIVE": [],
            "NEUTRAL":  ["FMCG", "PHARMA", "IT"]
        },
        "india_reason": (
            "Elevated fear → FII risk-off → India equity selling. "
            "Small/midcap stocks fall harder than Nifty50."
        ),
        "expected_nifty_move": "-1% to -3%",
        "lag": "Same or next session"
    },

    # ── GOLD ────────────────────────────────────────────────────────────
    {
        "id": "GOLD_SURGE",
        "trigger": "gold_up_warning",
        "description": "Gold rises >1.5%",
        "direction": "MIXED",
        "magnitude": "LOW",
        "sectors_impacted": {
            "POSITIVE": ["JEWELLERY"],
            "NEGATIVE": ["BANKING", "REALTY"],
            "NEUTRAL":  ["IT", "FMCG"]
        },
        "india_reason": (
            "Gold rise = safe-haven buying = risk-off signal for equities. "
            "Jewellery stocks (Titan, Kalyan) rally on higher gold prices. "
            "However sustained gold rally signals fear → equity negative."
        ),
        "expected_nifty_move": "-0.3% to -0.8%",
        "lag": "Same session"
    },

    # ── CHINA MARKETS ────────────────────────────────────────────────────
    {
        "id": "CHINA_CRASH",
        "trigger": "china_index_down_critical",
        "description": "Shanghai/Shenzhen falls >3%",
        "direction": "NEGATIVE",
        "magnitude": "HIGH",
        "sectors_impacted": {
            "NEGATIVE": ["METALS", "MINING", "CHEMICALS"],
            "POSITIVE": [],
            "NEUTRAL":  ["IT", "BANKING", "FMCG"]
        },
        "india_reason": (
            "China is the world's largest commodity consumer. "
            "China crash → commodity prices fall → metal stocks crash globally. "
            "Indian metal companies (Tata Steel, Hindalco, JSW) follow. "
            "Also EM risk-off sentiment drags India."
        ),
        "expected_nifty_move": "-0.5% to -2%",
        "lag": "Same day (markets overlap)"
    },

    # ── FED / INTEREST RATES ─────────────────────────────────────────────
    {
        "id": "US_RATES_RISE_SIGNAL",
        "trigger": "us_bond_yield_spike",
        "description": "US 10Y bond yield spikes sharply",
        "direction": "NEGATIVE",
        "magnitude": "HIGH",
        "sectors_impacted": {
            "NEGATIVE": ["BANKING", "NBFC", "REALTY", "AUTO"],
            "POSITIVE": [],
            "NEUTRAL":  ["IT", "PHARMA", "FMCG"]
        },
        "india_reason": (
            "Higher US rates → FIIs move money from India to US Treasuries "
            "(safer, higher return). INR weakens. RBI forced to raise rates. "
            "Rate-sensitive sectors (Banking, NBFCs, Realty) fall hardest."
        ),
        "expected_nifty_move": "-1% to -2.5%",
        "lag": "Next session"
    },

    # ── GLOBAL SELLOFF ───────────────────────────────────────────────────
    {
        "id": "GLOBAL_SELLOFF",
        "trigger": "global_selloff_detected",
        "description": "5+ global indices falling simultaneously",
        "direction": "NEGATIVE",
        "magnitude": "EXTREME",
        "sectors_impacted": {
            "NEGATIVE": ["IT", "METALS", "BANKING", "AUTO", "REALTY", "NBFC"],
            "POSITIVE": ["FMCG", "PHARMA"],
            "NEUTRAL":  ["POWER", "TELECOM"]
        },
        "india_reason": (
            "Coordinated global selloff = systemic risk event. "
            "FIIs liquidate all EM positions. India VIX spikes. "
            "Only defensive and domestic consumption stocks hold value. "
            "Circuit breakers at -10% and -15% on Nifty possible."
        ),
        "expected_nifty_move": "-3% to -10%",
        "lag": "Next open — guaranteed gap down"
    },
]

# -----------------------------------------------------------------------
# Helper: get rule by trigger ID
# -----------------------------------------------------------------------

def get_rules_by_trigger(trigger_id: str) -> list:
    return [r for r in GLOBAL_IMPACT_RULES if r["trigger"] == trigger_id]


def get_all_rules() -> list:
    return GLOBAL_IMPACT_RULES


def get_sector_stocks(sector: str) -> list:
    return SECTOR_STOCKS.get(sector.upper(), [])


def get_all_sectors() -> list:
    return list(SECTOR_STOCKS.keys())
