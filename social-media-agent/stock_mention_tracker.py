"""
stock_mention_tracker.py
------------------------
Finds and counts stock ticker mentions in social media text.
Tracks: $AAPL style cashtags, plain mentions (AAPL, Tesla),
        trending tickers, mention velocity (rising fast = signal).
Used by both global and India social media agents.
"""

import re
import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# Global top stocks to watch
# -----------------------------------------------------------------------

GLOBAL_TICKERS = {
    # US Mega caps
    "AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "NVIDIA",
    "GOOGL": "Alphabet", "AMZN": "Amazon", "META": "Meta",
    "TSLA": "Tesla", "JPM": "JPMorgan", "V": "Visa",
    "UNH": "UnitedHealth", "XOM": "ExxonMobil", "WMT": "Walmart",
    "JNJ": "Johnson & Johnson", "PG": "Procter & Gamble",
    "MA": "Mastercard", "HD": "Home Depot", "CVX": "Chevron",
    "ABBV": "AbbVie", "MRK": "Merck", "PFE": "Pfizer",
    "BAC": "Bank of America", "KO": "Coca-Cola", "DIS": "Disney",
    "NFLX": "Netflix", "AMD": "AMD", "INTC": "Intel",
    "CRM": "Salesforce", "ADBE": "Adobe", "PYPL": "PayPal",
    "UBER": "Uber", "ABNB": "Airbnb", "COIN": "Coinbase",
    # Indices
    "SPY": "S&P 500 ETF", "QQQ": "NASDAQ ETF", "IWM": "Russell 2000",
    "VIX": "Volatility Index",
    # Crypto-related
    "BTC": "Bitcoin", "ETH": "Ethereum",
}

INDIA_TICKERS = {
    "RELIANCE": "Reliance Industries", "TCS": "TCS",
    "INFY": "Infosys", "HDFCBANK": "HDFC Bank",
    "ICICIBANK": "ICICI Bank", "HINDUNILVR": "HUL",
    "ITC": "ITC", "SBIN": "SBI", "BAJFINANCE": "Bajaj Finance",
    "KOTAKBANK": "Kotak Bank", "WIPRO": "Wipro",
    "HCLTECH": "HCL Tech", "AXISBANK": "Axis Bank",
    "MARUTI": "Maruti Suzuki", "SUNPHARMA": "Sun Pharma",
    "TATASTEEL": "Tata Steel", "TATAMOTORS": "Tata Motors",
    "NTPC": "NTPC", "ONGC": "ONGC", "LT": "L&T",
    "ADANIPORTS": "Adani Ports", "ADANIENT": "Adani Ent",
    "ADANIGREEN": "Adani Green", "BAJAJFINSV": "Bajaj Finserv",
    "TITAN": "Titan", "ASIANPAINT": "Asian Paints",
    "TECHM": "Tech Mahindra", "NESTLEIND": "Nestle India",
    "ULTRACEMCO": "UltraTech Cement", "BHARTIARTL": "Airtel",
    "JSWSTEEL": "JSW Steel", "HINDALCO": "Hindalco",
    "DRREDDY": "Dr Reddy's", "CIPLA": "Cipla",
    "DIVISLAB": "Divi's Labs", "POWERGRID": "Power Grid",
    "COALINDIA": "Coal India", "M&M": "Mahindra",
    "INDIGO": "IndiGo", "HAL": "HAL", "BEL": "BEL",
    "NIFTY": "Nifty 50", "SENSEX": "BSE Sensex",
    "BANKNIFTY": "Bank Nifty",
}

# Common name → ticker mapping for plain text mentions
NAME_TO_TICKER = {
    "apple": "AAPL", "microsoft": "MSFT", "nvidia": "NVDA",
    "google": "GOOGL", "alphabet": "GOOGL", "amazon": "AMZN",
    "meta": "META", "facebook": "META", "tesla": "TSLA",
    "netflix": "NFLX", "disney": "DIS", "uber": "UBER",
    "bitcoin": "BTC", "ethereum": "ETH", "crypto": "BTC",
    # India names
    "reliance": "RELIANCE", "tcs": "TCS", "infosys": "INFY",
    "hdfc": "HDFCBANK", "icici": "ICICIBANK", "wipro": "WIPRO",
    "sbi": "SBIN", "adani": "ADANIENT", "tata": "TATAMOTORS",
    "bajaj": "BAJFINANCE", "airtel": "BHARTIARTL",
    "indigo": "INDIGO", "zomato": "ZOMATO", "paytm": "PAYTM",
}


class StockMentionTracker:
    """
    Finds stock mentions in social media posts.
    Tracks mention frequency, sentiment per ticker, trending tickers.
    """

    def __init__(self, mode: str = "global"):
        """mode: 'global' or 'india'"""
        self.mode    = mode
        self.tickers = {**GLOBAL_TICKERS, **(INDIA_TICKERS if mode == "india" else {})}
        self._history = defaultdict(list)  # ticker -> list of mention counts over time

    def extract_mentions(self, text: str) -> list:
        """
        Find all stock mentions in text.
        Returns list of ticker symbols found.
        """
        found = set()
        text_upper = text.upper()
        text_lower = text.lower()

        # 1. Cashtag format: $AAPL $RELIANCE
        cashtags = re.findall(r'\$([A-Z]{1,10})', text_upper)
        for tag in cashtags:
            if tag in self.tickers:
                found.add(tag)

        # 2. Plain ticker in text: "AAPL is going up"
        words = re.findall(r'\b([A-Z]{2,10})\b', text_upper)
        for word in words:
            if word in self.tickers:
                found.add(word)

        # 3. Company name mentions: "Tesla is bullish"
        for name, ticker in NAME_TO_TICKER.items():
            if name in text_lower and ticker in self.tickers:
                found.add(ticker)

        return list(found)

    def count_mentions(self, posts: list) -> dict:
        """
        Count how many posts mention each ticker.
        Returns dict: ticker -> mention count.
        """
        counts = Counter()
        for post in posts:
            text = post.get("text", "") if isinstance(post, dict) else str(post)
            mentioned = self.extract_mentions(text)
            counts.update(mentioned)
        return dict(counts.most_common(20))

    def get_trending(self, posts: list, top_n: int = 10) -> list:
        """
        Get top trending tickers by mention count.
        Returns list of dicts with ticker, name, count, rank.
        """
        counts = self.count_mentions(posts)
        trending = []
        for rank, (ticker, count) in enumerate(
            sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n], 1
        ):
            trending.append({
                "rank":    rank,
                "ticker":  ticker,
                "name":    self.tickers.get(ticker, ticker),
                "mentions": count,
            })
        return trending

    def get_sentiment_per_ticker(self, posts: list,
                                  analyzer) -> dict:
        """
        For each mentioned ticker, collect all posts mentioning it
        and compute aggregate sentiment.
        Returns: ticker -> sentiment_dict.
        """
        ticker_posts = defaultdict(list)

        for post in posts:
            text = post.get("text", "") if isinstance(post, dict) else str(post)
            mentioned = self.extract_mentions(text)
            for ticker in mentioned:
                ticker_posts[ticker].append(text)

        result = {}
        for ticker, texts in ticker_posts.items():
            sentiment = analyzer.analyze_batch(texts)
            sentiment["ticker"]   = ticker
            sentiment["name"]     = self.tickers.get(ticker, ticker)
            sentiment["mentions"] = len(texts)
            result[ticker] = sentiment

        # Sort by mention count
        return dict(
            sorted(result.items(), key=lambda x: x[1]["mentions"], reverse=True)
        )
