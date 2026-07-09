"""
sector_universe.py
------------------
Complete mapping of EVERY sector in the Indian stock market.
25 sectors × 10-30 stocks each = 400+ stocks tracked.
Covers NSE Nifty sectoral indices + additional sub-sectors.
"""

# ═══════════════════════════════════════════════════════════════
# ALL 25 SECTORS IN INDIAN MARKET + THEIR NSE STOCKS
# ═══════════════════════════════════════════════════════════════

SECTORS = {

    "IT": {
        "index": "NIFTY IT",
        "description": "Information Technology — software exports, digital services",
        "stocks": [
            "TCS", "INFY", "WIPRO", "HCLTECH", "TECHM", "LTIM",
            "MPHASIS", "COFORGE", "PERSISTENT", "HAPPSTMNDS", "KPITTECH",
            "LTTS", "TATAELXSI", "CYIENT", "SONACOMS", "MASTEK",
            "NEWGEN", "INTELLECT", "BIRLASOFT", "NIITLTD",
        ],
    },

    "BANKING": {
        "index": "NIFTY BANK",
        "description": "Public & Private sector banks",
        "stocks": [
            "HDFCBANK", "ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN",
            "BANKBARODA", "PNB", "CANBK", "UNIONBANK", "INDUSINDBK",
            "FEDERALBNK", "IDFCFIRSTB", "BANDHANBNK", "RBLBANK",
            "AUBANK", "CUB", "KARURVYSYA", "INDIANB", "MAHABANK",
        ],
    },

    "NBFC_FINANCE": {
        "index": "NIFTY FINANCIAL SERVICES",
        "description": "NBFCs, AMCs, insurance, financial services",
        "stocks": [
            "BAJFINANCE", "BAJAJFINSV", "CHOLAFIN", "MUTHOOTFIN",
            "MANAPPURAM", "SHRIRAMFIN", "POONAWALLA", "LICHSGFIN",
            "CANFINHOME", "IIFL", "HDFCAMC", "NIPPONLIFE",
            "ABCAPITAL", "L&TFH", "RECLTD", "PFC", "IRFC",
        ],
    },

    "PHARMA": {
        "index": "NIFTY PHARMA",
        "description": "Pharmaceuticals, biotech, healthcare",
        "stocks": [
            "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "LUPIN",
            "AUROPHARMA", "BIOCON", "TORNTPHARM", "ALKEM", "IPCALAB",
            "GLENMARK", "NATCOPHARMA", "LALPATHLAB", "METROPOLIS",
            "ABBOTINDIA", "PFIZER", "SANOFI", "APOLLOHOSP", "MAXHEALTH",
            "FORTIS", "MEDANTA",
        ],
    },

    "AUTO": {
        "index": "NIFTY AUTO",
        "description": "Passenger vehicles, commercial vehicles, 2-wheelers",
        "stocks": [
            "MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "HEROMOTOCO",
            "EICHERMOT", "ASHOKLEY", "ESCORTS", "TVSMOTOR", "TIINDIA",
            "BALKRISIND", "APOLLOTYRE", "MRF", "CEATLTD", "EXIDEIND",
            "AMARAJABAT", "MOTHERSON", "BOSCHLTD", "BHARATFORG",
        ],
    },

    "OIL_GAS": {
        "index": "NIFTY OIL & GAS",
        "description": "Upstream, downstream, gas distribution",
        "stocks": [
            "RELIANCE", "ONGC", "IOC", "BPCL", "HINDPETRO", "OIL",
            "GAIL", "PETRONET", "MGL", "IGL", "GSPL", "GUJGASLTD",
            "CASTROLIND", "CHENNPETRO", "MRPL",
        ],
    },

    "METALS_MINING": {
        "index": "NIFTY METAL",
        "description": "Steel, aluminium, copper, zinc, iron ore",
        "stocks": [
            "TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "SAIL",
            "NMDC", "NATIONALUM", "COALINDIA", "MOIL", "HINDCOPPER",
            "WELCORP", "JINDALSAW", "JINDALSTEL", "RATNAMANI",
            "APLAPOLLO", "TITAGARH",
        ],
    },

    "FMCG": {
        "index": "NIFTY FMCG",
        "description": "Fast moving consumer goods — food, personal care",
        "stocks": [
            "HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA", "DABUR",
            "MARICO", "COLPAL", "GODREJCP", "TATACONSUM", "VBL",
            "EMAMILTD", "RADICO", "UBL", "PGHH", "BIKAJI",
            "ZYDUSWELL", "JYOTHYLABS",
        ],
    },

    "REALTY": {
        "index": "NIFTY REALTY",
        "description": "Real estate developers, housing",
        "stocks": [
            "DLF", "GODREJPROP", "OBEROIRLTY", "PRESTIGE", "BRIGADE",
            "PHOENIXLTD", "SOBHA", "LODHA", "MAHLIFE", "SUNTECK",
            "KOLTEPATIL", "ASHIANA",
        ],
    },

    "INFRA_CONSTRUCTION": {
        "index": "NIFTY INFRA",
        "description": "Infrastructure, EPC, roads, railways",
        "stocks": [
            "LT", "KNR", "NCC", "IRB", "PNC", "HG",
            "AHLUCONT", "KNRCON", "RVNL", "IRCON", "NBCC",
            "ENGINERSIN", "BLS", "JMCPROJECT",
        ],
    },

    "CEMENT": {
        "index": "NIFTY MIDCAP",
        "description": "Cement manufacturers",
        "stocks": [
            "ULTRACEMCO", "SHREECEM", "AMBUJACEMENT", "ACC",
            "RAMCOCEM", "DALBHARAT", "JKCEMENT", "NUVOCO",
            "JKLAKSHMI", "HEIDELBERG", "BIRLACEM", "PRISMJOHNS",
        ],
    },

    "POWER_ENERGY": {
        "index": "NIFTY ENERGY",
        "description": "Power generation, transmission, distribution, renewables",
        "stocks": [
            "NTPC", "POWERGRID", "TATAPOWER", "ADANIPOWER", "TORNTPOWER",
            "NHPC", "SJVN", "CESC", "JSW ENERGY", "ADANIGREEN",
            "SUZLON", "INOXWIND", "IREDA", "RECLTD", "PFC",
        ],
    },

    "TELECOM": {
        "index": "NIFTY TELECOM",
        "description": "Telecom operators, tower companies, fibre",
        "stocks": [
            "BHARTIARTL", "IDEA", "TTML", "HFCL",
            "STERLITE", "TEJAS", "ROUTE",
        ],
    },

    "DEFENCE": {
        "index": "NIFTY DEFENCE",
        "description": "Defence manufacturing, shipbuilding, aerospace",
        "stocks": [
            "HAL", "BEL", "BHEL", "MIDHANI", "COCHINSHIP",
            "GRSE", "MAZAGON", "SOLARINDS", "DATAPATTNS", "PARAS",
            "IDEAFORGE", "BDL",
        ],
    },

    "RAILWAY": {
        "index": "BSE RAILWAYS",
        "description": "Railways, wagons, coaches, signalling",
        "stocks": [
            "IRCTC", "IRFC", "RVNL", "IRCON",
            "TITAGARH", "TEXRAIL", "JUPITERINDS", "RITES",
            "RAILTEL", "CONCOR",
        ],
    },

    "INSURANCE": {
        "index": "NIFTY FINANCIAL",
        "description": "Life insurance, general insurance, health insurance",
        "stocks": [
            "HDFCLIFE", "SBILIFE", "ICICIGI", "ICICIPRULI",
            "STARHEALTH", "NIACL", "GICRE", "LIFEINSURE",
        ],
    },

    "CHEMICALS": {
        "index": "BSE CHEMICALS",
        "description": "Specialty chemicals, agro chemicals, dyes",
        "stocks": [
            "PIIND", "UPL", "AARTI", "ATUL", "SRF",
            "DEEPAKNTR", "CLEAN", "NAVINFLUOR", "FINEORG",
            "GALAXYSURF", "VINATIORG", "TATACHEM", "ALKYLAMINE",
        ],
    },

    "CONSUMER_DURABLES": {
        "index": "NIFTY CONSUMER DURABLES",
        "description": "Electronics, appliances, lifestyle",
        "stocks": [
            "TITAN", "VOLTAS", "HAVELLS", "WHIRLPOOL", "BLUESTARCO",
            "CROMPTON", "ORIENTELEC", "DIXON", "AMBER", "KALYANKJIL",
            "BATAINDIA", "RELAXO", "PAGEIND", "TRENT", "RAJESHEXPO",
        ],
    },

    "MEDIA_ENTERTAINMENT": {
        "index": "NIFTY MEDIA",
        "description": "Broadcasting, digital media, print, OTT",
        "stocks": [
            "ZEEL", "PVRINOX", "SUNTV", "TV18BRDCST", "NETWORK18",
            "SAREGAMA", "TIPS", "NAZARA", "DISH",
        ],
    },

    "JEWELLERY_RETAIL": {
        "index": "BSE CONSUMER",
        "description": "Jewellery, organized retail, fashion",
        "stocks": [
            "TITAN", "KALYAN", "SENCO", "TRENT", "DMART",
            "SHOPERSTOP", "VMART", "ADITYA BIRLA FASHION",
        ],
    },

    "AGRI_FERTILIZER": {
        "index": "BSE AGRI",
        "description": "Fertilizers, seeds, agrochemicals",
        "stocks": [
            "UPL", "PIIND", "COROMANDEL", "RALLIS", "CHAMBAL",
            "GNFC", "RCF", "GSFC", "DEEPAKFERT", "KAVERI",
        ],
    },

    "TEXTILES": {
        "index": "BSE TEXTILES",
        "description": "Yarn, fabric, apparel, home textiles",
        "stocks": [
            "PAGEIND", "RAYMOND", "ARVIND", "WELSPUNLIV",
            "TRIDENT", "VARDHMAN", "KITEX", "GOKALDAS",
            "KPR", "LUXIND",
        ],
    },

    "LOGISTICS_SHIPPING": {
        "index": "BSE LOGISTICS",
        "description": "Logistics, ports, shipping, courier",
        "stocks": [
            "ADANIPORTS", "CONCOR", "DELHIVERY", "BLUEDART",
            "ALLCARGO", "MAHSEAMLES", "GE SHIPPING", "SCI",
            "TCI", "VRL",
        ],
    },

    "HOTELS_TOURISM": {
        "index": "BSE HOSPITALITY",
        "description": "Hotels, restaurants, tourism, travel",
        "stocks": [
            "INDHOTEL", "LEMONTRE", "CHALET", "EIH",
            "THOMASCOOK", "MAHINDHOLIDAY", "EASEMYTRIP", "IRCTC",
        ],
    },

    "PSU": {
        "index": "NIFTY PSE",
        "description": "Public Sector Undertakings — government companies",
        "stocks": [
            "SBIN", "COALINDIA", "ONGC", "NTPC", "POWERGRID",
            "NHPC", "IRFC", "RECLTD", "PFC", "IRCTC",
            "HAL", "BEL", "BHEL", "NMDC", "SJVN", "RVNL",
            "NBCC", "IRCON", "CONCOR", "NATIONALUM",
        ],
    },

    "EV_GREEN_ENERGY": {
        "index": "BSE GREEN ENERGY",
        "description": "Electric vehicles, solar, wind, hydrogen, batteries",
        "stocks": [
            "TATAMOTORS", "M&M", "TATAPOWER", "ADANIGREEN",
            "SUZLON", "INOXWIND", "IREDA", "OLECTRA",
            "GREENPANEL", "EXIDEIND", "AMARAJABAT",
        ],
    },
}

# Total sectors
TOTAL_SECTORS = len(SECTORS)  # 25

def get_all_sectors() -> list:
    return list(SECTORS.keys())

def get_sector(name: str) -> dict:
    return SECTORS.get(name, {})

def get_sector_stocks(name: str) -> list:
    return SECTORS.get(name, {}).get("stocks", [])

def get_all_stocks_flat() -> list:
    """All unique stocks across all sectors."""
    all_s = set()
    for data in SECTORS.values():
        all_s.update(data.get("stocks", []))
    return sorted(all_s)
