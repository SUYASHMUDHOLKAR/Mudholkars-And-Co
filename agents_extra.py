"""
agents_extra.py - Additional analysis agents for Indian stock market intelligence.

Contains 5 standalone agent classes:
- DeliveryVolumeAgent
- MutualFundAgent
- InsiderTradingAgent
- GlobalCorrelationAgent
- VolatilityAgent

Each agent returns a dict with: direction, score, signal, weight
"""

import logging
from typing import Dict, List, Optional

import yfinance as yf
import requests
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Standard headers for NSE API calls
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json,text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.nseindia.com/",
    "Connection": "keep-alive",
}

NSE_BASE_URL = "https://www.nseindia.com"


def _get_nse_session() -> requests.Session:
    """Create a session with NSE cookies pre-loaded."""
    session = requests.Session()
    session.headers.update(NSE_HEADERS)
    try:
        session.get(NSE_BASE_URL, timeout=10)
    except Exception as e:
        logger.warning(f"Failed to initialize NSE session: {e}")
    return session


class DeliveryVolumeAgent:
    """
    Checks delivery percentage from NSE bhavcopy data.

    Logic:
    - Stocks with >50% delivery = strong hands buying = BULLISH
    - Stocks with <30% delivery = speculative trading = BEARISH
    - Between 30-50% = NEUTRAL

    Weight: 1.3
    """

    WEIGHT = 1.3

    def __init__(self):
        self.session = _get_nse_session()

    def analyze(self, symbol: str) -> Dict:
        """
        Analyze delivery volume for a given stock symbol.

        Args:
            symbol: NSE stock symbol (e.g., 'RELIANCE')

        Returns:
            dict with keys: direction, score, signal, weight
        """
        try:
            url = f"{NSE_BASE_URL}/api/quote-equity?symbol={symbol}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Extract delivery data from security-wise delivery position
            trade_info = data.get("securityWiseDP", {})
            delivery_pct = float(trade_info.get("delToTradQty", 0))

            if delivery_pct > 50:
                direction = "BULLISH"
                score = min(50 + (delivery_pct - 50) * 1.5, 85)
                signal = (
                    f"Strong hands buying: {delivery_pct:.1f}% delivery volume "
                    f"(above 50% threshold)"
                )
            elif delivery_pct < 30:
                direction = "BEARISH"
                score = max(20, 50 - (30 - delivery_pct) * 1.5)
                signal = (
                    f"Speculative trading: only {delivery_pct:.1f}% delivery volume "
                    f"(below 30% threshold)"
                )
            else:
                direction = "NEUTRAL"
                score = 50
                signal = (
                    f"Moderate delivery volume: {delivery_pct:.1f}% "
                    f"(between 30-50% range)"
                )

            return {
                "direction": direction,
                "score": round(score, 1),
                "signal": signal,
                "weight": self.WEIGHT,
            }

        except Exception as e:
            logger.error(f"DeliveryVolumeAgent error for {symbol}: {e}")
            return {
                "direction": "NEUTRAL",
                "score": 50,
                "signal": f"Unable to fetch delivery data for {symbol}: {str(e)}",
                "weight": self.WEIGHT,
            }

    def analyze_batch(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Analyze delivery volume for multiple symbols.

        Args:
            symbols: List of NSE stock symbols

        Returns:
            dict mapping symbol -> analysis result
        """
        results = {}
        for symbol in symbols:
            results[symbol] = self.analyze(symbol)
        return results


class MutualFundAgent:
    """
    Tracks mutual fund holdings changes via yfinance institutional data.

    Logic:
    - If MFs/institutions increasing stake = BULLISH
    - If MFs/institutions decreasing stake = BEARISH
    - Uses major_holders and institutional_holders from yfinance

    Weight: 1.2
    """

    WEIGHT = 1.2

    def analyze(self, symbol: str) -> Dict:
        """
        Analyze mutual fund / institutional holdings for a stock.

        Args:
            symbol: Stock symbol (e.g., 'RELIANCE.NS' for NSE stocks)

        Returns:
            dict with keys: direction, score, signal, weight
        """
        try:
            # Append .NS if not already present for Indian stocks
            yf_symbol = symbol if "." in symbol else f"{symbol}.NS"
            ticker = yf.Ticker(yf_symbol)

            # Get major holders data
            major_holders = ticker.major_holders
            institutional_holders = ticker.institutional_holders

            # Extract institutional holding percentage
            inst_pct = 0.0
            if major_holders is not None and not major_holders.empty:
                for idx, row in major_holders.iterrows():
                    value_str = str(row.iloc[0]).replace("%", "").strip()
                    label = str(row.iloc[1]).lower() if len(row) > 1 else ""
                    if "institution" in label and "hold" in label:
                        try:
                            inst_pct = float(value_str)
                        except ValueError:
                            pass

            # Check recent institutional holder changes
            holder_count = 0
            if institutional_holders is not None and not institutional_holders.empty:
                holder_count = len(institutional_holders)

            # Determine direction based on institutional presence
            if inst_pct > 40:
                direction = "BULLISH"
                score = min(60 + (inst_pct - 40) * 0.5, 80)
                signal = (
                    f"Strong institutional backing: {inst_pct:.1f}% held by institutions. "
                    f"{holder_count} major institutional holders identified."
                )
            elif inst_pct > 20:
                direction = "NEUTRAL"
                score = 50 + (inst_pct - 20) * 0.25
                signal = (
                    f"Moderate institutional holding: {inst_pct:.1f}%. "
                    f"{holder_count} institutional holders."
                )
            elif inst_pct > 0:
                direction = "BEARISH"
                score = max(30, 50 - (20 - inst_pct))
                signal = (
                    f"Low institutional interest: only {inst_pct:.1f}% held by institutions."
                )
            else:
                direction = "NEUTRAL"
                score = 50
                signal = (
                    f"Institutional holding data unavailable for {symbol}. "
                    f"Found {holder_count} institutional holders in records."
                )

            return {
                "direction": direction,
                "score": round(score, 1),
                "signal": signal,
                "weight": self.WEIGHT,
            }

        except Exception as e:
            logger.error(f"MutualFundAgent error for {symbol}: {e}")
            return {
                "direction": "NEUTRAL",
                "score": 50,
                "signal": f"Unable to fetch MF/institutional data for {symbol}: {str(e)}",
                "weight": self.WEIGHT,
            }

    def analyze_batch(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Analyze mutual fund holdings for multiple symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            dict mapping symbol -> analysis result
        """
        results = {}
        for symbol in symbols:
            results[symbol] = self.analyze(symbol)
        return results


class InsiderTradingAgent:
    """
    Checks SEBI SAST/PIT (Prohibition of Insider Trading) data from NSE API.

    Logic:
    - Promoter buying = STRONG BULLISH (score 80+)
    - Promoter selling = BEARISH
    - Uses NSE corporates-pit endpoint

    Weight: 1.5
    """

    WEIGHT = 1.5

    def __init__(self):
        self.session = _get_nse_session()

    def analyze(self, symbol: str) -> Dict:
        """
        Analyze insider/promoter trading activity for a stock.

        Args:
            symbol: NSE stock symbol (e.g., 'RELIANCE')

        Returns:
            dict with keys: direction, score, signal, weight
        """
        try:
            url = (
                f"{NSE_BASE_URL}/api/corporates-pit?"
                f"index=equities&symbol={symbol}"
            )
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            transactions = data.get("data", [])

            if not transactions:
                return {
                    "direction": "NEUTRAL",
                    "score": 50,
                    "signal": f"No recent insider trading data found for {symbol}.",
                    "weight": self.WEIGHT,
                }

            # Analyze recent transactions
            promoter_buys = 0
            promoter_sells = 0
            total_buy_value = 0.0
            total_sell_value = 0.0

            for txn in transactions[:20]:  # Check last 20 transactions
                category = str(txn.get("personCategory", "")).lower()
                acq_mode = str(txn.get("acquistionMode", "")).lower()
                txn_type = str(txn.get("typeOfTransaction", "")).lower()

                is_promoter = "promoter" in category or "director" in category

                try:
                    shares = float(txn.get("noOfShareAcq", 0) or 0)
                except (ValueError, TypeError):
                    shares = 0

                if is_promoter:
                    if "buy" in txn_type or "acquisition" in txn_type:
                        promoter_buys += 1
                        total_buy_value += shares
                    elif "sell" in txn_type or "disposal" in txn_type:
                        promoter_sells += 1
                        total_sell_value += shares

            # Determine signal
            if promoter_buys > promoter_sells and promoter_buys > 0:
                direction = "BULLISH"
                # Strong bullish for promoter buying
                score = min(80 + (promoter_buys * 3), 95)
                signal = (
                    f"STRONG: Promoter/insider BUYING detected. "
                    f"{promoter_buys} buy transactions vs {promoter_sells} sells. "
                    f"Net buying of {total_buy_value - total_sell_value:.0f} shares."
                )
            elif promoter_sells > promoter_buys and promoter_sells > 0:
                direction = "BEARISH"
                score = max(20, 50 - (promoter_sells * 5))
                signal = (
                    f"Promoter/insider SELLING detected. "
                    f"{promoter_sells} sell transactions vs {promoter_buys} buys. "
                    f"Net selling of {total_sell_value - total_buy_value:.0f} shares."
                )
            else:
                direction = "NEUTRAL"
                score = 50
                signal = (
                    f"Mixed insider activity: {promoter_buys} buys, "
                    f"{promoter_sells} sells. No clear directional bias."
                )

            return {
                "direction": direction,
                "score": round(score, 1),
                "signal": signal,
                "weight": self.WEIGHT,
            }

        except Exception as e:
            logger.error(f"InsiderTradingAgent error for {symbol}: {e}")
            return {
                "direction": "NEUTRAL",
                "score": 50,
                "signal": f"Unable to fetch insider trading data for {symbol}: {str(e)}",
                "weight": self.WEIGHT,
            }

    def analyze_batch(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Analyze insider trading for multiple symbols.

        Args:
            symbols: List of NSE stock symbols

        Returns:
            dict mapping symbol -> analysis result
        """
        results = {}
        for symbol in symbols:
            results[symbol] = self.analyze(symbol)
        return results


class GlobalCorrelationAgent:
    """
    Checks global market indices for correlation impact on Indian markets.

    Monitors: S&P500 (^GSPC), Dow (^DJI), Nasdaq (^IXIC),
              China (000001.SS), Crude Oil (CL=F), Gold (GC=F)

    Logic:
    - If US/China crashed >1.5% yesterday = BEARISH for India
    - If US/China rallied >1% yesterday = BULLISH for India
    - Commodity moves also factored in

    Weight: 1.4
    """

    WEIGHT = 1.4

    GLOBAL_INDICES = {
        "^GSPC": "S&P 500",
        "^DJI": "Dow Jones",
        "^IXIC": "Nasdaq",
        "000001.SS": "Shanghai Composite",
        "CL=F": "Crude Oil",
        "GC=F": "Gold",
    }

    def analyze(self) -> Dict:
        """
        Analyze global market conditions for India correlation.

        This is a market-wide signal, not per-stock.

        Returns:
            dict with keys: direction, score, signal, weight
        """
        try:
            changes = {}
            signals_list = []

            for ticker_symbol, name in self.GLOBAL_INDICES.items():
                try:
                    ticker = yf.Ticker(ticker_symbol)
                    hist = ticker.history(period="5d")

                    if hist is not None and len(hist) >= 2:
                        prev_close = hist["Close"].iloc[-2]
                        last_close = hist["Close"].iloc[-1]
                        pct_change = ((last_close - prev_close) / prev_close) * 100
                        changes[ticker_symbol] = pct_change
                        signals_list.append(f"{name}: {pct_change:+.2f}%")
                except Exception as e:
                    logger.warning(f"Failed to fetch {name} ({ticker_symbol}): {e}")

            if not changes:
                return {
                    "direction": "NEUTRAL",
                    "score": 50,
                    "signal": "Unable to fetch any global market data.",
                    "weight": self.WEIGHT,
                }

            # Calculate weighted impact
            # US indices have higher weight for India correlation
            us_indices = ["^GSPC", "^DJI", "^IXIC"]
            us_changes = [changes[k] for k in us_indices if k in changes]
            avg_us_change = np.mean(us_changes) if us_changes else 0

            china_change = changes.get("000001.SS", 0)
            crude_change = changes.get("CL=F", 0)
            gold_change = changes.get("GC=F", 0)

            # Weighted composite score
            composite = (
                avg_us_change * 0.4
                + china_change * 0.2
                + crude_change * 0.2
                + gold_change * 0.2
            )

            # Determine direction
            if avg_us_change < -1.5 or china_change < -1.5:
                direction = "BEARISH"
                score = max(15, 50 + composite * 10)
                signal_prefix = "GLOBAL RISK-OFF: "
            elif avg_us_change > 1.0 or china_change > 1.0:
                direction = "BULLISH"
                score = min(85, 50 + composite * 10)
                signal_prefix = "GLOBAL RISK-ON: "
            elif composite < -0.5:
                direction = "BEARISH"
                score = max(30, 50 + composite * 8)
                signal_prefix = "Mild global weakness: "
            elif composite > 0.5:
                direction = "BULLISH"
                score = min(70, 50 + composite * 8)
                signal_prefix = "Mild global strength: "
            else:
                direction = "NEUTRAL"
                score = 50
                signal_prefix = "Global markets stable: "

            signal = signal_prefix + " | ".join(signals_list)

            return {
                "direction": direction,
                "score": round(score, 1),
                "signal": signal,
                "weight": self.WEIGHT,
            }

        except Exception as e:
            logger.error(f"GlobalCorrelationAgent error: {e}")
            return {
                "direction": "NEUTRAL",
                "score": 50,
                "signal": f"Unable to analyze global markets: {str(e)}",
                "weight": self.WEIGHT,
            }

    def analyze_batch(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        For GlobalCorrelationAgent, the analysis is market-wide.
        Returns the same global result mapped to each symbol.

        Args:
            symbols: List of symbols (result is same for all)

        Returns:
            dict mapping symbol -> global analysis result
        """
        global_result = self.analyze()
        return {symbol: global_result for symbol in symbols}


class VolatilityAgent:
    """
    Calculates Average True Range (ATR) for volatility assessment.

    Logic:
    - ATR% > 4% of price = HIGH volatility = AVOID/BEARISH (risky)
    - ATR% between 2-4% = MODERATE volatility = NEUTRAL
    - ATR% < 2% = LOW volatility = safer for swing trades = slight BULLISH
    - Also checks India VIX (^INDIAVIX) for market-wide fear gauge

    Weight: 1.1
    """

    WEIGHT = 1.1
    ATR_PERIOD = 14

    def _calculate_atr(self, hist: pd.DataFrame, period: int = 14) -> Optional[float]:
        """
        Calculate Average True Range over specified period.

        Args:
            hist: DataFrame with High, Low, Close columns
            period: ATR lookback period (default 14)

        Returns:
            ATR value or None if insufficient data
        """
        if hist is None or len(hist) < period + 1:
            return None

        high = hist["High"]
        low = hist["Low"]
        close = hist["Close"]

        # True Range = max(H-L, abs(H-prevC), abs(L-prevC))
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # ATR is the rolling mean of True Range
        atr = true_range.rolling(window=period).mean().iloc[-1]
        return atr

    def _get_india_vix(self) -> Optional[float]:
        """Fetch India VIX value."""
        try:
            vix_ticker = yf.Ticker("^INDIAVIX")
            vix_hist = vix_ticker.history(period="5d")
            if vix_hist is not None and not vix_hist.empty:
                return vix_hist["Close"].iloc[-1]
        except Exception as e:
            logger.warning(f"Failed to fetch India VIX: {e}")
        return None

    def analyze(self, symbol: str) -> Dict:
        """
        Analyze volatility for a given stock using ATR and India VIX.

        Args:
            symbol: Stock symbol (e.g., 'RELIANCE' or 'RELIANCE.NS')

        Returns:
            dict with keys: direction, score, signal, weight
        """
        try:
            # Append .NS if not already present for Indian stocks
            yf_symbol = symbol if "." in symbol else f"{symbol}.NS"
            ticker = yf.Ticker(yf_symbol)
            hist = ticker.history(period="1mo")

            if hist is None or hist.empty:
                return {
                    "direction": "NEUTRAL",
                    "score": 50,
                    "signal": f"No price data available for {symbol}.",
                    "weight": self.WEIGHT,
                }

            # Calculate ATR
            atr = self._calculate_atr(hist, self.ATR_PERIOD)
            current_price = hist["Close"].iloc[-1]

            if atr is None or current_price == 0:
                return {
                    "direction": "NEUTRAL",
                    "score": 50,
                    "signal": f"Insufficient data to calculate ATR for {symbol}.",
                    "weight": self.WEIGHT,
                }

            atr_pct = (atr / current_price) * 100

            # Get India VIX for additional context
            india_vix = self._get_india_vix()
            vix_signal = ""
            vix_adjustment = 0

            if india_vix is not None:
                if india_vix > 20:
                    vix_signal = f" India VIX at {india_vix:.1f} (HIGH fear)."
                    vix_adjustment = -5
                elif india_vix < 13:
                    vix_signal = f" India VIX at {india_vix:.1f} (LOW/complacent)."
                    vix_adjustment = 3
                else:
                    vix_signal = f" India VIX at {india_vix:.1f} (normal range)."

            # Determine direction based on ATR%
            if atr_pct > 4.0:
                direction = "BEARISH"
                score = max(20, 40 - (atr_pct - 4) * 5) + vix_adjustment
                signal = (
                    f"HIGH volatility: ATR% = {atr_pct:.2f}% (>{4}% threshold). "
                    f"ATR = ₹{atr:.2f}, Price = ₹{current_price:.2f}. "
                    f"RISKY for swing trades - avoid or reduce position size.{vix_signal}"
                )
            elif atr_pct < 2.0:
                direction = "BULLISH"
                score = min(70, 60 + (2 - atr_pct) * 10) + vix_adjustment
                signal = (
                    f"LOW volatility: ATR% = {atr_pct:.2f}% (<2% threshold). "
                    f"ATR = ₹{atr:.2f}, Price = ₹{current_price:.2f}. "
                    f"Safer for swing trades - controlled risk.{vix_signal}"
                )
            else:
                direction = "NEUTRAL"
                score = 50 + vix_adjustment
                signal = (
                    f"MODERATE volatility: ATR% = {atr_pct:.2f}% (2-4% range). "
                    f"ATR = ₹{atr:.2f}, Price = ₹{current_price:.2f}. "
                    f"Normal trading conditions.{vix_signal}"
                )

            # Clamp score to valid range
            score = max(10, min(90, score))

            return {
                "direction": direction,
                "score": round(score, 1),
                "signal": signal,
                "weight": self.WEIGHT,
            }

        except Exception as e:
            logger.error(f"VolatilityAgent error for {symbol}: {e}")
            return {
                "direction": "NEUTRAL",
                "score": 50,
                "signal": f"Unable to analyze volatility for {symbol}: {str(e)}",
                "weight": self.WEIGHT,
            }

    def analyze_batch(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Analyze volatility for multiple symbols.

        Args:
            symbols: List of stock symbols

        Returns:
            dict mapping symbol -> analysis result
        """
        results = {}
        for symbol in symbols:
            results[symbol] = self.analyze(symbol)
        return results


# Module-level convenience for quick access
__all__ = [
    "DeliveryVolumeAgent",
    "MutualFundAgent",
    "InsiderTradingAgent",
    "GlobalCorrelationAgent",
    "VolatilityAgent",
]
