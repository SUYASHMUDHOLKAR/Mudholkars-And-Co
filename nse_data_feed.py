"""
nse_data_feed.py
----------------
Fetches REAL data from NSE India website:
  1. FII/DII daily buying/selling data
  2. Options chain (call/put OI, volume, unusual activity)

No API key needed. Free. Direct from NSE.
Includes retry/backoff to handle NSE rate-limiting and blocks.
"""

import time
import logging
import requests
import json
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

# Retry configuration
MAX_RETRIES = 3
BACKOFF_BASE = 2  # seconds: 2, 4, 8


def _retry_with_backoff(func):
    """Decorator: retry a function with exponential backoff on failure."""
    def wrapper(*args, **kwargs):
        last_error = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except (requests.exceptions.RequestException, requests.exceptions.Timeout,
                    requests.exceptions.ConnectionError, json.JSONDecodeError) as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    wait = BACKOFF_BASE ** attempt
                    logger.warning(f"  NSE retry {attempt}/{MAX_RETRIES} after {wait}s: {e}")
                    time.sleep(wait)
                else:
                    logger.error(f"  NSE failed after {MAX_RETRIES} retries: {e}")
        raise last_error if last_error else RuntimeError("NSE fetch failed")
    return wrapper


class NSEDataFeed:
    """Fetches live data directly from NSE India website with retry/backoff."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(NSE_HEADERS)
        self._init_session()

    def _init_session(self):
        """Hit NSE homepage first to get cookies (required). Retries on failure."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get("https://www.nseindia.com", timeout=10)
                if resp.status_code == 200:
                    return
            except Exception as e:
                if attempt < MAX_RETRIES:
                    wait = BACKOFF_BASE ** attempt
                    logger.warning(f"  NSE session init retry {attempt}: {e} (waiting {wait}s)")
                    time.sleep(wait)
                else:
                    logger.error(f"  NSE session init failed after {MAX_RETRIES} retries")

    def _get_with_retry(self, url: str, timeout: int = 12) -> Optional[requests.Response]:
        """GET request with automatic retry and session refresh."""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, timeout=timeout)
                if resp.status_code == 200:
                    return resp
                elif resp.status_code in (401, 403):
                    # Session expired — refresh cookies
                    logger.info(f"  NSE session expired (HTTP {resp.status_code}), refreshing...")
                    self._init_session()
                elif resp.status_code == 429:
                    # Rate limited
                    wait = BACKOFF_BASE ** (attempt + 1)  # longer wait for rate limit
                    logger.warning(f"  NSE rate limited (429). Waiting {wait}s...")
                    time.sleep(wait)
                else:
                    logger.warning(f"  NSE HTTP {resp.status_code} for {url}")
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
                if attempt < MAX_RETRIES:
                    wait = BACKOFF_BASE ** attempt
                    logger.warning(f"  NSE retry {attempt}/{MAX_RETRIES}: {e} (waiting {wait}s)")
                    time.sleep(wait)
                    # Refresh session on connection errors
                    self._init_session()
                else:
                    logger.error(f"  NSE request failed after {MAX_RETRIES} retries: {url}")
                    return None
        return None

    # ═══════════════════════════════════════════════════════════
    # FII/DII DAILY DATA
    # ═══════════════════════════════════════════════════════════

    def get_fii_dii_data(self) -> dict:
        """
        Get today's FII and DII buying/selling data.
        Returns:
          - FII net buy/sell in ₹ crore
          - DII net buy/sell in ₹ crore
          - Signal: FII_BUYING / FII_SELLING / NEUTRAL
        """
        try:
            url = "https://www.nseindia.com/api/fiidiiTradeReact"
            resp = self._get_with_retry(url)

            if not resp or resp.status_code != 200:
                # Fallback URL
                url = "https://www.nseindia.com/api/fiidiiActivity"
                resp = self._get_with_retry(url)

            if not resp or resp.status_code != 200:
                return self._fii_fallback()

            data = resp.json()
            fii_buy = 0
            fii_sell = 0
            dii_buy = 0
            dii_sell = 0

            for item in data if isinstance(data, list) else [data]:
                category = item.get("category", "").upper()
                if "FII" in category or "FPI" in category:
                    fii_buy = float(item.get("buyValue", 0) or 0)
                    fii_sell = float(item.get("sellValue", 0) or 0)
                elif "DII" in category:
                    dii_buy = float(item.get("buyValue", 0) or 0)
                    dii_sell = float(item.get("sellValue", 0) or 0)

            fii_net = fii_buy - fii_sell
            dii_net = dii_buy - dii_sell

            if fii_net > 500:
                signal = "FII_STRONG_BUYING"
                market_impact = "BULLISH"
            elif fii_net > 0:
                signal = "FII_BUYING"
                market_impact = "MILD_BULLISH"
            elif fii_net < -500:
                signal = "FII_STRONG_SELLING"
                market_impact = "BEARISH"
            elif fii_net < 0:
                signal = "FII_SELLING"
                market_impact = "MILD_BEARISH"
            else:
                signal = "NEUTRAL"
                market_impact = "NEUTRAL"

            return {
                "fii_buy_cr": round(fii_buy, 2),
                "fii_sell_cr": round(fii_sell, 2),
                "fii_net_cr": round(fii_net, 2),
                "dii_buy_cr": round(dii_buy, 2),
                "dii_sell_cr": round(dii_sell, 2),
                "dii_net_cr": round(dii_net, 2),
                "signal": signal,
                "market_impact": market_impact,
                "interpretation": self._interpret_fii_dii(fii_net, dii_net),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        except Exception as e:
            logger.warning(f"FII/DII fetch error: {e}")
            return self._fii_fallback()

    def _fii_fallback(self) -> dict:
        """Fallback if NSE API is down."""
        return {
            "signal": "UNKNOWN",
            "market_impact": "NEUTRAL",
            "error": "NSE API unavailable",
            "interpretation": "Cannot determine FII/DII flow. Use other signals.",
        }

    def _interpret_fii_dii(self, fii_net: float, dii_net: float) -> str:
        if fii_net > 1000:
            return "FII aggressively buying. Strong bullish signal for next session."
        elif fii_net > 500:
            return "FII net buyers. Market likely to be positive."
        elif fii_net < -1000:
            return "FII heavy selling. Expect market pressure. Be cautious."
        elif fii_net < -500:
            return "FII selling. Mild bearish pressure expected."
        elif dii_net > 1000 and fii_net < 0:
            return "DII supporting market against FII selling. Sideways expected."
        else:
            return "Mixed signals. No strong directional bias."

    # ═══════════════════════════════════════════════════════════
    # OPTIONS CHAIN DATA
    # ═══════════════════════════════════════════════════════════

    def get_options_chain(self, symbol: str = "NIFTY") -> dict:
        """
        Fetch options chain for a symbol from NSE.
        Detects: unusual call/put activity, PCR, max pain.

        symbol: NIFTY, BANKNIFTY, RELIANCE, TCS, etc.
        """
        try:
            url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
            if symbol not in ("NIFTY", "BANKNIFTY", "FINNIFTY"):
                url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"

            resp = self._get_with_retry(url, timeout=15)
            if not resp or resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code if resp else 'timeout'}", "symbol": symbol}

            data = resp.json()
            records = data.get("records", {})
            chain_data = records.get("data", [])
            expiry_dates = records.get("expiryDates", [])

            if not chain_data:
                return {"error": "No data", "symbol": symbol}

            # Current expiry (nearest)
            current_expiry = expiry_dates[0] if expiry_dates else None

            # Aggregate for current expiry
            total_call_oi = 0
            total_put_oi = 0
            total_call_vol = 0
            total_put_vol = 0
            max_call_oi_strike = 0
            max_call_oi = 0
            max_put_oi_strike = 0
            max_put_oi = 0
            unusual_activity = []

            for row in chain_data:
                if row.get("expiryDate") != current_expiry:
                    continue

                ce = row.get("CE", {})
                pe = row.get("PE", {})
                strike = row.get("strikePrice", 0)

                ce_oi = ce.get("openInterest", 0) or 0
                pe_oi = pe.get("openInterest", 0) or 0
                ce_vol = ce.get("totalTradedVolume", 0) or 0
                pe_vol = pe.get("totalTradedVolume", 0) or 0
                ce_oi_chg = ce.get("changeinOpenInterest", 0) or 0
                pe_oi_chg = pe.get("changeinOpenInterest", 0) or 0

                total_call_oi += ce_oi
                total_put_oi += pe_oi
                total_call_vol += ce_vol
                total_put_vol += pe_vol

                if ce_oi > max_call_oi:
                    max_call_oi = ce_oi
                    max_call_oi_strike = strike
                if pe_oi > max_put_oi:
                    max_put_oi = pe_oi
                    max_put_oi_strike = strike

                # Detect unusual activity (OI change > 10 lakh)
                if abs(ce_oi_chg) > 1000000:
                    unusual_activity.append({
                        "type": "CALL",
                        "strike": strike,
                        "oi_change": ce_oi_chg,
                        "signal": "BULLISH" if ce_oi_chg > 0 else "UNWINDING",
                    })
                if abs(pe_oi_chg) > 1000000:
                    unusual_activity.append({
                        "type": "PUT",
                        "strike": strike,
                        "oi_change": pe_oi_chg,
                        "signal": "BEARISH" if pe_oi_chg > 0 else "SHORT_COVERING",
                    })

            # Put-Call Ratio
            pcr = total_put_oi / total_call_oi if total_call_oi else 0

            # Interpretation
            if pcr >= 1.3:
                pcr_signal = "STRONG_BULLISH"
                interpretation = "High PCR = heavy put writing = market support. Bullish."
            elif pcr >= 1.0:
                pcr_signal = "BULLISH"
                interpretation = "PCR > 1 indicates bullish sentiment."
            elif pcr <= 0.7:
                pcr_signal = "BEARISH"
                interpretation = "Low PCR = more calls than puts = bearish sentiment."
            else:
                pcr_signal = "NEUTRAL"
                interpretation = "PCR neutral. No strong directional bias."

            # Max Pain (approximate)
            max_pain = (max_call_oi_strike + max_put_oi_strike) / 2

            return {
                "symbol": symbol,
                "expiry": current_expiry,
                "pcr": round(pcr, 3),
                "pcr_signal": pcr_signal,
                "total_call_oi": total_call_oi,
                "total_put_oi": total_put_oi,
                "max_call_oi_strike": max_call_oi_strike,
                "max_put_oi_strike": max_put_oi_strike,
                "max_pain": round(max_pain, 0),
                "unusual_activity": unusual_activity[:5],
                "interpretation": interpretation,
                "market_signal": pcr_signal,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        except Exception as e:
            logger.warning(f"Options chain error for {symbol}: {e}")
            return {"error": str(e), "symbol": symbol}

    def get_stock_options_signal(self, symbol: str) -> dict:
        """
        Quick signal from options data for a specific stock.
        High call OI build-up at a strike = resistance.
        High put OI build-up = support.
        """
        chain = self.get_options_chain(symbol)
        if chain.get("error"):
            return {"signal": "UNKNOWN", "pcr": 0}

        return {
            "symbol": symbol,
            "signal": chain.get("pcr_signal", "NEUTRAL"),
            "pcr": chain.get("pcr", 0),
            "max_pain": chain.get("max_pain", 0),
            "resistance": chain.get("max_call_oi_strike", 0),
            "support": chain.get("max_put_oi_strike", 0),
            "unusual": chain.get("unusual_activity", []),
            "interpretation": chain.get("interpretation", ""),
        }

    # ═══════════════════════════════════════════════════════════
    # COMBINED MARKET SIGNAL
    # ═══════════════════════════════════════════════════════════

    def get_market_signal(self) -> dict:
        """
        Combined signal from FII/DII + Nifty Options + BankNifty Options.
        The ULTIMATE market direction predictor.
        """
        fii = self.get_fii_dii_data()
        nifty_options = self.get_options_chain("NIFTY")
        banknifty_options = self.get_options_chain("BANKNIFTY")

        signals = []
        if fii.get("market_impact") == "BULLISH":
            signals.append("BULL")
        elif fii.get("market_impact") == "BEARISH":
            signals.append("BEAR")

        if nifty_options.get("pcr_signal") in ("STRONG_BULLISH", "BULLISH"):
            signals.append("BULL")
        elif nifty_options.get("pcr_signal") == "BEARISH":
            signals.append("BEAR")

        bull_count = signals.count("BULL")
        bear_count = signals.count("BEAR")

        if bull_count >= 2:
            combined = "STRONG_BULLISH"
            action = "Aggressive buying. FII + Options both confirm upside."
        elif bull_count == 1:
            combined = "MILD_BULLISH"
            action = "Cautious buying. One signal confirms."
        elif bear_count >= 2:
            combined = "STRONG_BEARISH"
            action = "AVOID buying. FII selling + Options bearish."
        elif bear_count == 1:
            combined = "MILD_BEARISH"
            action = "Reduce exposure. One bearish signal."
        else:
            combined = "NEUTRAL"
            action = "Wait for clearer signals."

        return {
            "combined_signal": combined,
            "action": action,
            "fii_dii": fii,
            "nifty_pcr": nifty_options.get("pcr", 0),
            "nifty_pcr_signal": nifty_options.get("pcr_signal", "UNKNOWN"),
            "nifty_max_pain": nifty_options.get("max_pain", 0),
            "nifty_support": nifty_options.get("max_put_oi_strike", 0),
            "nifty_resistance": nifty_options.get("max_call_oi_strike", 0),
            "unusual_activity": nifty_options.get("unusual_activity", []),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
