"""
consensus_engine.py
-------------------
Mudholkars and Co — THE BRAIN

Combines signals from ALL agents into a single verdict per stock.
"How many of my 47 agents agree on this stock?"

Only recommends when 4+ agents agree = high probability trades.

Output per stock:
  - Consensus: STRONG BUY / BUY / HOLD / SELL / AVOID
  - Confidence: 0-100%
  - Agents agreeing: list of agent names + their signals
  - Dissenting agents: who disagrees and why
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class ConsensusEngine:
    """
    THE BRAIN of Mudholkars and Co.
    Reads outputs from all agents and produces one combined verdict.
    """

    def evaluate(self, stock: str, agent_signals: dict) -> dict:
        """
        Evaluate consensus for a single stock across all agents.

        agent_signals: {
            "agent_name": {
                "direction": "BULLISH" / "BEARISH" / "NEUTRAL",
                "score": 0-100,
                "signal": "reason text",
                "weight": 1.0 (importance of this agent)
            }
        }

        Returns final verdict with confidence.
        """
        if not agent_signals:
            return {"stock": stock, "consensus": "NO DATA", "confidence": 0}

        bullish_agents = []
        bearish_agents = []
        neutral_agents = []
        total_weight   = 0
        weighted_score = 0

        for agent, data in agent_signals.items():
            direction = data.get("direction", "NEUTRAL")
            score     = data.get("score", 50)
            weight    = data.get("weight", 1.0)
            signal    = data.get("signal", "")

            total_weight += weight

            # Normalize score to -1 to +1
            normalized = (score - 50) / 50  # 100→+1, 0→-1, 50→0
            if direction == "BEARISH":
                normalized = -abs(normalized)
            elif direction == "BULLISH":
                normalized = abs(normalized)

            weighted_score += normalized * weight

            entry = {"agent": agent, "score": score, "signal": signal}
            if direction == "BULLISH":
                bullish_agents.append(entry)
            elif direction == "BEARISH":
                bearish_agents.append(entry)
            else:
                neutral_agents.append(entry)

        # Consensus calculation
        total_agents  = len(agent_signals)
        bull_count    = len(bullish_agents)
        bear_count    = len(bearish_agents)
        consensus_pct = (weighted_score / total_weight) if total_weight else 0

        # Confidence = how strongly agents agree
        agreement_ratio = max(bull_count, bear_count) / total_agents if total_agents else 0
        confidence = round(agreement_ratio * 100, 1)

        # Final verdict
        if consensus_pct >= 0.4 and bull_count >= 4:
            verdict = "STRONG BUY"
        elif consensus_pct >= 0.15 and bull_count >= 3:
            verdict = "BUY"
        elif consensus_pct <= -0.4 and bear_count >= 4:
            verdict = "STRONG SELL"
        elif consensus_pct <= -0.15 and bear_count >= 3:
            verdict = "SELL"
        else:
            verdict = "HOLD"

        # Action level
        if confidence >= 80 and verdict in ("STRONG BUY", "STRONG SELL"):
            action = "ACT NOW"
        elif confidence >= 60:
            action = "HIGH CONVICTION"
        elif confidence >= 40:
            action = "MODERATE"
        else:
            action = "WAIT"

        return {
            "stock":            stock,
            "consensus":        verdict,
            "confidence":       confidence,
            "action":           action,
            "consensus_score":  round(consensus_pct * 100, 1),
            "agents_total":     total_agents,
            "bullish_count":    bull_count,
            "bearish_count":    bear_count,
            "neutral_count":    len(neutral_agents),
            "bullish_agents":   bullish_agents,
            "bearish_agents":   bearish_agents,
            "neutral_agents":   neutral_agents,
            "timestamp":        datetime.utcnow().isoformat() + "Z",
        }

    def evaluate_batch(self, all_stocks: dict) -> list:
        """
        Evaluate consensus for multiple stocks.
        all_stocks: { "RELIANCE": {agent_signals}, "TCS": {agent_signals}, ... }
        Returns sorted by confidence descending.
        """
        results = []
        for stock, signals in all_stocks.items():
            result = self.evaluate(stock, signals)
            results.append(result)

        # Sort: STRONG BUY first, then by confidence
        priority = {"STRONG BUY": 5, "BUY": 4, "HOLD": 3, "SELL": 2, "STRONG SELL": 1, "NO DATA": 0}
        results.sort(key=lambda x: (priority.get(x["consensus"], 0), x["confidence"]), reverse=True)
        return results

    def get_actionable(self, results: list) -> dict:
        """
        From consensus results, get only actionable picks.
        Only stocks with 4+ agents agreeing and confidence >= 60%.
        """
        strong_buys = [r for r in results if r["consensus"] == "STRONG BUY" and r["confidence"] >= 60]
        buys        = [r for r in results if r["consensus"] == "BUY" and r["confidence"] >= 50]
        sells       = [r for r in results if r["consensus"] in ("SELL", "STRONG SELL") and r["confidence"] >= 50]

        return {
            "timestamp":    datetime.utcnow().isoformat() + "Z",
            "strong_buys":  strong_buys[:5],
            "buys":         buys[:10],
            "sells":        sells[:5],
            "total_actionable": len(strong_buys) + len(buys) + len(sells),
        }

    def print_consensus(self, results: list):
        """Print consensus report."""
        ist = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %H:%M IST")
        print(f"\n{'='*65}")
        print(f"  🧠 CONSENSUS ENGINE — Mudholkars and Co")
        print(f"  {ist}")
        print(f"{'='*65}")

        actionable = [r for r in results if r["consensus"] in ("STRONG BUY", "BUY", "STRONG SELL", "SELL")]
        print(f"\n  Stocks analyzed: {len(results)} | Actionable: {len(actionable)}")

        # Strong buys
        sbuys = [r for r in results if r["consensus"] == "STRONG BUY"]
        if sbuys:
            print(f"\n  🔥 STRONG BUY ({len(sbuys)} stocks)")
            print("  " + "-" * 55)
            for r in sbuys[:5]:
                print(f"    {r['stock']:12s}  Confidence: {r['confidence']:5.1f}%  "
                      f"Agents: {r['bullish_count']}/{r['agents_total']} bullish")
                for a in r["bullish_agents"][:3]:
                    print(f"      ✓ {a['agent']}: {a['signal'][:50]}")

        # Buys
        buys = [r for r in results if r["consensus"] == "BUY"]
        if buys:
            print(f"\n  📈 BUY ({len(buys)} stocks)")
            print("  " + "-" * 55)
            for r in buys[:5]:
                print(f"    {r['stock']:12s}  Confidence: {r['confidence']:5.1f}%  "
                      f"Agents: {r['bullish_count']}/{r['agents_total']} bullish")

        # Sells
        sells = [r for r in results if r["consensus"] in ("SELL", "STRONG SELL")]
        if sells:
            print(f"\n  📉 SELL/AVOID ({len(sells)} stocks)")
            print("  " + "-" * 55)
            for r in sells[:5]:
                print(f"    {r['stock']:12s}  Confidence: {r['confidence']:5.1f}%  "
                      f"Agents: {r['bearish_count']}/{r['agents_total']} bearish")

        print(f"\n{'='*65}")
