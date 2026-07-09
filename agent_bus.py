"""
agent_bus.py
------------
Mudholkars and Co — Inter-Agent Communication Bus

All agents post their findings here. Other agents read from here.
Like a company Slack channel — everyone sees everything.

Flow:
  Scout finds volume spike → posts to bus
  Buzz Hunter finds trending stock → posts to bus
  Consensus Engine reads ALL posts → makes decision
  Portfolio Manager reads consensus → executes trade
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

BUS_FILE = Path("reports/agent_bus.json")


class AgentBus:
    """
    Shared communication channel between all agents.
    Agents POST signals. Consensus Engine READS all signals.
    """

    def __init__(self):
        self.signals = []
        self._load()

    def post(self, agent_name: str, stock: str, direction: str,
             score: int, signal: str, weight: float = 1.0,
             metadata: dict = None):
        """
        An agent posts a signal to the bus.
        Other agents and the consensus engine read this.
        """
        entry = {
            "agent":     agent_name,
            "stock":     stock.upper().replace(".NS", ""),
            "direction": direction,  # BULLISH / BEARISH / NEUTRAL
            "score":     score,       # 0-100
            "signal":    signal,      # human-readable reason
            "weight":    weight,
            "metadata":  metadata or {},
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        self.signals.append(entry)
        self._save()
        logger.debug(f"BUS: {agent_name} → {stock} {direction} (score={score})")

    def get_signals_for_stock(self, stock: str, max_age_hours: int = 4) -> list:
        """Get all recent signals for a specific stock."""
        stock = stock.upper().replace(".NS", "")
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        return [
            s for s in self.signals
            if s["stock"] == stock and
            datetime.fromisoformat(s["timestamp"].replace("Z", "")) >= cutoff
        ]

    def get_all_stocks_with_signals(self, max_age_hours: int = 4) -> dict:
        """Get all stocks that have signals, grouped by stock."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        grouped = defaultdict(list)
        for s in self.signals:
            ts = datetime.fromisoformat(s["timestamp"].replace("Z", ""))
            if ts >= cutoff:
                grouped[s["stock"]].append(s)
        return dict(grouped)

    def get_consensus_input(self, max_age_hours: int = 4) -> dict:
        """
        Format signals for the ConsensusEngine.
        Returns: { stock: { agent_name: signal_dict } }
        """
        grouped = self.get_all_stocks_with_signals(max_age_hours)
        consensus_input = {}
        for stock, signals in grouped.items():
            consensus_input[stock] = {}
            for s in signals:
                consensus_input[stock][s["agent"]] = {
                    "direction": s["direction"],
                    "score":     s["score"],
                    "signal":    s["signal"],
                    "weight":    s["weight"],
                }
        return consensus_input

    def get_hot_stocks(self, min_agents: int = 3, max_age_hours: int = 4) -> list:
        """Stocks mentioned by 3+ agents (high conviction candidates)."""
        grouped = self.get_all_stocks_with_signals(max_age_hours)
        hot = []
        for stock, signals in grouped.items():
            if len(signals) >= min_agents:
                bull = sum(1 for s in signals if s["direction"] == "BULLISH")
                bear = sum(1 for s in signals if s["direction"] == "BEARISH")
                hot.append({
                    "stock":       stock,
                    "total_agents": len(signals),
                    "bullish":     bull,
                    "bearish":     bear,
                    "consensus":   "BULLISH" if bull > bear else ("BEARISH" if bear > bull else "MIXED"),
                })
        hot.sort(key=lambda x: x["total_agents"], reverse=True)
        return hot

    def clear_old(self, hours: int = 24):
        """Remove signals older than N hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        self.signals = [
            s for s in self.signals
            if datetime.fromisoformat(s["timestamp"].replace("Z", "")) >= cutoff
        ]
        self._save()

    def _save(self):
        BUS_FILE.parent.mkdir(exist_ok=True)
        with open(BUS_FILE, "w") as f:
            json.dump({"signals": self.signals[-500:]}, f, indent=2)  # keep last 500

    def _load(self):
        if BUS_FILE.exists():
            try:
                with open(BUS_FILE) as f:
                    data = json.load(f)
                self.signals = data.get("signals", [])
            except:
                self.signals = []
