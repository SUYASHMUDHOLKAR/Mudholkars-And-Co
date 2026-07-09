"""
alert_engine.py
---------------
Analyses price + indicator data and fires alerts for unusual events.
Alert types: price crash/surge, volume spike, RSI extremes, MACD crossover,
             VIX fear levels, gap up/down, 52-week breaches, golden/death cross.
"""

import json
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# Alert severity levels
SEVERITY_INFO     = "INFO"
SEVERITY_WARNING  = "WARNING"
SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_EXTREME  = "EXTREME"


class Alert:
    """Represents a single alert event."""

    def __init__(self, symbol: str, alert_type: str, severity: str,
                 message: str, data: Optional[dict] = None):
        self.symbol     = symbol
        self.alert_type = alert_type
        self.severity   = severity
        self.message    = message
        self.data       = data or {}
        self.timestamp  = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> dict:
        return {
            "timestamp":  self.timestamp,
            "symbol":     self.symbol,
            "type":       self.alert_type,
            "severity":   self.severity,
            "message":    self.message,
            "data":       self.data,
        }

    def __str__(self) -> str:
        return f"[{self.severity}] {self.symbol} | {self.alert_type} | {self.message}"


class AlertEngine:
    """
    Evaluates price and indicator snapshots against configured thresholds.
    Returns a list of Alert objects for any anomalies detected.
    """

    def __init__(self, config: dict):
        self.config    = config
        self.thresh    = config.get("alert_thresholds", {})
        self.price_t   = self.thresh.get("price_change", {})
        self.volume_t  = self.thresh.get("volume", {})
        self.vix_t     = self.thresh.get("vix", {})
        self.rsi_t     = self.thresh.get("rsi", {})
        self.gap_t     = self.thresh.get("gap", {})
        self.week52_t  = self.thresh.get("week_52", {})

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def evaluate(self, price_data: dict, indicator_data: Optional[dict] = None,
                 ma_data: Optional[dict] = None) -> list:
        """
        Run all checks on a symbol's data. Returns list of Alert objects.
        price_data:     output of PriceTracker.fetch_current()
        indicator_data: output of IndicatorTracker.get_full_snapshot()
        ma_data:        output of PriceTracker.compute_moving_averages()
        """
        alerts = []
        symbol = price_data.get("symbol", "UNKNOWN")

        alerts += self._check_price_move(symbol, price_data)
        alerts += self._check_volume(symbol, price_data)
        alerts += self._check_gap(symbol, price_data)
        alerts += self._check_52week(symbol, price_data)
        alerts += self._check_vix(symbol, price_data)

        if indicator_data:
            alerts += self._check_rsi(symbol, indicator_data.get("rsi"))
            alerts += self._check_macd(symbol, indicator_data.get("macd"))
            alerts += self._check_bollinger(symbol, price_data, indicator_data.get("bollinger"))

        if ma_data:
            alerts += self._check_moving_averages(symbol, ma_data)

        for alert in alerts:
            logger.warning(str(alert)) if alert.severity in (SEVERITY_CRITICAL, SEVERITY_EXTREME) \
                else logger.info(str(alert))

        return alerts

    def evaluate_batch(self, all_price_data: dict,
                       all_indicator_data: Optional[dict] = None,
                       all_ma_data: Optional[dict] = None) -> dict:
        """
        Evaluate alerts for multiple symbols at once.
        Returns dict keyed by symbol -> list of Alert dicts.
        """
        results = {}
        for symbol, price_data in all_price_data.items():
            if price_data.get("error"):
                continue
            indicators = (all_indicator_data or {}).get(symbol)
            ma         = (all_ma_data or {}).get(symbol)
            raw_alerts = self.evaluate(price_data, indicators, ma)
            results[symbol] = [a.to_dict() for a in raw_alerts]
        return results

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_price_move(self, symbol: str, data: dict) -> list:
        alerts = []
        pct = data.get("pct_change", 0)
        ext = self.price_t.get("extreme_pct", 5.0)
        crit = self.price_t.get("critical_pct", 3.0)
        warn = self.price_t.get("warning_pct", 1.5)
        abs_pct = abs(pct)
        direction = "UP" if pct > 0 else "DOWN"

        if abs_pct >= ext:
            alerts.append(Alert(
                symbol, "EXTREME_PRICE_MOVE", SEVERITY_EXTREME,
                f"Extreme move {pct:+.2f}% ({direction})",
                {"pct_change": pct}
            ))
        elif abs_pct >= crit:
            alerts.append(Alert(
                symbol, "CRITICAL_PRICE_MOVE", SEVERITY_CRITICAL,
                f"Critical move {pct:+.2f}% ({direction})",
                {"pct_change": pct}
            ))
        elif abs_pct >= warn:
            alerts.append(Alert(
                symbol, "PRICE_WARNING", SEVERITY_WARNING,
                f"Notable move {pct:+.2f}% ({direction})",
                {"pct_change": pct}
            ))
        return alerts

    def _check_volume(self, symbol: str, data: dict) -> list:
        alerts = []
        ratio = data.get("volume_ratio", 1.0)
        spike = self.volume_t.get("spike_multiplier", 2.0)
        ext   = self.volume_t.get("extreme_spike_multiplier", 3.5)

        if ratio >= ext:
            alerts.append(Alert(
                symbol, "EXTREME_VOLUME_SPIKE", SEVERITY_CRITICAL,
                f"Extreme volume spike: {ratio:.1f}x average",
                {"volume_ratio": ratio, "volume": data.get("volume"),
                 "avg_volume_30d": data.get("avg_volume_30d")}
            ))
        elif ratio >= spike:
            alerts.append(Alert(
                symbol, "VOLUME_SPIKE", SEVERITY_WARNING,
                f"Volume spike: {ratio:.1f}x average",
                {"volume_ratio": ratio}
            ))
        return alerts

    def _check_gap(self, symbol: str, data: dict) -> list:
        alerts = []
        gap = data.get("gap_pct", 0)
        gap_up  = self.gap_t.get("gap_up_pct", 1.5)
        gap_dn  = self.gap_t.get("gap_down_pct", -1.5)

        if gap >= gap_up:
            alerts.append(Alert(
                symbol, "GAP_UP", SEVERITY_WARNING,
                f"Gap UP open: {gap:+.2f}% above previous close",
                {"gap_pct": gap, "open": data.get("open"), "prev_close": data.get("prev_close")}
            ))
        elif gap <= gap_dn:
            alerts.append(Alert(
                symbol, "GAP_DOWN", SEVERITY_WARNING,
                f"Gap DOWN open: {gap:+.2f}% below previous close",
                {"gap_pct": gap, "open": data.get("open"), "prev_close": data.get("prev_close")}
            ))
        return alerts

    def _check_52week(self, symbol: str, data: dict) -> list:
        alerts = []
        price = data.get("current_price", 0)
        high  = data.get("week_52_high")
        low   = data.get("week_52_low")
        near_pct = self.week52_t.get("near_high_pct", 2.0)

        if high and price >= high * (1 - near_pct / 100):
            alerts.append(Alert(
                symbol, "NEAR_52W_HIGH", SEVERITY_INFO,
                f"Price {price:.4f} near 52-week high of {high:.4f}",
                {"current": price, "week_52_high": high}
            ))
        if low and price <= low * (1 + near_pct / 100):
            alerts.append(Alert(
                symbol, "NEAR_52W_LOW", SEVERITY_WARNING,
                f"Price {price:.4f} near 52-week low of {low:.4f}",
                {"current": price, "week_52_low": low}
            ))
        return alerts

    def _check_vix(self, symbol: str, data: dict) -> list:
        """Check VIX (Fear Index) levels — only fires for ^VIX symbol."""
        if symbol != "^VIX":
            return []
        alerts = []
        price = data.get("current_price", 0)
        ext_fear = self.vix_t.get("extreme_fear", 40)
        hi_fear  = self.vix_t.get("high_fear", 30)
        elevated = self.vix_t.get("elevated", 20)

        if price >= ext_fear:
            alerts.append(Alert(
                symbol, "VIX_EXTREME_FEAR", SEVERITY_EXTREME,
                f"VIX at {price:.2f} — EXTREME FEAR (market panic likely)",
                {"vix": price}
            ))
        elif price >= hi_fear:
            alerts.append(Alert(
                symbol, "VIX_HIGH_FEAR", SEVERITY_CRITICAL,
                f"VIX at {price:.2f} — HIGH FEAR (increased volatility)",
                {"vix": price}
            ))
        elif price >= elevated:
            alerts.append(Alert(
                symbol, "VIX_ELEVATED", SEVERITY_WARNING,
                f"VIX at {price:.2f} — Elevated volatility",
                {"vix": price}
            ))
        return alerts

    def _check_rsi(self, symbol: str, rsi_data: Optional[dict]) -> list:
        if not rsi_data:
            return []
        alerts = []
        rsi    = rsi_data.get("rsi", 50)
        signal = rsi_data.get("signal", "NEUTRAL")

        if signal == "EXTREME_OVERBOUGHT":
            alerts.append(Alert(
                symbol, "RSI_EXTREME_OVERBOUGHT", SEVERITY_CRITICAL,
                f"RSI={rsi:.1f} — Extremely overbought, reversal risk high",
                {"rsi": rsi}
            ))
        elif signal == "OVERBOUGHT":
            alerts.append(Alert(
                symbol, "RSI_OVERBOUGHT", SEVERITY_WARNING,
                f"RSI={rsi:.1f} — Overbought territory",
                {"rsi": rsi}
            ))
        elif signal == "EXTREME_OVERSOLD":
            alerts.append(Alert(
                symbol, "RSI_EXTREME_OVERSOLD", SEVERITY_CRITICAL,
                f"RSI={rsi:.1f} — Extremely oversold, bounce possible",
                {"rsi": rsi}
            ))
        elif signal == "OVERSOLD":
            alerts.append(Alert(
                symbol, "RSI_OVERSOLD", SEVERITY_WARNING,
                f"RSI={rsi:.1f} — Oversold territory",
                {"rsi": rsi}
            ))
        return alerts

    def _check_macd(self, symbol: str, macd_data: Optional[dict]) -> list:
        if not macd_data:
            return []
        alerts = []
        crossover = macd_data.get("crossover", "NONE")

        if crossover == "BULLISH_CROSSOVER":
            alerts.append(Alert(
                symbol, "MACD_BULLISH_CROSSOVER", SEVERITY_INFO,
                f"MACD bullish crossover — potential uptrend starting",
                {"macd": macd_data.get("macd"), "signal": macd_data.get("signal")}
            ))
        elif crossover == "BEARISH_CROSSOVER":
            alerts.append(Alert(
                symbol, "MACD_BEARISH_CROSSOVER", SEVERITY_WARNING,
                f"MACD bearish crossover — potential downtrend starting",
                {"macd": macd_data.get("macd"), "signal": macd_data.get("signal")}
            ))
        return alerts

    def _check_bollinger(self, symbol: str, price_data: dict,
                         bb_data: Optional[dict]) -> list:
        if not bb_data:
            return []
        alerts = []
        price = price_data.get("current_price", 0)
        upper = bb_data.get("upper_band", 0)
        lower = bb_data.get("lower_band", 0)

        if upper and price >= upper:
            alerts.append(Alert(
                symbol, "BOLLINGER_UPPER_BREACH", SEVERITY_WARNING,
                f"Price {price:.4f} breached upper Bollinger Band {upper:.4f}",
                {"price": price, "upper_band": upper}
            ))
        elif lower and price <= lower:
            alerts.append(Alert(
                symbol, "BOLLINGER_LOWER_BREACH", SEVERITY_WARNING,
                f"Price {price:.4f} breached lower Bollinger Band {lower:.4f}",
                {"price": price, "lower_band": lower}
            ))
        return alerts

    def _check_moving_averages(self, symbol: str, ma_data: dict) -> list:
        alerts = []

        if ma_data.get("golden_cross"):
            alerts.append(Alert(
                symbol, "GOLDEN_CROSS", SEVERITY_INFO,
                "Golden Cross: 50MA crossed above 200MA — long-term bullish signal",
                {"ma_50": ma_data.get("ma_50"), "ma_200": ma_data.get("ma_200")}
            ))
        if ma_data.get("death_cross"):
            alerts.append(Alert(
                symbol, "DEATH_CROSS", SEVERITY_CRITICAL,
                "Death Cross: 50MA crossed below 200MA — long-term bearish signal",
                {"ma_50": ma_data.get("ma_50"), "ma_200": ma_data.get("ma_200")}
            ))
        return alerts

    # ------------------------------------------------------------------
    # Global market check — look for multi-exchange selloff
    # ------------------------------------------------------------------

    def check_global_selloff(self, all_price_data: dict) -> Optional[Alert]:
        """
        If 5+ major indices are all down more than warning threshold simultaneously,
        fire a global market selloff alert.
        """
        warn = self.price_t.get("warning_pct", 1.5)
        down_symbols = [
            sym for sym, d in all_price_data.items()
            if isinstance(d, dict) and d.get("pct_change", 0) <= -warn
        ]
        if len(down_symbols) >= 5:
            return Alert(
                "GLOBAL", "GLOBAL_SELLOFF", SEVERITY_EXTREME,
                f"{len(down_symbols)} indices/assets down simultaneously — possible global selloff",
                {"affected_symbols": down_symbols}
            )
        return None
