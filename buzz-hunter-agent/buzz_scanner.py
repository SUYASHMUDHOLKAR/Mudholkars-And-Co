"""
buzz_scanner.py
---------------
Scans the internet for stock buzz from every possible free source.
This agent's ONLY job: find which stocks are buzzing RIGHT NOW.

Sources:
  - Financial news RSS (mentions = buzz)
  - Google Trends (search interest spikes)
  - Yahoo Finance volume spikes (unusual trading activity)
  - Yahoo Finance gainers/losers (price momentum)
  - Finviz screener (most active, top gainers)
"""

import re
import logging
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Optional

import requests
import feedparser
import yfinance as yf

try:
    from pytrends.request import TrendReq
    PYTRENDS_OK = True
except ImportError:
    PYTRENDS_OK = False

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

# RSS sources to scan for stock mentions (buzz = how many times a stock appears)
BUZZ_RSS_SOURCES = [
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.livemint.com/rss/markets",
    "https://feeds.feedburner.com/ndtvprofit-latest",
    "https://in.investing.com/rss/news_25.rss",
    "https://www.investing.com/rss/news.rss",
    "https://seekingalpha.com/market_currents.xml",
    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://www.thehindu.com/business/feeder/default.rss",
]

# India stocks to scan for buzz
INDIA_STOCKS = [
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN",
    "BAJFINANCE", "ITC", "WIPRO", "HCLTECH", "TATAMOTORS", "MARUTI",
    "SUNPHARMA", "AXISBANK", "KOTAKBANK", "TATASTEEL", "LT", "ONGC",
    "NTPC", "ADANIENT", "ADANIPORTS", "ADANIGREEN", "TITAN", "ASIANPAINT",
    "HINDUNILVR", "BHARTIARTL", "JSWSTEEL", "HINDALCO", "DRREDDY", "CIPLA",
    "COALINDIA", "POWERGRID", "TECHM", "DIVISLAB", "EICHERMOT", "M&M",
    "NESTLEIND", "ULTRACEMCO", "BAJAJFINSV", "INDIGO", "HAL", "BEL",
    "IRFC", "SUZLON", "ZOMATO", "PAYTM", "NYKAA", "POLICYBZR",
    "TATAELXSI", "DIXON", "JIOFIN", "TRENT", "VBL", "IRCTC",
]

GLOBAL_STOCKS = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA",
    "JPM", "AMD", "INTC", "NFLX", "DIS", "PYPL", "UBER",
    "COIN", "PLTR", "GME", "AMC", "SOFI", "RIVN", "NIO",
    "SMCI", "ARM", "SNOW", "CRWD", "PANW",
]

# Common company name → ticker
NAME_MAP = {
    "reliance": "RELIANCE", "tcs": "TCS", "infosys": "INFY",
    "hdfc": "HDFCBANK", "icici": "ICICIBANK", "sbi": "SBIN",
    "adani": "ADANIENT", "tata motors": "TATAMOTORS", "tata steel": "TATASTEEL",
    "bajaj finance": "BAJFINANCE", "wipro": "WIPRO", "airtel": "BHARTIARTL",
    "zomato": "ZOMATO", "paytm": "PAYTM", "suzlon": "SUZLON",
    "irfc": "IRFC", "hal": "HAL", "titan": "TITAN",
    "apple": "AAPL", "microsoft": "MSFT", "nvidia": "NVDA",
    "google": "GOOGL", "amazon": "AMZN", "tesla": "TSLA",
    "meta": "META", "netflix": "NFLX", "coinbase": "COIN",
    "palantir": "PLTR", "gamestop": "GME",
}


class BuzzScanner:
    """Scans the internet for stock buzz. That's ALL it does."""

    def __init__(self):
        self.all_tickers = set(INDIA_STOCKS + GLOBAL_STOCKS)

    # ------------------------------------------------------------------
    # 1. News Mention Buzz — which stocks appear most in headlines today
    # ------------------------------------------------------------------

    def scan_news_buzz(self) -> dict:
        """Count how many times each stock appears across all news sources."""
        logger.info("Scanning news for stock mentions...")
        mention_counts = Counter()
        headlines = []

        for url in BUZZ_RSS_SOURCES:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=8)
                if resp.status_code != 200:
                    continue
                feed = feedparser.parse(resp.content)
                for entry in feed.entries[:15]:
                    title   = getattr(entry, "title", "")
                    summary = getattr(entry, "summary", "") or ""
                    text    = f"{title} {re.sub(r'<[^>]+>', '', summary)}".lower()
                    headlines.append(text)

                    # Find ticker mentions
                    for ticker in self.all_tickers:
                        if ticker.lower() in text:
                            mention_counts[ticker] += 1
                    for name, ticker in NAME_MAP.items():
                        if name in text:
                            mention_counts[ticker] += 1

                time.sleep(0.2)
            except:
                continue

        logger.info(f"Scanned {len(headlines)} headlines, found {len(mention_counts)} tickers mentioned")
        return dict(mention_counts.most_common(30))

    # ------------------------------------------------------------------
    # 2. Volume Buzz — which stocks have unusual trading volume today
    # ------------------------------------------------------------------

    def scan_volume_buzz(self, tickers: list = None) -> list:
        """Find stocks with unusual volume spikes (2x+ average)."""
        logger.info("Scanning for volume spikes...")
        tickers = tickers or (INDIA_STOCKS[:20] + GLOBAL_STOCKS[:15])
        buzzing = []

        for ticker in tickers:
            try:
                symbol = f"{ticker}.NS" if ticker in INDIA_STOCKS else ticker
                t = yf.Ticker(symbol)
                hist = t.history(period="35d", interval="1d")
                if hist.empty or len(hist) < 5:
                    continue

                today_vol = float(hist["Volume"].iloc[-1])
                avg_vol   = float(hist["Volume"].iloc[:-1].tail(30).mean())
                if avg_vol == 0:
                    continue

                ratio = today_vol / avg_vol
                if ratio >= 2.0:
                    price    = float(hist["Close"].iloc[-1])
                    prev     = float(hist["Close"].iloc[-2])
                    pct_chg  = ((price - prev) / prev * 100) if prev else 0

                    buzzing.append({
                        "ticker":       ticker,
                        "volume_ratio": round(ratio, 1),
                        "today_volume": int(today_vol),
                        "avg_volume":   int(avg_vol),
                        "price":        round(price, 2),
                        "pct_change":   round(pct_chg, 2),
                        "signal":       "EXTREME_VOLUME" if ratio >= 4 else "HIGH_VOLUME",
                    })
            except:
                continue

        buzzing.sort(key=lambda x: x["volume_ratio"], reverse=True)
        logger.info(f"Volume buzz: {len(buzzing)} stocks with unusual volume")
        return buzzing[:15]

    # ------------------------------------------------------------------
    # 3. Price Momentum Buzz — biggest gainers today (market is talking)
    # ------------------------------------------------------------------

    def scan_price_buzz(self, tickers: list = None) -> dict:
        """Find today's biggest gainers and losers (price buzz)."""
        logger.info("Scanning for price momentum buzz...")
        tickers = tickers or (INDIA_STOCKS[:30] + GLOBAL_STOCKS[:15])
        moves = []

        for ticker in tickers:
            try:
                symbol = f"{ticker}.NS" if ticker in INDIA_STOCKS else ticker
                t = yf.Ticker(symbol)
                hist = t.history(period="5d", interval="1d")
                if len(hist) < 2:
                    continue

                price = float(hist["Close"].iloc[-1])
                prev  = float(hist["Close"].iloc[-2])
                pct   = ((price - prev) / prev * 100) if prev else 0

                moves.append({
                    "ticker":     ticker,
                    "price":      round(price, 2),
                    "pct_change": round(pct, 2),
                })
            except:
                continue

        moves.sort(key=lambda x: abs(x["pct_change"]), reverse=True)
        gainers = [m for m in moves if m["pct_change"] > 1.5][:10]
        losers  = [m for m in moves if m["pct_change"] < -1.5][:10]

        logger.info(f"Price buzz: {len(gainers)} big gainers, {len(losers)} big losers")
        return {"top_gainers": gainers, "top_losers": losers}

    # ------------------------------------------------------------------
    # 4. Google Search Buzz — sudden spike in search interest
    # ------------------------------------------------------------------

    def scan_google_buzz(self, tickers: list = None) -> dict:
        """Check Google Trends for stocks people are suddenly searching."""
        if not PYTRENDS_OK:
            return {}

        keywords = tickers or ["Suzlon share", "IRFC share", "Adani share",
                               "Tata Motors share", "Zomato share",
                               "NVIDIA stock", "Tesla stock", "GameStop stock"]
        try:
            pytrends = TrendReq(hl="en-IN", tz=330)
            results  = {}
            for i in range(0, len(keywords), 5):
                chunk = keywords[i:i+5]
                pytrends.build_payload(chunk, timeframe="now 1-d", geo="IN")
                data = pytrends.interest_over_time()
                if not data.empty:
                    for kw in chunk:
                        if kw in data.columns:
                            results[kw] = int(data[kw].iloc[-1])
                time.sleep(1)
            logger.info(f"Google buzz: {len(results)} keywords tracked")
            return results
        except Exception as e:
            logger.warning(f"Google Trends error: {e}")
            return {}

    # ------------------------------------------------------------------
    # Full scan
    # ------------------------------------------------------------------

    def scan_all(self) -> dict:
        """Run all buzz scans and return combined data."""
        logger.info("=" * 50)
        logger.info("BUZZ HUNTER — Full internet scan starting...")
        logger.info("=" * 50)

        news_buzz   = self.scan_news_buzz()
        volume_buzz = self.scan_volume_buzz()
        price_buzz  = self.scan_price_buzz()
        google_buzz = self.scan_google_buzz()

        return {
            "news_mentions":  news_buzz,
            "volume_spikes":  volume_buzz,
            "price_momentum": price_buzz,
            "google_search":  google_buzz,
            "scanned_at":     datetime.utcnow().isoformat() + "Z",
        }
