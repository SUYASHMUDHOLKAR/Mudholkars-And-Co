"""
Self-Improvement Engine
=======================
Tracks prediction accuracy, auto-adjusts thresholds, and continuously
improves signal reliability over time.

Runs on every pipeline cycle to compare predictions vs actual outcomes.
State persisted to reports/self_improvement_state.json
Prediction log at reports/prediction_log.json
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yfinance as yf

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

# File paths
REPORTS_DIR = Path("reports")
PREDICTION_LOG_PATH = REPORTS_DIR / "prediction_log.json"
STATE_PATH = REPORTS_DIR / "self_improvement_state.json"

# Default configuration
DEFAULT_STATE = {
    "min_score_threshold": 60.0,
    "total_predictions": 0,
    "correct_predictions": 0,
    "overall_accuracy": 0.0,
    "accuracy_by_signal": {},
    "threshold_history": [],
    "last_updated": None,
    "consecutive_wins": 0,
    "consecutive_losses": 0,
    "adjustment_step": 2.0,
    "min_threshold_floor": 40.0,
    "max_threshold_ceiling": 85.0,
}


class SelfImprover:
    """
    Self-improvement engine that tracks prediction accuracy and
    auto-adjusts trading thresholds based on performance.
    """

    def __init__(self):
        self._ensure_reports_dir()
        self.state = self._load_state()
        self.prediction_log = self._load_prediction_log()

    def _ensure_reports_dir(self):
        """Create reports directory if it doesn't exist."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> Dict:
        """Load state from disk or initialize with defaults."""
        try:
            if STATE_PATH.exists():
                with open(STATE_PATH, "r") as f:
                    state = json.load(f)
                logger.info(f"Loaded state: accuracy={state.get('overall_accuracy', 0):.1f}%")
                return state
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load state, using defaults: {e}")
        return DEFAULT_STATE.copy()

    def _save_state(self):
        """Persist current state to disk."""
        try:
            self.state["last_updated"] = datetime.now().isoformat()
            with open(STATE_PATH, "w") as f:
                json.dump(self.state, f, indent=2, default=str)
            logger.info("State saved successfully.")
        except IOError as e:
            logger.error(f"Failed to save state: {e}")

    def _load_prediction_log(self) -> List[Dict]:
        """Load prediction log from disk."""
        try:
            if PREDICTION_LOG_PATH.exists():
                with open(PREDICTION_LOG_PATH, "r") as f:
                    log = json.load(f)
                logger.info(f"Loaded {len(log)} predictions from log.")
                return log
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load prediction log: {e}")
        return []

    def _save_prediction_log(self):
        """Persist prediction log to disk."""
        try:
            with open(PREDICTION_LOG_PATH, "w") as f:
                json.dump(self.prediction_log, f, indent=2, default=str)
        except IOError as e:
            logger.error(f"Failed to save prediction log: {e}")


    def record_prediction(self, symbol: str, signal_type: str, direction: str,
                          score: float, entry_price: float, target_pct: float = 2.0,
                          stop_loss_pct: float = 1.0):
        """
        Record a new prediction for later verification.

        Args:
            symbol: Stock ticker symbol
            signal_type: Type of signal (e.g., 'breakout', 'candlestick', 'gap')
            direction: 'bullish' or 'bearish'
            score: Confidence score of the signal
            entry_price: Price at prediction time
            target_pct: Expected profit target percentage
            stop_loss_pct: Stop loss percentage
        """
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
            "outcome": None,
            "outcome_price": None,
            "outcome_pct": None,
            "verified_at": None,
        }
        self.prediction_log.append(prediction)
        self._save_prediction_log()
        logger.info(f"Recorded prediction: {symbol} {signal_type} {direction} score={score}")

    def _check_outcome(self, prediction: Dict) -> Optional[Dict]:
        """
        Check if a prediction has reached target or stop-loss.

        Returns updated prediction dict or None if still pending.
        """
        if prediction["outcome"] is not None:
            return prediction

        symbol = prediction["symbol"]
        try:
            ticker = yf.Ticker(symbol)
            # Get data since prediction was made
            pred_time = datetime.fromisoformat(prediction["predicted_at"])
            days_since = (datetime.now() - pred_time).days

            if days_since < 1:
                return None  # Too early to check

            df = ticker.history(period=f"{min(days_since + 2, 30)}d")
            if df.empty:
                return None

            entry_price = prediction["entry_price"]
            direction = prediction["direction"]
            target_price = prediction["target_price"]
            stop_loss_price = prediction["stop_loss_price"]

            # Check each day after prediction
            for idx in range(len(df)):
                high = float(df["High"].iloc[idx])
                low = float(df["Low"].iloc[idx])
                close = float(df["Close"].iloc[idx])

                if direction == "bullish":
                    if high >= target_price:
                        prediction["outcome"] = "win"
                        prediction["outcome_price"] = target_price
                        prediction["outcome_pct"] = prediction["target_pct"]
                        break
                    elif low <= stop_loss_price:
                        prediction["outcome"] = "loss"
                        prediction["outcome_price"] = stop_loss_price
                        prediction["outcome_pct"] = -prediction["stop_loss_pct"]
                        break
                else:  # bearish
                    if low <= target_price:
                        prediction["outcome"] = "win"
                        prediction["outcome_price"] = target_price
                        prediction["outcome_pct"] = prediction["target_pct"]
                        break
                    elif high >= stop_loss_price:
                        prediction["outcome"] = "loss"
                        prediction["outcome_price"] = stop_loss_price
                        prediction["outcome_pct"] = -prediction["stop_loss_pct"]
                        break

            # If exceeded max holding period (5 days), mark at current price
            if prediction["outcome"] is None and days_since >= 5:
                current_price = float(df["Close"].iloc[-1])
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
                if direction == "bearish":
                    pnl_pct = -pnl_pct
                prediction["outcome"] = "win" if pnl_pct > 0 else "loss"
                prediction["outcome_price"] = current_price
                prediction["outcome_pct"] = round(pnl_pct, 2)

            if prediction["outcome"] is not None:
                prediction["verified_at"] = datetime.now().isoformat()

        except Exception as e:
            logger.error(f"Error checking outcome for {prediction['id']}: {e}")
            return None

        return prediction


    def improve(self) -> Dict:
        """
        Main improvement cycle. Compares predictions to actual outcomes
        and adjusts thresholds accordingly.

        Returns:
            Dict with improvement summary
        """
        logger.info("=" * 50)
        logger.info("SELF-IMPROVEMENT CYCLE STARTING")
        logger.info("=" * 50)

        newly_resolved = 0
        wins = 0
        losses = 0

        # Check all unresolved predictions
        for i, pred in enumerate(self.prediction_log):
            if pred["outcome"] is None:
                updated = self._check_outcome(pred)
                if updated and updated["outcome"] is not None:
                    self.prediction_log[i] = updated
                    newly_resolved += 1
                    if updated["outcome"] == "win":
                        wins += 1
                        self.state["correct_predictions"] += 1
                        self.state["consecutive_wins"] += 1
                        self.state["consecutive_losses"] = 0
                    else:
                        losses += 1
                        self.state["consecutive_losses"] += 1
                        self.state["consecutive_wins"] = 0
                    self.state["total_predictions"] += 1

                    # Update accuracy by signal type
                    sig_type = updated["signal_type"]
                    if sig_type not in self.state["accuracy_by_signal"]:
                        self.state["accuracy_by_signal"][sig_type] = {
                            "total": 0, "correct": 0, "accuracy": 0.0
                        }
                    self.state["accuracy_by_signal"][sig_type]["total"] += 1
                    if updated["outcome"] == "win":
                        self.state["accuracy_by_signal"][sig_type]["correct"] += 1
                    sig_stats = self.state["accuracy_by_signal"][sig_type]
                    sig_stats["accuracy"] = round(
                        (sig_stats["correct"] / sig_stats["total"]) * 100, 1
                    )

        # Update overall accuracy
        if self.state["total_predictions"] > 0:
            self.state["overall_accuracy"] = round(
                (self.state["correct_predictions"] / self.state["total_predictions"]) * 100, 1
            )

        # Auto-adjust threshold
        self._adjust_threshold()

        # Save everything
        self._save_prediction_log()
        self._save_state()

        summary = {
            "newly_resolved": newly_resolved,
            "wins": wins,
            "losses": losses,
            "overall_accuracy": self.state["overall_accuracy"],
            "current_threshold": self.state["min_score_threshold"],
            "total_predictions": self.state["total_predictions"],
            "accuracy_by_signal": self.state["accuracy_by_signal"],
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"Improvement cycle complete: {newly_resolved} resolved, "
                    f"accuracy={self.state['overall_accuracy']}%, "
                    f"threshold={self.state['min_score_threshold']}")
        return summary

    def _adjust_threshold(self):
        """
        Auto-adjust minimum score threshold based on performance.
        - Winning streak (5+): lower threshold to take more trades
        - Losing streak (3+): raise threshold to be more selective
        """
        step = self.state["adjustment_step"]
        floor = self.state["min_threshold_floor"]
        ceiling = self.state["max_threshold_ceiling"]
        current = self.state["min_score_threshold"]

        old_threshold = current

        # Lower threshold if winning consistently
        if self.state["consecutive_wins"] >= 5:
            current = max(floor, current - step)
            logger.info(f"Winning streak! Lowering threshold: {old_threshold} -> {current}")

        # Raise threshold if losing
        elif self.state["consecutive_losses"] >= 3:
            current = min(ceiling, current + step)
            logger.info(f"Losing streak. Raising threshold: {old_threshold} -> {current}")

        # Gradual adjustment based on overall accuracy
        elif self.state["total_predictions"] >= 10:
            accuracy = self.state["overall_accuracy"]
            if accuracy >= 70:
                current = max(floor, current - step * 0.5)
            elif accuracy < 45:
                current = min(ceiling, current + step * 0.5)

        self.state["min_score_threshold"] = round(current, 1)

        if old_threshold != current:
            self.state["threshold_history"].append({
                "from": old_threshold,
                "to": current,
                "reason": f"wins={self.state['consecutive_wins']} losses={self.state['consecutive_losses']}",
                "timestamp": datetime.now().isoformat(),
            })

    def get_accuracy(self) -> Dict:
        """
        Get current system accuracy percentage and breakdown.

        Returns:
            Dict with overall accuracy, per-signal accuracy, and threshold info
        """
        return {
            "overall_accuracy_pct": self.state["overall_accuracy"],
            "total_predictions": self.state["total_predictions"],
            "correct_predictions": self.state["correct_predictions"],
            "current_threshold": self.state["min_score_threshold"],
            "accuracy_by_signal": self.state["accuracy_by_signal"],
            "consecutive_wins": self.state["consecutive_wins"],
            "consecutive_losses": self.state["consecutive_losses"],
            "last_updated": self.state["last_updated"],
        }

    def get_min_score_threshold(self) -> float:
        """Get the current minimum score threshold for trade entry."""
        return self.state["min_score_threshold"]

    def get_signal_reliability(self) -> Dict[str, float]:
        """Get reliability ranking of each signal type."""
        reliability = {}
        for sig_type, stats in self.state["accuracy_by_signal"].items():
            if stats["total"] >= 3:  # Minimum sample size
                reliability[sig_type] = stats["accuracy"]
        return dict(sorted(reliability.items(), key=lambda x: x[1], reverse=True))

    def reset(self):
        """Reset all state and logs (use with caution)."""
        logger.warning("Resetting self-improvement state!")
        self.state = DEFAULT_STATE.copy()
        self.prediction_log = []
        self._save_state()
        self._save_prediction_log()


if __name__ == "__main__":
    improver = SelfImprover()

    # Show current accuracy
    accuracy = improver.get_accuracy()
    print(f"\n{'='*50}")
    print(f"SELF-IMPROVEMENT ENGINE STATUS")
    print(f"{'='*50}")
    print(f"Overall Accuracy: {accuracy['overall_accuracy_pct']}%")
    print(f"Total Predictions: {accuracy['total_predictions']}")
    print(f"Current Threshold: {accuracy['current_threshold']}")
    print(f"Consecutive Wins: {accuracy['consecutive_wins']}")
    print(f"Consecutive Losses: {accuracy['consecutive_losses']}")
    print(f"\nAccuracy by Signal Type:")
    for sig, stats in accuracy['accuracy_by_signal'].items():
        print(f"  {sig}: {stats.get('accuracy', 0)}% ({stats.get('total', 0)} trades)")

    # Run improvement cycle
    print(f"\nRunning improvement cycle...")
    result = improver.improve()
    print(f"Resolved: {result['newly_resolved']} | Wins: {result['wins']} | Losses: {result['losses']}")
    print(f"Updated Accuracy: {result['overall_accuracy']}%")
    print(f"Updated Threshold: {result['current_threshold']}")
