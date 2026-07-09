"""
india_tracker.py
----------------
Tracks India-specific market indicators that the Scout Agent doesn't focus on.
Specialized for NSE/BSE and Indian market ecosystem.

Tracks:
  - Nifty 50, Sensex (core indices)
  - Nifty Bank, Nifty IT (sector indices)
  - India VIX (fear gauge)
  - SGX Nifty (Singapore futures — predicts India open)
  - USD/INR (rupee strength)
  - FII/DII flows (foreign vs domestic institutional investor activity)
  - Top Nifty50 gainers/losers
"""

import logging
from typing import Optional
from datetime import datetime, date

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


class IndiaTracker:
    """Specialized tracker for NSE/BSE and Indian market signals."""

    def __init__(self):
        # Symbols
        self.nifty50 = "^NSEI"
        self.sensex  = "^BSESN"
        self.nifty_bank = "^NSEBANK"
        self.nifty_it   = "NIFTYIT.NS"
        self.india_vix  = "^INDIAVIX"
        self.sgx_nifty  = "NIFTY50.SI"  # SGX Singapore Nifty futures
        self.usdinr     = "USDINR=X"

        # Top Nifty50 stocks for quick read
        self.nifty50_stocks = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
            "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS",
            "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "MARUTI.NS", "ASIANPAINT.NS",
            "HCLTECH.NS", "WIPRO.NS", "ULTRACEMCO.NS", "TITAN.NS", "SUNPHARMA.NS",
            "NESTLEIND.NS", "TATAMOTORS.NS", "POWERGRID.NS", "NTPC.NS", "ONGC.NS",
            "M&M.NS", "TATASTEEL.NS", "BAJAJFINSV.NS", "TECHM.NS", "HINDALCO.NS",
            "INDUSINDBK.NS", "ADANIENT.NS", "ADANIPORTS.NS", "COALINDIA.NS",
            "JSWSTEEL.NS", "DIVISLAB.NS", "DRREDDY.NS", "APOLLOHOSP.NS",
            "CIPLA.NS", "GRASIM.NS", "EICHERMOT.NS", "BRITANNIA.NS",
            "BPCL.NS", "SHREECEM.NS", "HEROMOTOCO.NS", "UPL.NS",
            "TATACONSUM.NS", "SBILIFE.NS", "VEDL.NS", "LTIM.NS"
        ]

    # ------------------------------------------------------------------
    # Core indices
    # ------------------------------------------------------------------

    def get_nifty_sensex(self) -> dict:
        """Fetch current Nifty50 and Sensex data."""
        try:
            nifty  = yf.Ticker(self.nifty50).history(period="1d", interval="1m")
            sensex = yf.Ticker(self.sensex).history(period="1d", interval="1m")

            if nifty.empty or sensex.empty:
                return {"error": "No data for Nifty/Sensex"}

            n_curr = float(nifty["Close"].iloc[-1])
            s_curr = float(sensex["Close"].iloc[-1])

            # Previous close
            n_hist = yf.Ticker(self.nifty50).history(period="5d", interval="1d")
            s_hist = yf.Ticker(self.sensex).history(period="5d", interval="1d")

            n_prev = float(n_hist["Close"].iloc[-2]) if len(n_hist) >= 2 else n_curr
            s_prev = float(s_hist["Close"].iloc[-2]) if len(s_hist) >= 2 else s_curr

            n_chg = ((n_curr - n_prev) / n_prev * 100) if n_prev else 0
            s_chg = ((s_curr - s_prev) / s_prev * 100) if s_prev else 0

            return {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "nifty50": {
                    "current": round(n_curr, 2),
                    "prev_close": round(n_prev, 2),
                    "change_pct": round(n_chg, 2),
                    "day_high": round(float(nifty["High"].max()), 2),
                    "day_low":  round(float(nifty["Low"].min()), 2),
                },
                "sensex": {
                    "current": round(s_curr, 2),
                    "prev_close": round(s_prev, 2),
                    "change_pct": round(s_chg, 2),
                    "day_high": round(float(sensex["High"].max()), 2),
                    "day_low":  round(float(sensex["Low"].min()), 2),
                }
            }
        except Exception as e:
            logger.error(f"Error fetching Nifty/Sensex: {e}")
            return {"error": str(e)}

    def get_india_vix(self) -> Optional[dict]:
        """India VIX (fear index) — higher = more fear/volatility."""
        try:
            ticker = yf.Ticker(self.india_vix)
            hist = ticker.history(period="5d", interval="1d")
            if hist.empty:
                return None

            curr = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else curr
            chg  = ((curr - prev) / prev * 100) if prev else 0

            level = "LOW"
            if curr >= 25:
                level = "EXTREME"
            elif curr >= 20:
                level = "HIGH"
            elif curr >= 15:
                level = "ELEVATED"

            return {
                "current": round(curr, 2),
                "prev_close": round(prev, 2),
                "change_pct": round(chg, 2),
                "fear_level": level,
            }
        except Exception as e:
            logger.error(f"Error fetching India VIX: {e}")
            return None

    def get_sgx_nifty(self) -> Optional[dict]:
        """
        SGX Nifty (Singapore futures) — trades when NSE is closed.
        Best indicator of where Nifty will open next morning.
        """
        try:
            ticker = yf.Ticker(self.sgx_nifty)
            hist = ticker.history(period="1d", interval="1m")
            if hist.empty:
                return None

            curr = float(hist["Close"].iloc[-1])
            # Compare to last NSE close
            nse = yf.Ticker(self.nifty50).history(period="5d", interval="1d")
            nse_close = float(nse["Close"].iloc[-1])
            premium = curr - nse_close
            premium_pct = (premium / nse_close * 100) if nse_close else 0

            return {
                "sgx_nifty": round(curr, 2),
                "nse_nifty_close": round(nse_close, 2),
                "premium": round(premium, 2),
                "premium_pct": round(premium_pct, 2),
                "signal": "GAP_UP" if premium_pct > 0.5 else ("GAP_DOWN" if premium_pct < -0.5 else "FLAT")
            }
        except Exception as e:
            logger.error(f"Error fetching SGX Nifty: {e}")
            return None

    def get_usdinr(self) -> Optional[dict]:
        """USD/INR — tracks rupee strength/weakness."""
        try:
            ticker = yf.Ticker(self.usdinr)
            hist = ticker.history(period="5d", interval="1d")
            if hist.empty:
                return None

            curr = float(hist["Close"].iloc[-1])
            prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else curr
            chg  = ((curr - prev) / prev * 100) if prev else 0

            trend = "WEAKENING" if chg > 0 else ("STRENGTHENING" if chg < 0 else "STABLE")

            return {
                "usdinr": round(curr, 4),
                "prev_close": round(prev, 4),
                "change_pct": round(chg, 2),
                "inr_trend": trend,
            }
        except Exception as e:
            logger.error(f"Error fetching USD/INR: {e}")
            return None

    # ------------------------------------------------------------------
    # Nifty50 stock movers
    # ------------------------------------------------------------------

    def get_nifty50_movers(self) -> dict:
        """Top 5 gainers and losers from Nifty50."""
        try:
            moves = []
            for symbol in self.nifty50_stocks[:20]:  # Check first 20 for speed
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="5d", interval="1d")
                    if len(hist) < 2:
                        continue

                    curr = float(hist["Close"].iloc[-1])
                    prev = float(hist["Close"].iloc[-2])
                    chg  = ((curr - prev) / prev * 100) if prev else 0

                    moves.append({
                        "symbol": symbol,
                        "price": round(curr, 2),
                        "change_pct": round(chg, 2),
                    })
                except:
                    continue

            moves.sort(key=lambda x: x["change_pct"], reverse=True)
            return {
                "top_gainers": moves[:5],
                "top_losers":  moves[-5:][::-1],
            }
        except Exception as e:
            logger.error(f"Error fetching Nifty50 movers: {e}")
            return {"top_gainers": [], "top_losers": []}

    # ------------------------------------------------------------------
    # Full India snapshot
    # ------------------------------------------------------------------

    def get_full_snapshot(self) -> dict:
        """Fetch all India-specific data in one call."""
        logger.info("Fetching India market snapshot...")
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "indices": self.get_nifty_sensex(),
            "india_vix": self.get_india_vix(),
            "sgx_nifty": self.get_sgx_nifty(),
            "usdinr": self.get_usdinr(),
            "nifty50_movers": self.get_nifty50_movers(),
        }
