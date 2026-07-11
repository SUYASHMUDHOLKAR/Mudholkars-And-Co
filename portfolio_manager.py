"""
portfolio_manager.py
--------------------
Mudholkars and Co — Portfolio Manager

Capital: ₹10,00,000 (₹10 Lakh) — Target: ₹1 Crore
Strategy: Swing + Positional with tight risk control

With ₹10L:
  - Max 5 positions at a time (~₹2L each)
  - Targets: +5-15% per trade
  - Stop-loss: -3% strict (trail after +3%)
  - Focus: high-conviction consensus plays (4+ agents agree)
  - Hold time: 1-21 days (swing + positional)
  - Expected: 5-10 trades/month (quality over quantity)
"""

import os
import json
import logging
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

CAPITAL = int(os.environ.get("INITIAL_CAPITAL", 1000000))


class PortfolioManager:
    """
    Portfolio manager for ₹10L capital.
    Quality trades only — consensus-driven.
    """

    def __init__(self, capital: float = None):
        self.capital = capital or CAPITAL
        self.available_cash = self.capital
        self.positions = []
        self.closed_trades = []
        self.pnl = 0.0
        self.max_positions = int(os.environ.get("MAX_POSITIONS", 5))
        self.max_risk_per_trade_pct = float(os.environ.get("MAX_RISK_PCT", 2.0))
        self.target_multiplier = 2.5  # Risk:Reward = 1:2.5
        self.state_file = Path("reports/portfolio_state.json")

        # Load existing state if available
        self._load_state()

    # ------------------------------------------------------------------
    # Trade management
    # ------------------------------------------------------------------

    def can_trade(self) -> bool:
        """Check if we can take a new position."""
        return (
            len(self.positions) < self.max_positions
            and self.available_cash >= 10000  # minimum ₹10K per trade
        )

    def open_position(self, stock: str, price: float, quantity: int,
                      stop_loss: float, target: float,
                      reason: str = "", signal_score: int = 0) -> dict:
        """Open a new position."""
        if not self.can_trade():
            return {"status": "REJECTED", "reason": "Max positions or no cash"}

        cost = price * quantity
        if cost > self.available_cash:
            # Adjust quantity to fit available cash
            quantity = int(self.available_cash / price)
            if quantity <= 0:
                return {"status": "REJECTED", "reason": "Insufficient funds"}
            cost = price * quantity

        position = {
            "stock":        stock,
            "entry_price":  round(price, 2),
            "quantity":     quantity,
            "cost":         round(cost, 2),
            "stop_loss":    round(stop_loss, 2),
            "target":       round(target, 2),
            "reason":       reason,
            "signal_score": signal_score,
            "entry_date":   datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M"),
            "status":       "OPEN",
            "current_pnl":  0,
        }

        self.positions.append(position)
        self.available_cash -= cost
        self._save_state()

        logger.info(f"OPENED: {stock} × {quantity} @ ₹{price} | SL: ₹{stop_loss} | TGT: ₹{target}")
        return {"status": "OPENED", "position": position}

    def close_position(self, stock: str, exit_price: float, reason: str = "TARGET") -> dict:
        """Close an existing position."""
        for i, pos in enumerate(self.positions):
            if pos["stock"] == stock:
                pnl = (exit_price - pos["entry_price"]) * pos["quantity"]
                pnl_pct = ((exit_price - pos["entry_price"]) / pos["entry_price"]) * 100

                closed = {
                    **pos,
                    "exit_price":  round(exit_price, 2),
                    "exit_date":   datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M"),
                    "pnl":         round(pnl, 2),
                    "pnl_pct":     round(pnl_pct, 2),
                    "exit_reason": reason,
                    "status":      "CLOSED",
                }

                self.closed_trades.append(closed)
                self.pnl += pnl
                self.available_cash += (pos["cost"] + pnl)
                self.capital += pnl  # update capital
                self.positions.pop(i)
                self._save_state()

                icon = "✅" if pnl > 0 else "❌"
                logger.info(f"{icon} CLOSED: {stock} @ ₹{exit_price} | PnL: ₹{pnl:.0f} ({pnl_pct:+.1f}%) | {reason}")
                return {"status": "CLOSED", "trade": closed}

        return {"status": "NOT_FOUND", "reason": f"No open position for {stock}"}

    def check_stop_losses(self, current_prices: dict) -> list:
        """Check if any position hit stop-loss or target."""
        actions = []
        for pos in self.positions[:]:
            stock = pos["stock"]
            if stock not in current_prices:
                continue

            price = current_prices[stock]
            if price <= pos["stop_loss"]:
                result = self.close_position(stock, price, "STOP_LOSS_HIT")
                actions.append(result)
            elif price >= pos["target"]:
                result = self.close_position(stock, price, "TARGET_HIT")
                actions.append(result)

        return actions

    # ------------------------------------------------------------------
    # Position sizing for ₹10L capital
    # ------------------------------------------------------------------

    def calculate_aggressive_position(self, stock: str, price: float,
                                       stop_loss: float) -> dict:
        """
        Calculate position size based on risk management.
        Allocates max 20% of capital per position (5 positions max).
        """
        allocation = min(self.available_cash * 0.50, self.capital * 0.20)  # max 20% of total capital
        quantity = int(allocation / price)

        if quantity <= 0:
            return {"approved": False, "reason": "Price too high for allocation"}

        cost = quantity * price
        risk_per_share = price - stop_loss
        total_risk = risk_per_share * quantity
        risk_pct = (total_risk / self.capital) * 100

        # Don't risk more than 3% of total capital
        if risk_pct > self.max_risk_per_trade_pct:
            quantity = int((self.capital * self.max_risk_per_trade_pct / 100) / risk_per_share)
            if quantity <= 0:
                return {"approved": False, "reason": "Risk too high"}
            cost = quantity * price
            total_risk = risk_per_share * quantity
            risk_pct = (total_risk / self.capital) * 100

        target = price + (risk_per_share * self.target_multiplier)
        reward = (target - price) * quantity

        return {
            "approved":    True,
            "stock":       stock,
            "price":       round(price, 2),
            "quantity":    quantity,
            "cost":        round(cost, 2),
            "stop_loss":   round(stop_loss, 2),
            "target":      round(target, 2),
            "risk":        round(total_risk, 2),
            "risk_pct":    round(risk_pct, 2),
            "reward":      round(reward, 2),
            "risk_reward": round(reward / total_risk if total_risk else 0, 1),
        }

    # ------------------------------------------------------------------
    # Performance tracking
    # ------------------------------------------------------------------

    def get_performance(self) -> dict:
        """Get portfolio performance summary."""
        total_trades = len(self.closed_trades)
        winners = [t for t in self.closed_trades if t["pnl"] > 0]
        losers = [t for t in self.closed_trades if t["pnl"] <= 0]
        win_rate = len(winners) / total_trades * 100 if total_trades else 0

        total_pnl = sum(t["pnl"] for t in self.closed_trades)
        avg_win = sum(t["pnl"] for t in winners) / len(winners) if winners else 0
        avg_loss = sum(t["pnl"] for t in losers) / len(losers) if losers else 0

        return {
            "initial_capital":  CAPITAL,
            "current_capital":  round(self.capital, 2),
            "available_cash":   round(self.available_cash, 2),
            "total_pnl":        round(total_pnl, 2),
            "pnl_pct":          round(total_pnl / CAPITAL * 100, 2),
            "total_trades":     total_trades,
            "winners":          len(winners),
            "losers":           len(losers),
            "win_rate":         round(win_rate, 1),
            "avg_win":          round(avg_win, 2),
            "avg_loss":         round(avg_loss, 2),
            "open_positions":   len(self.positions),
            "positions":        self.positions,
            "best_trade":       max(self.closed_trades, key=lambda x: x["pnl"])["stock"] if self.closed_trades else None,
            "worst_trade":      min(self.closed_trades, key=lambda x: x["pnl"])["stock"] if self.closed_trades else None,
        }

    def print_status(self):
        """Print current portfolio status."""
        perf = self.get_performance()
        ist = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %H:%M IST")
        print(f"\n{'='*55}")
        print(f"  💼 PORTFOLIO STATUS — Mudholkars and Co")
        print(f"  {ist}")
        print(f"{'='*55}")
        print(f"  Capital:     ₹{perf['current_capital']:,.2f} (started ₹{CAPITAL:,.0f})")
        print(f"  Cash Free:   ₹{perf['available_cash']:,.2f}")
        print(f"  Total P&L:   ₹{perf['total_pnl']:+,.2f} ({perf['pnl_pct']:+.1f}%)")
        print(f"  Trades:      {perf['total_trades']} total | Win: {perf['win_rate']:.0f}%")
        print(f"  Open:        {perf['open_positions']} positions")

        if self.positions:
            print(f"\n  OPEN POSITIONS:")
            for p in self.positions:
                print(f"    {p['stock']:12s} {p['quantity']}×₹{p['entry_price']}  "
                      f"SL=₹{p['stop_loss']} TGT=₹{p['target']}")

        print(f"{'='*55}")

    # ------------------------------------------------------------------
    # State persistence
    # ------------------------------------------------------------------

    def _save_state(self):
        self.state_file.parent.mkdir(exist_ok=True)
        state = {
            "capital": self.capital,
            "available_cash": self.available_cash,
            "positions": self.positions,
            "closed_trades": self.closed_trades,
            "pnl": self.pnl,
            "updated": datetime.utcnow().isoformat() + "Z",
        }
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=2)

    def _load_state(self):
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
                self.capital = state.get("capital", self.capital)
                self.available_cash = state.get("available_cash", self.available_cash)
                self.positions = state.get("positions", [])
                self.closed_trades = state.get("closed_trades", [])
                self.pnl = state.get("pnl", 0)
                logger.info(f"Loaded portfolio state: ₹{self.capital} capital, {len(self.positions)} open")
            except:
                pass
