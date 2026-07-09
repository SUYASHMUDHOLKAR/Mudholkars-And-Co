"""
analyst.py
----------
Core India market deep analysis engine.
Reads Scout Agent data + India snapshot and produces:
  1. Global event → Indian sector impact analysis
  2. Sentiment score for Indian market (Bullish/Bearish/Neutral)
  3. Sector-wise outlook with specific stocks to watch
  4. Opening gap prediction (using SGX Nifty)
  5. Risk level assessment
  6. Actionable summary for trader
"""

import logging
from datetime import datetime
from typing import Optional

from india_agent.global_impact import (
    GLOBAL_IMPACT_RULES, SECTOR_STOCKS,
    get_sector_stocks
)

logger = logging.getLogger(__name__)

# Sentiment scoring weights
MAGNITUDE_SCORE = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "EXTREME": 5
}


class IndiaAnalyst:
    """
    Deep analysis engine for Indian market impact.
    Takes Scout Agent output + India-specific data and produces
    a comprehensive analysis report.
    """

    def __init__(self):
        self.rules = GLOBAL_IMPACT_RULES

    # ------------------------------------------------------------------
    # Main analysis entry point
    # ------------------------------------------------------------------

    def analyse(self, scout_data: dict, india_snapshot: dict) -> dict:
        """
        Full deep analysis. Call this every time the agent runs.

        scout_data:     output from Scout Agent (price_data + alerts)
        india_snapshot: output from IndiaTracker.get_full_snapshot()
        """
        logger.info("Running India market deep analysis...")

        triggered_rules   = self._match_rules(scout_data)
        sector_outlook    = self._build_sector_outlook(triggered_rules)
        sentiment         = self._compute_sentiment(triggered_rules, india_snapshot)
        opening_signal    = self._predict_opening(india_snapshot, triggered_rules)
        risk_level        = self._assess_risk(sentiment, india_snapshot)
        key_events        = self._extract_key_events(scout_data)
        watchlist         = self._build_watchlist(sector_outlook)
        summary           = self._write_summary(
            sentiment, triggered_rules, sector_outlook,
            opening_signal, risk_level, india_snapshot
        )

        return {
            "timestamp":       datetime.utcnow().isoformat() + "Z",
            "sentiment":       sentiment,
            "risk_level":      risk_level,
            "opening_signal":  opening_signal,
            "triggered_rules": triggered_rules,
            "sector_outlook":  sector_outlook,
            "key_events":      key_events,
            "watchlist":       watchlist,
            "india_snapshot":  india_snapshot,
            "summary":         summary,
        }

    # ------------------------------------------------------------------
    # Rule matching — what global events are happening?
    # ------------------------------------------------------------------

    def _match_rules(self, scout_data: dict) -> list:
        """
        Match Scout Agent data against global impact rules.
        Returns list of triggered rules with actual values attached.
        """
        price_data = scout_data.get("price_data", {})
        alerts     = scout_data.get("alerts", {})
        triggered  = []

        # Flatten all alert types from scout
        all_alert_types = set()
        for sym_alerts in alerts.values():
            for a in sym_alerts:
                all_alert_types.add(a.get("type", ""))

        # Check global selloff
        if "GLOBAL_SELLOFF" in all_alert_types:
            rule = next((r for r in self.rules if r["id"] == "GLOBAL_SELLOFF"), None)
            if rule:
                triggered.append({**rule, "triggered_by": "GLOBAL_SELLOFF"})

        # Check US indices
        sp500  = price_data.get("^GSPC", {})
        nasdaq = price_data.get("^IXIC", {})
        us_pct = min(
            sp500.get("pct_change", 0),
            nasdaq.get("pct_change", 0)
        )
        if us_pct <= -3.0:
            rule = next((r for r in self.rules if r["id"] == "US_MARKET_CRASH"), None)
            if rule:
                triggered.append({**rule, "actual_value": f"S&P {sp500.get('pct_change',0):+.2f}%",
                                   "triggered_by": "^GSPC"})
        elif us_pct >= 3.0:
            rule = next((r for r in self.rules if r["id"] == "US_MARKET_SURGE"), None)
            if rule:
                triggered.append({**rule, "actual_value": f"S&P {sp500.get('pct_change',0):+.2f}%",
                                   "triggered_by": "^GSPC"})

        # Check Crude Oil
        crude = price_data.get("CL=F", {})
        crude_pct = crude.get("pct_change", 0)
        if crude_pct >= 2.0:
            rule = next((r for r in self.rules if r["id"] == "CRUDE_OIL_SPIKE"), None)
            if rule:
                triggered.append({**rule, "actual_value": f"Crude {crude_pct:+.2f}%",
                                   "triggered_by": "CL=F"})
        elif crude_pct <= -2.0:
            rule = next((r for r in self.rules if r["id"] == "CRUDE_OIL_CRASH"), None)
            if rule:
                triggered.append({**rule, "actual_value": f"Crude {crude_pct:+.2f}%",
                                   "triggered_by": "CL=F"})

        # Check USD/INR
        usdinr = price_data.get("USDINR=X", {})
        inr_pct = usdinr.get("pct_change", 0)
        if inr_pct >= 0.5:
            rule = next((r for r in self.rules if r["id"] == "INR_WEAKENS"), None)
            if rule:
                triggered.append({**rule,
                                   "actual_value": f"USD/INR {usdinr.get('current_price', 0):.2f} ({inr_pct:+.2f}%)",
                                   "triggered_by": "USDINR=X"})
        elif inr_pct <= -0.5:
            rule = next((r for r in self.rules if r["id"] == "INR_STRENGTHENS"), None)
            if rule:
                triggered.append({**rule,
                                   "actual_value": f"USD/INR {usdinr.get('current_price', 0):.2f} ({inr_pct:+.2f}%)",
                                   "triggered_by": "USDINR=X"})

        # Check VIX
        vix = price_data.get("^VIX", {})
        vix_price = vix.get("current_price", 0)
        if vix_price >= 40:
            rule = next((r for r in self.rules if r["id"] == "VIX_EXTREME_FEAR"), None)
            if rule:
                triggered.append({**rule, "actual_value": f"VIX={vix_price:.1f}",
                                   "triggered_by": "^VIX"})
        elif vix_price >= 30:
            rule = next((r for r in self.rules if r["id"] == "VIX_HIGH_FEAR"), None)
            if rule:
                triggered.append({**rule, "actual_value": f"VIX={vix_price:.1f}",
                                   "triggered_by": "^VIX"})

        # Check Gold
        gold = price_data.get("GC=F", {})
        gold_pct = gold.get("pct_change", 0)
        if gold_pct >= 1.5:
            rule = next((r for r in self.rules if r["id"] == "GOLD_SURGE"), None)
            if rule:
                triggered.append({**rule, "actual_value": f"Gold {gold_pct:+.2f}%",
                                   "triggered_by": "GC=F"})

        # Check China
        china = price_data.get("000001.SS", {})
        china_pct = china.get("pct_change", 0)
        if china_pct <= -3.0:
            rule = next((r for r in self.rules if r["id"] == "CHINA_CRASH"), None)
            if rule:
                triggered.append({**rule, "actual_value": f"SSE {china_pct:+.2f}%",
                                   "triggered_by": "000001.SS"})

        logger.info(f"Triggered {len(triggered)} impact rules")
        return triggered

    # ------------------------------------------------------------------
    # Sector outlook
    # ------------------------------------------------------------------

    def _build_sector_outlook(self, triggered_rules: list) -> dict:
        """
        Aggregate all triggered rules into a per-sector outlook.
        Returns dict: sector → { direction, score, reasons, stocks_to_watch }
        """
        sector_scores = {}

        for rule in triggered_rules:
            mag_score = MAGNITUDE_SCORE.get(rule.get("magnitude", "LOW"), 1)
            impacted  = rule.get("sectors_impacted", {})

            for direction, sectors in impacted.items():
                for sector in sectors:
                    if sector not in sector_scores:
                        sector_scores[sector] = {"score": 0, "reasons": []}

                    if direction == "POSITIVE":
                        sector_scores[sector]["score"] += mag_score
                    elif direction == "NEGATIVE":
                        sector_scores[sector]["score"] -= mag_score

                    sector_scores[sector]["reasons"].append(
                        f"{direction}: {rule['description']}"
                    )

        # Build final outlook per sector
        outlook = {}
        for sector, data in sector_scores.items():
            score = data["score"]
            if score >= 3:
                direction = "STRONG_BUY"
            elif score >= 1:
                direction = "BUY"
            elif score == 0:
                direction = "NEUTRAL"
            elif score >= -2:
                direction = "CAUTION"
            else:
                direction = "AVOID"

            stocks = get_sector_stocks(sector)
            outlook[sector] = {
                "direction":       direction,
                "score":           score,
                "reasons":         data["reasons"],
                "stocks_to_watch": stocks[:5],  # top 5 stocks in sector
            }

        return dict(sorted(outlook.items(),
                           key=lambda x: x[1]["score"], reverse=True))

    # ------------------------------------------------------------------
    # Sentiment score
    # ------------------------------------------------------------------

    def _compute_sentiment(self, triggered_rules: list,
                           india_snapshot: dict) -> dict:
        """
        Compute overall Indian market sentiment score.
        Range: -10 (extreme bearish) to +10 (extreme bullish)
        """
        score = 0.0
        factors = []

        # Score from triggered rules
        for rule in triggered_rules:
            mag   = MAGNITUDE_SCORE.get(rule.get("magnitude", "LOW"), 1)
            dirn  = rule.get("direction", "NEUTRAL")
            if dirn == "POSITIVE":
                score += mag
                factors.append(f"+{mag}: {rule['description']}")
            elif dirn == "NEGATIVE":
                score -= mag
                factors.append(f"-{mag}: {rule['description']}")

        # India VIX adjustment
        vix_data = india_snapshot.get("india_vix")
        if vix_data:
            vix_val = vix_data.get("current", 0)
            if vix_val >= 25:
                score -= 2
                factors.append(f"-2: India VIX elevated at {vix_val}")
            elif vix_val <= 12:
                score += 1
                factors.append(f"+1: India VIX low at {vix_val} (calm market)")

        # INR adjustment
        inr_data = india_snapshot.get("usdinr")
        if inr_data:
            inr_chg = inr_data.get("change_pct", 0)
            if inr_chg >= 0.5:
                score -= 0.5
                factors.append(f"-0.5: INR weakening ({inr_chg:+.2f}%)")
            elif inr_chg <= -0.5:
                score += 0.5
                factors.append(f"+0.5: INR strengthening ({inr_chg:+.2f}%)")

        # Clamp score to -10 to +10
        score = max(-10, min(10, score))

        if score >= 4:
            label = "STRONGLY_BULLISH"
        elif score >= 1.5:
            label = "BULLISH"
        elif score >= -1.5:
            label = "NEUTRAL"
        elif score >= -4:
            label = "BEARISH"
        else:
            label = "STRONGLY_BEARISH"

        return {
            "score": round(score, 1),
            "label": label,
            "factors": factors,
        }

    # ------------------------------------------------------------------
    # Opening gap prediction
    # ------------------------------------------------------------------

    def _predict_opening(self, india_snapshot: dict,
                         triggered_rules: list) -> dict:
        """
        Predict where Nifty will open next session.
        Uses SGX Nifty as primary signal + global event overlay.
        """
        sgx = india_snapshot.get("sgx_nifty")
        indices = india_snapshot.get("indices", {})
        nifty_close = (indices.get("nifty50") or {}).get("current", 0)

        sgx_signal = "UNKNOWN"
        sgx_premium_pct = 0.0

        if sgx:
            sgx_signal = sgx.get("signal", "FLAT")
            sgx_premium_pct = sgx.get("premium_pct", 0)

        # Adjust based on rule magnitudes
        rule_bias = 0.0
        for rule in triggered_rules:
            mag = MAGNITUDE_SCORE.get(rule.get("magnitude", "LOW"), 1) * 0.2
            if rule.get("direction") == "NEGATIVE":
                rule_bias -= mag
            elif rule.get("direction") == "POSITIVE":
                rule_bias += mag

        total_gap_est = sgx_premium_pct + rule_bias

        if total_gap_est >= 1.0:
            opening = "GAP_UP_STRONG"
        elif total_gap_est >= 0.3:
            opening = "GAP_UP_MILD"
        elif total_gap_est <= -1.0:
            opening = "GAP_DOWN_STRONG"
        elif total_gap_est <= -0.3:
            opening = "GAP_DOWN_MILD"
        else:
            opening = "FLAT_OPEN"

        estimated_open = round(nifty_close * (1 + total_gap_est / 100), 2) if nifty_close else None

        return {
            "sgx_signal":        sgx_signal,
            "sgx_premium_pct":   sgx_premium_pct,
            "rule_bias_pct":     round(rule_bias, 2),
            "estimated_gap_pct": round(total_gap_est, 2),
            "opening_type":      opening,
            "estimated_open":    estimated_open,
        }

    # ------------------------------------------------------------------
    # Risk assessment
    # ------------------------------------------------------------------

    def _assess_risk(self, sentiment: dict, india_snapshot: dict) -> str:
        score = abs(sentiment.get("score", 0))
        vix = (india_snapshot.get("india_vix") or {}).get("current", 0)

        if score >= 6 or vix >= 25:
            return "EXTREME"
        elif score >= 4 or vix >= 18:
            return "HIGH"
        elif score >= 2 or vix >= 14:
            return "MEDIUM"
        else:
            return "LOW"

    # ------------------------------------------------------------------
    # Key events from Scout data
    # ------------------------------------------------------------------

    def _extract_key_events(self, scout_data: dict) -> list:
        """Extract only critical/extreme alerts from Scout as key events."""
        events = []
        for sym, sym_alerts in scout_data.get("alerts", {}).items():
            for a in sym_alerts:
                if a.get("severity") in ("CRITICAL", "EXTREME"):
                    events.append({
                        "symbol":   sym,
                        "event":    a.get("type"),
                        "severity": a.get("severity"),
                        "message":  a.get("message"),
                    })
        return events

    # ------------------------------------------------------------------
    # Watchlist
    # ------------------------------------------------------------------

    def _build_watchlist(self, sector_outlook: dict) -> dict:
        """Build buy/avoid watchlist from sector outlook."""
        buy   = []
        avoid = []
        for sector, data in sector_outlook.items():
            direction = data.get("direction")
            stocks    = data.get("stocks_to_watch", [])[:3]
            if direction in ("STRONG_BUY", "BUY"):
                buy += [{"symbol": s, "sector": sector,
                         "reason": direction} for s in stocks]
            elif direction == "AVOID":
                avoid += [{"symbol": s, "sector": sector,
                           "reason": "AVOID"} for s in stocks]
        return {"buy_watchlist": buy, "avoid_watchlist": avoid}

    # ------------------------------------------------------------------
    # Human-readable summary
    # ------------------------------------------------------------------

    def _write_summary(self, sentiment: dict, triggered_rules: list,
                       sector_outlook: dict, opening_signal: dict,
                       risk_level: str, india_snapshot: dict) -> str:
        lines = []
        lines.append("=" * 65)
        lines.append("  INDIA MARKET DEEP ANALYSIS")
        lines.append(f"  Generated: {datetime.now().strftime('%d %b %Y  %H:%M IST')}")
        lines.append("=" * 65)

        # Sentiment
        score = sentiment.get("score", 0)
        label = sentiment.get("label", "NEUTRAL")
        lines.append(f"\nMARKET SENTIMENT : {label}  (Score: {score:+.1f} / 10)")
        lines.append(f"RISK LEVEL       : {risk_level}")

        # Opening prediction
        op = opening_signal
        lines.append(
            f"NIFTY OPENING    : {op.get('opening_type')}  "
            f"(~{op.get('estimated_gap_pct', 0):+.2f}%)"
        )
        if op.get("estimated_open"):
            lines.append(f"ESTIMATED OPEN   : {op['estimated_open']:.0f}")

        # India VIX
        vix_data = india_snapshot.get("india_vix")
        if vix_data:
            lines.append(
                f"INDIA VIX        : {vix_data.get('current', 0):.1f}  "
                f"[{vix_data.get('fear_level', '')}]"
            )

        # INR
        inr_data = india_snapshot.get("usdinr")
        if inr_data:
            lines.append(
                f"USD/INR          : {inr_data.get('usdinr', 0):.2f}  "
                f"({inr_data.get('change_pct', 0):+.2f}%)  "
                f"→ INR {inr_data.get('inr_trend', '')}"
            )

        # Global events
        if triggered_rules:
            lines.append(f"\nGLOBAL EVENTS IMPACTING INDIA ({len(triggered_rules)})")
            lines.append("-" * 40)
            for rule in triggered_rules:
                lines.append(
                    f"  [{rule['magnitude']:6s}] {rule['description']}"
                )
                lines.append(f"           → {rule['india_reason'][:90]}")
                lines.append(f"           → Expected Nifty: {rule.get('expected_nifty_move', 'N/A')}")

        # Sector outlook
        lines.append(f"\nSECTOR OUTLOOK")
        lines.append("-" * 40)
        for sector, data in sector_outlook.items():
            direction = data.get("direction")
            score_s   = data.get("score", 0)
            stocks    = ", ".join(s.replace(".NS", "") for s in data.get("stocks_to_watch", [])[:3])
            lines.append(f"  {sector:18s} : {direction:15s} (score {score_s:+d})  |  {stocks}")

        # Sentiment factors
        lines.append(f"\nSENTIMENT FACTORS")
        lines.append("-" * 40)
        for f in sentiment.get("factors", []):
            lines.append(f"  {f}")

        lines.append("\n" + "=" * 65)
        return "\n".join(lines)
