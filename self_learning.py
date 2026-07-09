"""
self_learning.py
----------------
Mudholkars and Co — SELF-LEARNING ENGINE

This is what makes the system improve over time WITHOUT manual intervention.
Every week it:
  1. Reviews all trades taken (wins + losses)
  2. Identifies WHICH signals led to wins vs losses
  3. Auto-adjusts signal weights (what worked gets more weight)
  4. Tracks accuracy per stock, per sector, per signal type
  5. Updates ML model with new data points
  6. Saves learned parameters for next run

After 1 month:  System knows which signals to trust
After 3 months: System is significantly smarter than Day 1
After 1 year:   System has 1000+ data points, highly tuned
After 2 years:  System knows market patterns deeply
"""

import json
import logging
import numpy as np
from datetime import datetime, date, timedelta
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)

LEARNING_FILE = Path("reports/learning_state.json")
TRADE_HISTORY_FILE = Path("reports/trade_history.json")


class SelfLearningEngine:
    """
    The system learns from every trade.
    Adjusts weights, thresholds, and preferences automatically.
    """

    def __init__(self):
        self.state = self._load_state()
        self.trade_history = self._load_trades()

    # ═══════════════════════════════════════════════════════════
    # CORE: Record every trade outcome
    # ═══════════════════════════════════════════════════════════

    def record_trade(self, trade: dict):
        """
        Record a completed trade for learning.
        trade = {
            symbol, entry, exit, pnl, pnl_pct, reason,
            signals_used: [list of which agents agreed],
            score_at_entry, market_condition, sector
        }
        """
        trade["recorded_at"] = datetime.utcnow().isoformat()
        trade["win"] = trade.get("pnl", 0) > 0
        self.trade_history.append(trade)
        self._save_trades()

        # Update running stats
        self._update_signal_accuracy(trade)
        self._update_stock_performance(trade)
        self._update_market_condition_stats(trade)
        self._save_state()

    # ═══════════════════════════════════════════════════════════
    # LEARN: Which signals are most reliable?
    # ═══════════════════════════════════════════════════════════

    def _update_signal_accuracy(self, trade: dict):
        """Track win rate per signal source."""
        signals = trade.get("signals_used", [])
        win = trade.get("win", False)

        signal_stats = self.state.setdefault("signal_accuracy", {})
        for sig in signals:
            if sig not in signal_stats:
                signal_stats[sig] = {"wins": 0, "total": 0, "weight": 1.0}
            signal_stats[sig]["total"] += 1
            if win:
                signal_stats[sig]["wins"] += 1
            # Recalculate win rate and adjust weight
            wr = signal_stats[sig]["wins"] / signal_stats[sig]["total"]
            # Weight = 0.5 to 2.0 based on win rate
            signal_stats[sig]["win_rate"] = round(wr * 100, 1)
            signal_stats[sig]["weight"] = round(0.5 + wr * 1.5, 2)

    def _update_stock_performance(self, trade: dict):
        """Track which stocks we're good/bad at trading."""
        stock = trade.get("symbol", "UNKNOWN")
        stock_stats = self.state.setdefault("stock_performance", {})
        if stock not in stock_stats:
            stock_stats[stock] = {"wins": 0, "losses": 0, "total_pnl": 0, "avoid": False}
        if trade.get("win"):
            stock_stats[stock]["wins"] += 1
        else:
            stock_stats[stock]["losses"] += 1
        stock_stats[stock]["total_pnl"] += trade.get("pnl", 0)

        # If we lost 3+ times on same stock, mark as avoid
        if stock_stats[stock]["losses"] >= 3 and stock_stats[stock]["wins"] == 0:
            stock_stats[stock]["avoid"] = True
            logger.info(f"LEARNED: Avoid {stock} — lost {stock_stats[stock]['losses']} times")

    def _update_market_condition_stats(self, trade: dict):
        """Track win rate in different market conditions."""
        condition = trade.get("market_condition", "UNKNOWN")  # BULLISH/BEARISH/SIDEWAYS
        cond_stats = self.state.setdefault("market_conditions", {})
        if condition not in cond_stats:
            cond_stats[condition] = {"wins": 0, "total": 0}
        cond_stats[condition]["total"] += 1
        if trade.get("win"):
            cond_stats[condition]["wins"] += 1

    # ═══════════════════════════════════════════════════════════
    # APPLY: Use learned knowledge for next trade
    # ═══════════════════════════════════════════════════════════

    def get_learned_weights(self) -> dict:
        """
        Return current learned weights for each signal source.
        Agents that historically worked better get higher weight.
        """
        signal_stats = self.state.get("signal_accuracy", {})
        weights = {}
        for sig, data in signal_stats.items():
            weights[sig] = data.get("weight", 1.0)
        return weights

    def should_avoid_stock(self, symbol: str) -> bool:
        """Check if we've learned to avoid this stock."""
        stock_stats = self.state.get("stock_performance", {})
        return stock_stats.get(symbol, {}).get("avoid", False)

    def get_minimum_score(self) -> int:
        """
        Auto-adjust minimum entry score based on recent performance.
        If win rate < 50% → raise threshold (be more selective)
        If win rate > 70% → lower threshold (take more trades)
        """
        recent = self.trade_history[-20:]  # last 20 trades
        if len(recent) < 5:
            return 72  # default

        wins = sum(1 for t in recent if t.get("win"))
        wr = wins / len(recent)

        if wr < 0.45:
            return 78  # be more selective
        elif wr < 0.55:
            return 75
        elif wr > 0.75:
            return 68  # can afford to take more trades
        elif wr > 0.65:
            return 70
        else:
            return 72  # default

    def get_best_performing_signals(self, top_n: int = 3) -> list:
        """Which signal sources have the best track record?"""
        signal_stats = self.state.get("signal_accuracy", {})
        ranked = sorted(signal_stats.items(),
                       key=lambda x: x[1].get("win_rate", 0), reverse=True)
        return [(name, data) for name, data in ranked[:top_n]]

    # ═══════════════════════════════════════════════════════════
    # WEEKLY REVIEW: Auto-runs every Sunday
    # ═══════════════════════════════════════════════════════════

    def weekly_review(self) -> dict:
        """
        Run every week. Analyzes past week's trades and adjusts system.
        This is what makes the system IMPROVE over time.
        """
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent = [t for t in self.trade_history
                  if t.get("recorded_at", "") >= week_ago.isoformat()]

        if not recent:
            return {"status": "no_trades_this_week"}

        wins = sum(1 for t in recent if t.get("win"))
        total = len(recent)
        wr = wins / total * 100
        total_pnl = sum(t.get("pnl", 0) for t in recent)
        avg_win = np.mean([t["pnl"] for t in recent if t.get("win")]) if wins else 0
        avg_loss = np.mean([t["pnl"] for t in recent if not t.get("win")]) if (total - wins) else 0

        # Auto-adjustments
        adjustments = []

        # 1. Adjust minimum score threshold
        new_min_score = self.get_minimum_score()
        old_min_score = self.state.get("min_score", 72)
        if new_min_score != old_min_score:
            adjustments.append(f"Min score: {old_min_score} → {new_min_score}")
            self.state["min_score"] = new_min_score

        # 2. Identify worst performing signal and reduce weight
        signal_stats = self.state.get("signal_accuracy", {})
        worst_signal = min(signal_stats.items(),
                         key=lambda x: x[1].get("win_rate", 50),
                         default=(None, None))
        if worst_signal[0] and worst_signal[1].get("win_rate", 50) < 40:
            worst_signal[1]["weight"] = max(0.3, worst_signal[1]["weight"] - 0.1)
            adjustments.append(f"Reduced weight of {worst_signal[0]} (WR={worst_signal[1]['win_rate']}%)")

        # 3. Boost best performing signal
        best_signal = max(signal_stats.items(),
                        key=lambda x: x[1].get("win_rate", 50),
                        default=(None, None))
        if best_signal[0] and best_signal[1].get("win_rate", 50) > 70:
            best_signal[1]["weight"] = min(2.5, best_signal[1]["weight"] + 0.1)
            adjustments.append(f"Boosted weight of {best_signal[0]} (WR={best_signal[1]['win_rate']}%)")

        # 4. Track overall system accuracy trend
        accuracy_history = self.state.setdefault("weekly_accuracy", [])
        accuracy_history.append({
            "week": date.today().isoformat(),
            "win_rate": round(wr, 1),
            "trades": total,
            "pnl": round(total_pnl, 2),
        })
        # Keep last 52 weeks
        self.state["weekly_accuracy"] = accuracy_history[-52:]

        self._save_state()

        review = {
            "period": "last_7_days",
            "trades": total,
            "wins": wins,
            "win_rate": round(wr, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "adjustments": adjustments,
            "new_min_score": new_min_score,
            "system_accuracy_trend": accuracy_history[-4:],
            "best_signal": best_signal[0] if best_signal[0] else "N/A",
            "worst_signal": worst_signal[0] if worst_signal[0] else "N/A",
        }

        logger.info(f"WEEKLY REVIEW: WR={wr:.0f}% | PnL=₹{total_pnl:+.0f} | Adjustments: {len(adjustments)}")
        return review

    # ═══════════════════════════════════════════════════════════
    # REPORT: Show what system has learned
    # ═══════════════════════════════════════════════════════════

    def get_learning_report(self) -> str:
        """Human-readable report of what the system has learned."""
        total_trades = len(self.trade_history)
        if total_trades == 0:
            return "No trades recorded yet. Learning starts after first trade."

        wins = sum(1 for t in self.trade_history if t.get("win"))
        overall_wr = wins / total_trades * 100
        total_pnl = sum(t.get("pnl", 0) for t in self.trade_history)

        lines = [
            "=" * 55,
            "  🧠 SELF-LEARNING REPORT — What the system knows",
            "=" * 55,
            f"  Total trades learned from: {total_trades}",
            f"  Overall win rate: {overall_wr:.1f}%",
            f"  Total P&L: ₹{total_pnl:+,.0f}",
            "",
            "  SIGNAL RELIABILITY (learned):",
        ]

        for sig, data in sorted(
            self.state.get("signal_accuracy", {}).items(),
            key=lambda x: x[1].get("win_rate", 0), reverse=True
        ):
            lines.append(f"    {sig:15s}: WR={data.get('win_rate',0):5.1f}% | Weight={data.get('weight',1.0):.2f} | Trades={data.get('total',0)}")

        avoided = [s for s, d in self.state.get("stock_performance", {}).items() if d.get("avoid")]
        if avoided:
            lines.append(f"\n  AVOID LIST (learned from losses): {', '.join(avoided)}")

        lines.append(f"\n  Current min score threshold: {self.state.get('min_score', 72)}")
        lines.append("=" * 55)
        return "\n".join(lines)

    # ═══════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════

    def _load_state(self) -> dict:
        if LEARNING_FILE.exists():
            try:
                with open(LEARNING_FILE) as f:
                    return json.load(f)
            except:
                pass
        return {"min_score": 72, "signal_accuracy": {}, "stock_performance": {}, "weekly_accuracy": []}

    def _save_state(self):
        LEARNING_FILE.parent.mkdir(exist_ok=True)
        with open(LEARNING_FILE, "w") as f:
            json.dump(self.state, f, indent=2)

    def _load_trades(self) -> list:
        if TRADE_HISTORY_FILE.exists():
            try:
                with open(TRADE_HISTORY_FILE) as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save_trades(self):
        TRADE_HISTORY_FILE.parent.mkdir(exist_ok=True)
        with open(TRADE_HISTORY_FILE, "w") as f:
            json.dump(self.trade_history[-500:], f, indent=2)  # keep last 500
