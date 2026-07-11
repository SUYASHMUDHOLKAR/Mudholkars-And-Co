"""
learning_engine.py
------------------
Mudholkars and Co — UNIFIED LEARNING ENGINE

Merged from self_improver.py + self_learning.py into one system.

Responsibilities:
  1. RECORD: Log every prediction and trade outcome
  2. VERIFY: Check past predictions against actual price moves
  3. LEARN: Update signal weights based on what worked
  4. ADJUST: Auto-tune thresholds (score, SL%, target%)
  5. ADVISE: Tell pipeline which stocks/signals to trust more
  6. REVIEW: Weekly self-assessment and improvement cycle

State files:
  reports/learning_state.json     — learned weights & thresholds
  reports/prediction_log.json     — all predictions with outcomes
  reports/trade_history.json      — completed trades for analysis

After 1 month:  System knows which signals to trust
After 3 months: System is significantly smarter than Day 1
After 1 year:   System has 1000+ data points, highly tuned
"""

import json
import logging
import numpy as np
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

import yfinance as yf

logger = logging.getLogger(__name__)

REPORTS_DIR = Path("reports")
STATE_FILE = REPORTS_DIR / "learning_state.json"
PREDICTION_LOG_FILE = REPORTS_DIR / "prediction_log.json"
TRADE_HISTORY_FILE = REPORTS_DIR / "trade_history.json"

# Default learning state
DEFAULT_STATE = {
    "min_score_threshold": 68.0,
    "total_predictions": 0,
    "correct_predictions": 0,
    "overall_accuracy": 0.0,
    "signal_accuracy": {},
    "stock_performance": {},
    "market_conditions": {},
    "day_of_week_stats": {},
    "threshold_history": [],
    "prefer_stocks": [],
    "avoid_stocks": [],
    "last_updated": None,
    "consecutive_wins": 0,
    "consecutive_losses": 0,
    "adjustment_step": 2.0,
    "min_threshold_floor": 40.0,
    "max_threshold_ceiling": 85.0,
}


class LearningEngine:
    """
    Unified learning engine — records, verifies, learns, adjusts.
    The system improves autonomously over time.
    """

    def __init__(self):
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        self.state = self._load_json(STATE_FILE, DEFAULT_STATE.copy())
        self.predictions = self._load_json(PREDICTION_LOG_FILE, [])
        self.trade_history = self._load_json(TRADE_HISTORY_FILE, [])

    # ═══════════════════════════════════════════════════════════
    # PERSISTENCE
    # ═══════════════════════════════════════════════════════════

    def _load_json(self, path: Path, default):
        try:
            if path.exists():
                data = json.loads(path.read_text())
                if data:
                    return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load {path.name}: {e}")
        return default

    def _save_state(self):
        self.state["last_updated"] = datetime.now().isoformat()
        STATE_FILE.write_text(json.dumps(self.state, indent=2, default=str))

    def _save_predictions(self):
        PREDICTION_LOG_FILE.write_text(json.dumps(self.predictions, indent=2, default=str))

    def _save_trades(self):
        TRADE_HISTORY_FILE.write_text(json.dumps(self.trade_history, indent=2, default=str))

    # ═══════════════════════════════════════════════════════════
    # 1. RECORD PREDICTIONS
    # ═══════════════════════════════════════════════════════════

    def record_prediction(self, symbol: str, signal_type: str, direction: str,
                          score: float, entry_price: float,
                          target_pct: float = 5.0, stop_loss_pct: float = 3.0):
        """Record a prediction for later verification."""
        prediction = {
            "id": f"{symbol}_{signal_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "symbol": symbol,
            "signal_type": signal_type,
            "direction": direction,
            "score": score,
            "entry_price": entry_price,
            "target_pct": target_pct,
            "stop_loss_pct": stop_loss_pct,
            "target_price": entry_price * (1 + target_pct / 100) if direction == "bullish"
                           else entry_price * (1 - target_pct / 100),
            "stop_loss_price": entry_price * (1 - stop_loss_pct / 100) if direction == "bullish"
                              else entry_price * (1 + stop_loss_pct / 100),
            "predicted_at": datetime.now().isoformat(),
            "outcome": None,  # "win" / "loss" / "expired"
            "outcome_price": None,
            "outcome_pct": None,
            "verified_at": None,
        }
        self.predictions.append(prediction)
        self.state["total_predictions"] = len([p for p in self.predictions if p.get("outcome")])
        self._save_predictions()
        self._save_state()
        logger.info(f"📝 Prediction recorded: {symbol} {direction} (score={score})")

    # ═══════════════════════════════════════════════════════════
    # 2. VERIFY PREDICTIONS (check outcomes)
    # ═══════════════════════════════════════════════════════════

    def verify_predictions(self, max_days: int = 21) -> dict:
        """
        Check unverified predictions against actual price data.
        Returns summary of newly verified predictions.
        """
        verified_count = 0
        wins = 0
        losses = 0

        for pred in self.predictions:
            if pred.get("outcome") is not None:
                continue

            pred_time = datetime.fromisoformat(pred["predicted_at"])
            days_since = (datetime.now() - pred_time).days

            if days_since < 1:
                continue  # Too early

            # Check if expired (max hold days exceeded)
            if days_since > max_days:
                pred["outcome"] = "expired"
                pred["verified_at"] = datetime.now().isoformat()
                verified_count += 1
                continue

            # Fetch price data
            try:
                symbol = pred["symbol"]
                if not symbol.endswith(".NS"):
                    symbol = f"{symbol}.NS"
                ticker = yf.Ticker(symbol)
                df = ticker.history(period=f"{min(days_since + 2, 30)}d")
                if df.empty:
                    continue

                for i in range(len(df)):
                    high = float(df["High"].iloc[i])
                    low = float(df["Low"].iloc[i])

                    if pred["direction"] == "bullish":
                        if high >= pred["target_price"]:
                            pred["outcome"] = "win"
                            pred["outcome_price"] = pred["target_price"]
                            pred["outcome_pct"] = pred["target_pct"]
                            wins += 1
                            break
                        elif low <= pred["stop_loss_price"]:
                            pred["outcome"] = "loss"
                            pred["outcome_price"] = pred["stop_loss_price"]
                            pred["outcome_pct"] = -pred["stop_loss_pct"]
                            losses += 1
                            break
                    else:  # bearish
                        if low <= pred["target_price"]:
                            pred["outcome"] = "win"
                            pred["outcome_price"] = pred["target_price"]
                            pred["outcome_pct"] = pred["target_pct"]
                            wins += 1
                            break
                        elif high >= pred["stop_loss_price"]:
                            pred["outcome"] = "loss"
                            pred["outcome_price"] = pred["stop_loss_price"]
                            pred["outcome_pct"] = -pred["stop_loss_pct"]
                            losses += 1
                            break

                if pred.get("outcome"):
                    pred["verified_at"] = datetime.now().isoformat()
                    verified_count += 1

            except Exception as e:
                logger.warning(f"  Verify failed for {pred['symbol']}: {e}")

        self._save_predictions()
        self._update_accuracy_stats()
        logger.info(f"📊 Verified {verified_count} predictions: {wins}W / {losses}L")
        return {"verified": verified_count, "wins": wins, "losses": losses}

    # ═══════════════════════════════════════════════════════════
    # 3. RECORD TRADE OUTCOMES
    # ═══════════════════════════════════════════════════════════

    def record_trade(self, trade: dict):
        """
        Record a completed trade for learning.
        trade = {
            symbol, entry, exit, pnl, pnl_pct, reason,
            signals_used: [list of agent names that agreed],
            score_at_entry, market_condition, sector, day_of_week
        }
        """
        trade["recorded_at"] = datetime.now().isoformat()
        trade["win"] = trade.get("pnl", 0) > 0
        self.trade_history.append(trade)
        self._save_trades()

        # Update all learning stats
        self._update_signal_accuracy(trade)
        self._update_stock_performance(trade)
        self._update_market_condition_stats(trade)
        self._update_day_of_week(trade)
        self._adjust_thresholds(trade)
        self._save_state()

        icon = "✅" if trade["win"] else "❌"
        logger.info(f"{icon} Trade recorded: {trade.get('symbol')} | PnL: {trade.get('pnl_pct', 0):+.1f}%")

    # ═══════════════════════════════════════════════════════════
    # 4. LEARNING ALGORITHMS
    # ═══════════════════════════════════════════════════════════

    def _update_signal_accuracy(self, trade: dict):
        """Track win rate per signal source and adjust weights."""
        signals = trade.get("signals_used", [])
        win = trade.get("win", False)
        signal_stats = self.state.setdefault("signal_accuracy", {})

        for sig in signals:
            if sig not in signal_stats:
                signal_stats[sig] = {"wins": 0, "total": 0, "weight": 1.0}
            signal_stats[sig]["total"] += 1
            if win:
                signal_stats[sig]["wins"] += 1
            # Weight = 0.5 to 2.0 based on win rate
            wr = signal_stats[sig]["wins"] / signal_stats[sig]["total"]
            signal_stats[sig]["win_rate"] = round(wr * 100, 1)
            signal_stats[sig]["weight"] = round(0.5 + wr * 1.5, 2)

    def _update_stock_performance(self, trade: dict):
        """Track which stocks we're good/bad at trading."""
        stock = trade.get("symbol", "UNKNOWN")
        stock_stats = self.state.setdefault("stock_performance", {})
        if stock not in stock_stats:
            stock_stats[stock] = {"wins": 0, "losses": 0, "total_pnl": 0, "trades": 0, "avoid": False}
        stock_stats[stock]["trades"] += 1
        if trade.get("win"):
            stock_stats[stock]["wins"] += 1
        else:
            stock_stats[stock]["losses"] += 1
        stock_stats[stock]["total_pnl"] += trade.get("pnl", 0)

        # Auto-mark stocks to avoid (3+ consecutive losses, 0 wins)
        s = stock_stats[stock]
        if s["losses"] >= 3 and s["wins"] == 0:
            s["avoid"] = True
            if stock not in self.state.get("avoid_stocks", []):
                self.state.setdefault("avoid_stocks", []).append(stock)
                logger.info(f"🚫 LEARNED: Avoid {stock} — {s['losses']} losses, 0 wins")

        # Prefer stocks with good track record (5+ trades, 60%+ win rate)
        if s["trades"] >= 5:
            wr = s["wins"] / s["trades"]
            if wr >= 0.6 and stock not in self.state.get("prefer_stocks", []):
                self.state.setdefault("prefer_stocks", []).append(stock)

    def _update_market_condition_stats(self, trade: dict):
        """Track win rate in different market conditions."""
        condition = trade.get("market_condition", "UNKNOWN")
        cond_stats = self.state.setdefault("market_conditions", {})
        if condition not in cond_stats:
            cond_stats[condition] = {"wins": 0, "total": 0, "win_rate": 0}
        cond_stats[condition]["total"] += 1
        if trade.get("win"):
            cond_stats[condition]["wins"] += 1
        t = cond_stats[condition]["total"]
        cond_stats[condition]["win_rate"] = round(cond_stats[condition]["wins"] / t * 100, 1)

    def _update_day_of_week(self, trade: dict):
        """Track which days are best for trading."""
        day = trade.get("day_of_week", datetime.now().strftime("%A"))
        day_stats = self.state.setdefault("day_of_week_stats", {})
        if day not in day_stats:
            day_stats[day] = {"wins": 0, "total": 0, "win_rate": 0}
        day_stats[day]["total"] += 1
        if trade.get("win"):
            day_stats[day]["wins"] += 1
        t = day_stats[day]["total"]
        day_stats[day]["win_rate"] = round(day_stats[day]["wins"] / t * 100, 1)

    def _adjust_thresholds(self, trade: dict):
        """Auto-adjust minimum score threshold based on streak."""
        if trade.get("win"):
            self.state["consecutive_wins"] = self.state.get("consecutive_wins", 0) + 1
            self.state["consecutive_losses"] = 0
        else:
            self.state["consecutive_losses"] = self.state.get("consecutive_losses", 0) + 1
            self.state["consecutive_wins"] = 0

        step = self.state.get("adjustment_step", 2.0)
        floor = self.state.get("min_threshold_floor", 40.0)
        ceiling = self.state.get("max_threshold_ceiling", 85.0)
        threshold = self.state.get("min_score_threshold", 68.0)

        # 3 consecutive losses → raise threshold (be more selective)
        if self.state["consecutive_losses"] >= 3:
            threshold = min(ceiling, threshold + step)
            self.state["consecutive_losses"] = 0
            logger.info(f"📈 Threshold raised to {threshold} (3 losses)")

        # 5 consecutive wins → lower threshold (be more aggressive)
        elif self.state["consecutive_wins"] >= 5:
            threshold = max(floor, threshold - step)
            self.state["consecutive_wins"] = 0
            logger.info(f"📉 Threshold lowered to {threshold} (5 wins)")

        self.state["min_score_threshold"] = threshold
        self.state.setdefault("threshold_history", []).append({
            "date": datetime.now().isoformat(),
            "threshold": threshold,
        })

    def _update_accuracy_stats(self):
        """Update overall accuracy stats from prediction log."""
        verified = [p for p in self.predictions if p.get("outcome") in ("win", "loss")]
        if verified:
            wins = len([p for p in verified if p["outcome"] == "win"])
            self.state["total_predictions"] = len(verified)
            self.state["correct_predictions"] = wins
            self.state["overall_accuracy"] = round(wins / len(verified) * 100, 1)
        self._save_state()

    # ═══════════════════════════════════════════════════════════
    # 5. ADVISE: Knowledge the pipeline can query
    # ═══════════════════════════════════════════════════════════

    def get_learned_weights(self) -> Dict[str, float]:
        """Return learned weights for each signal source."""
        signal_stats = self.state.get("signal_accuracy", {})
        return {sig: data.get("weight", 1.0) for sig, data in signal_stats.items()}

    def should_avoid_stock(self, symbol: str) -> bool:
        """Check if we've learned to avoid this stock."""
        return symbol in self.state.get("avoid_stocks", [])

    def get_preferred_stocks(self) -> list:
        """Get stocks we historically trade well."""
        return self.state.get("prefer_stocks", [])

    def get_minimum_score(self) -> float:
        """Current auto-adjusted minimum entry score."""
        return self.state.get("min_score_threshold", 68.0)

    def get_best_days(self) -> list:
        """Get days with highest win rate."""
        day_stats = self.state.get("day_of_week_stats", {})
        sorted_days = sorted(day_stats.items(), key=lambda x: x[1].get("win_rate", 0), reverse=True)
        return [d[0] for d in sorted_days if d[1].get("win_rate", 0) > 50]

    # ═══════════════════════════════════════════════════════════
    # 6. WEEKLY REVIEW
    # ═══════════════════════════════════════════════════════════

    def run_weekly_review(self) -> dict:
        """
        Weekly self-assessment. Call this on Sundays.
        Verifies all pending predictions and produces a learning report.
        """
        logger.info("🧠 Weekly Learning Review...")

        # Step 1: Verify all pending predictions
        verify_result = self.verify_predictions()

        # Step 2: Calculate this week's stats
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        recent_trades = [t for t in self.trade_history if t.get("recorded_at", "") > week_ago]
        recent_preds = [p for p in self.predictions
                       if p.get("verified_at", "") and p["verified_at"] > week_ago]

        week_wins = len([t for t in recent_trades if t.get("win")])
        week_total = len(recent_trades)
        week_wr = (week_wins / week_total * 100) if week_total else 0

        # Step 3: Identify strongest and weakest signals
        signal_stats = self.state.get("signal_accuracy", {})
        best_signals = sorted(signal_stats.items(), key=lambda x: x[1].get("win_rate", 0), reverse=True)[:3]
        worst_signals = sorted(signal_stats.items(), key=lambda x: x[1].get("win_rate", 0))[:3]

        review = {
            "date": datetime.now().isoformat(),
            "week_trades": week_total,
            "week_win_rate": round(week_wr, 1),
            "overall_accuracy": self.state.get("overall_accuracy", 0),
            "current_threshold": self.state.get("min_score_threshold", 68),
            "predictions_verified": verify_result,
            "best_signals": [(s[0], s[1].get("win_rate", 0)) for s in best_signals],
            "worst_signals": [(s[0], s[1].get("win_rate", 0)) for s in worst_signals],
            "preferred_stocks": self.state.get("prefer_stocks", []),
            "avoid_stocks": self.state.get("avoid_stocks", []),
            "total_trades_all_time": len(self.trade_history),
            "total_predictions": self.state.get("total_predictions", 0),
        }

        logger.info(f"  Week: {week_total} trades, {week_wr:.0f}% WR")
        logger.info(f"  Overall accuracy: {self.state.get('overall_accuracy', 0):.1f}%")
        logger.info(f"  Current threshold: {self.state.get('min_score_threshold', 68)}")
        logger.info(f"  Avoid: {self.state.get('avoid_stocks', [])}")

        self._save_state()
        return review


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", action="store_true", help="Run weekly review")
    parser.add_argument("--verify", action="store_true", help="Verify pending predictions")
    parser.add_argument("--status", action="store_true", help="Show learning status")
    args = parser.parse_args()

    engine = LearningEngine()

    if args.review:
        result = engine.run_weekly_review()
        print(json.dumps(result, indent=2))
    elif args.verify:
        result = engine.verify_predictions()
        print(json.dumps(result, indent=2))
    elif args.status:
        print(f"Overall accuracy: {engine.state.get('overall_accuracy', 0):.1f}%")
        print(f"Min score threshold: {engine.get_minimum_score()}")
        print(f"Total trades: {len(engine.trade_history)}")
        print(f"Preferred stocks: {engine.get_preferred_stocks()}")
        print(f"Avoid stocks: {engine.state.get('avoid_stocks', [])}")
        print(f"Best signals: {engine.get_learned_weights()}")
    else:
        print("Use --review, --verify, or --status")
