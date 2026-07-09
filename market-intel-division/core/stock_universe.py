"""
stock_universe.py
-----------------
Fetches and maintains the complete list of ALL NSE-listed companies.
Auto-updates: new IPOs added, delisted removed.
~2000+ stocks tracked.
"""

import json
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# NSE official list endpoint (CSV of all listed equities)
NSE_EQUITY_LIST_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

# Backup: Well-known Nifty 500 stocks (if NSE download fails)
NIFTY500_BACKUP = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR",
    "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK",
    "BAJFINANCE", "MARUTI", "ASIANPAINT", "HCLTECH", "WIPRO", "TITAN",
    "SUNPHARMA", "NESTLEIND", "ULTRACEMCO", "TATAMOTORS", "NTPC", "ONGC",
    "POWERGRID", "TATASTEEL", "JSWSTEEL", "HINDALCO", "ADANIENT", "ADANIPORTS",
    "ADANIGREEN", "BAJAJFINSV", "TECHM", "DIVISLAB", "DRREDDY", "CIPLA",
    "BRITANNIA", "EICHERMOT", "COALINDIA", "M&M", "INDUSINDBK", "GRASIM",
    "HEROMOTOCO", "BPCL", "TATACONSUM", "APOLLOHOSP", "SBILIFE", "UPL",
    "BAJAJ-AUTO", "HAL", "BEL", "IRFC", "IRCTC", "SUZLON", "ZOMATO",
    "PAYTM", "NYKAA", "POLICYBZR", "TRENT", "TATAELXSI", "DIXON",
    "JIOFIN", "VBL", "MARICO", "DABUR", "GODREJPROP", "DLF",
    "PIIND", "CHOLAFIN", "MUTHOOTFIN", "MANAPPURAM", "INDIGO",
    "FEDERALBNK", "IDFCFIRSTB", "BANKBARODA", "PNB", "CANBK",
    "VEDL", "NMDC", "SAIL", "NATIONALUM", "ABCAPITAL", "RECLTD",
    "PFC", "NHPC", "SJVN", "TORNTPOWER", "TATAPOWER", "ADANIPOWER",
    "OBEROIRLTY", "PRESTIGE", "BRIGADE", "GODREJCP", "COLPAL",
    "LUPIN", "AUROPHARMA", "BIOCON", "IPCALAB", "ALKEM",
    "ESCORTS", "ASHOKLEY", "TATACHEM", "ATUL", "PIDILITIND",
    "MPHASIS", "COFORGE", "LTIM", "PERSISTENT", "HAPPSTMNDS",
    "DELHIVERY", "STARHEALTH", "HDFCAMC", "ICICIGI", "SBICARD",
    "MCX", "BSE", "CDSL", "KPITTECH", "SONACOMS", "EXIDEIND",
    "AMARAJABAT", "MRF", "CEATLTD", "APOLLOTYRE", "BALKRISIND",
    "CONCOR", "MOTHERSON", "BHEL", "SIEMENS", "ABB", "CGPOWER",
    "CUMMINSIND", "THERMAX", "GRINDWELL", "ASTRAL", "POLYCAB",
    "KEI", "HAVELLS", "VOLTAS", "WHIRLPOOL", "BLUESTARCO",
    "CROMPTON", "ORIENTELEC", "CENTURYTEX", "AARTIDRUGS",
    "AAVAS", "AARTIIND", "ACC", "AMBUJACEM", "RAMCOCEM",
    "SHREECEM", "DALBHARAT", "JKCEMENT", "NUVOCO",
]

CACHE_FILE = "config/nse_stocks.json"


class StockUniverse:
    """
    Manages the complete list of ALL NSE-listed stocks.
    Auto-fetches from NSE. Falls back to Nifty500 if fetch fails.
    """

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.cache_path = self.base_dir / CACHE_FILE
        self.stocks = []

    def get_all_stocks(self) -> list:
        """
        Get full list of NSE stock symbols.
        Tries: 1) NSE download  2) Local cache  3) Backup list
        """
        # Try fetching fresh from NSE
        stocks = self._fetch_from_nse()
        if stocks and len(stocks) > 500:
            self.stocks = stocks
            self._save_cache(stocks)
            logger.info(f"NSE Universe: {len(stocks)} stocks (fresh download)")
            return stocks

        # Fall back to cache
        cached = self._load_cache()
        if cached and len(cached) > 100:
            self.stocks = cached
            logger.info(f"NSE Universe: {len(cached)} stocks (from cache)")
            return cached

        # Final fallback
        self.stocks = NIFTY500_BACKUP
        logger.warning(f"Using backup list: {len(NIFTY500_BACKUP)} stocks")
        return NIFTY500_BACKUP

    def get_nifty50(self) -> list:
        """Get only Nifty 50 stocks."""
        return NIFTY500_BACKUP[:50]

    def get_nifty500(self) -> list:
        """Get Nifty 500 stocks."""
        return NIFTY500_BACKUP

    def get_yf_symbol(self, ticker: str) -> str:
        """Convert NSE ticker to yfinance format."""
        return f"{ticker}.NS"

    def get_yf_symbols(self, tickers: list) -> list:
        """Convert list of NSE tickers to yfinance format."""
        return [f"{t}.NS" for t in tickers]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch_from_nse(self) -> list:
        """Download full equity list from NSE website."""
        try:
            session = requests.Session()
            # First hit NSE homepage to get cookies
            session.get("https://www.nseindia.com", headers=NSE_HEADERS, timeout=10)

            resp = session.get(NSE_EQUITY_LIST_URL, headers=NSE_HEADERS, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"NSE list download failed: HTTP {resp.status_code}")
                return []

            lines = resp.text.strip().split("\n")
            if len(lines) < 10:
                return []

            # Parse CSV: first column is SYMBOL
            stocks = []
            for line in lines[1:]:  # skip header
                parts = line.split(",")
                if parts and parts[0].strip():
                    symbol = parts[0].strip().replace('"', '')
                    if symbol.isalpha() or "&" in symbol or "-" in symbol:
                        stocks.append(symbol)

            return stocks
        except Exception as e:
            logger.warning(f"NSE fetch error: {e}")
            return []

    def _save_cache(self, stocks: list) -> None:
        """Save stock list to local cache file."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "updated": date.today().isoformat(),
                "count":   len(stocks),
                "stocks":  stocks,
            }
            with open(self.cache_path, "w") as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Cache save error: {e}")

    def _load_cache(self) -> list:
        """Load stock list from cache."""
        try:
            if not self.cache_path.exists():
                return []
            with open(self.cache_path) as f:
                data = json.load(f)
            return data.get("stocks", [])
        except:
            return []
