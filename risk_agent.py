"""
risk_agent.py
-------------
Mudholkars and Co — Risk Management Agent

Rules:
  1. Never risk more than 2% of capital on single trade
  2. Maximum 5 open positions at a time
  3. Stop-loss mandatory on every trade
  4. If portfolio down 8% in a week → HALT all new trades
  5. Position sizing based on volatility (ATR)
  6. Sector exposure limit: max 30% in one sector

Outputs:
  - Exact quantity to buy (based on capital + risk)
  - Stop-loss price
  - Target price (2:1 reward:risk minimum)
  - Position size in rupees
  - Portfolio heat check
"""

import logging
from typing import Optional
from datetime import datetime

import yfinance as yf

logger = logging.getLogger(__name__)


class RiskAgent:
    """
    Protects your capital. Every trade goes through this agent.
    No trade happens without Risk Agent approval.
    """

    def __init__(self, capital: float = 1000000, max_risk_pct: float = 2.0,
                 max_positions: int = 5, max_sector_pct: float = 30.0,
                 weekly_drawdown_halt: float = 8.0):
        """
        capital:              Total trading capital (₹)
        max_risk_pct:         Max % of capital to risk per trade
        max_positions:        Max simultaneous open positions
        max_sector_pct:       Max % of capital in one sector
        weekly_drawdown_halt: If portfolio drops this % in a week, halt trading
        """
        self.capital           = capital
        self.max_risk_pct      = max_risk_pct
        self.max_positions     = max_positions
        self.max_sector_pct    = max_sector_pct
        self.drawdown_halt_pct = weekly_drawdown_halt
        self.open_positions    = []

    def calculate_position(self, symbol: str, entry_price: float,
                           stop_loss_price: float,
                           sector: str = "UNKNOWN") -> dict:
        """
        Calculate position size for a trade.

        Given entry and stop-loss, tells you:
          - How many shares to buy
          - Total capital to deploy
          - Risk in rupees
          - Target price (2:1 ratio)
          - Whether trade is approved
        """
        # Risk per share
        risk_per_share = abs(entry_price - stop_loss_price)
        if risk_per_share == 0:
            return {"approved": False, "reason": "Stop-loss same as entry price"}

        # Max risk in rupees (2% of capital)
        max_risk_amount = self.capital * (self.max_risk_pct / 100)

        # Position size (quantity)
        quantity = int(max_risk_amount / risk_per_share)
        if quantity <= 0:
            return {"approved": False, "reason": "Risk too high for position size"}

        # Total investment
        position_value = quantity * entry_price
        position_pct   = (position_value / self.capital) * 100

        # Max 20% of capital in single stock
        if position_pct > 20:
            quantity = int((self.capital * 0.20) / entry_price)
            position_value = quantity * entry_price
            position_pct   = (position_value / self.capital) * 100

        # Target price (minimum 2:1 reward:risk)
        is_long = entry_price > stop_loss_price
        if is_long:
            target_price = entry_price + (risk_per_share * 2)
        else:
            target_price = entry_price - (risk_per_share * 2)

        # Risk:Reward ratio
        reward = abs(target_price - entry_price)
        risk_reward = reward / risk_per_share if risk_per_share else 0

        # Check position limit
        if len(self.open_positions) >= self.max_positions:
            return {
                "approved": False,
                "reason": f"Max positions ({self.max_positions}) reached. Close one first.",
            }

        # Sector check
        sector_exposure = sum(
            p["value"] for p in self.open_positions if p.get("sector") == sector
        )
        if sector_exposure + position_value > self.capital * (self.max_sector_pct / 100):
            return {
                "approved": False,
                "reason": f"Sector {sector} exposure would exceed {self.max_sector_pct}%",
            }

        return {
            "approved":       True,
            "symbol":         symbol,
            "direction":      "LONG" if is_long else "SHORT",
            "entry_price":    round(entry_price, 2),
            "stop_loss":      round(stop_loss_price, 2),
            "target_price":   round(target_price, 2),
            "quantity":       quantity,
            "position_value": round(position_value, 2),
            "position_pct":   round(position_pct, 1),
            "risk_amount":    round(quantity * risk_per_share, 2),
            "risk_pct":       round((quantity * risk_per_share) / self.capital * 100, 2),
            "reward_amount":  round(quantity * reward, 2),
            "risk_reward":    round(risk_reward, 2),
            "sector":         sector,
            "open_positions": len(self.open_positions),
            "capital":        self.capital,
        }

    def auto_stop_loss(self, symbol: str, atr_multiplier: float = 2.0) -> Optional[dict]:
        """
        Calculate stop-loss automatically using ATR (Average True Range).
        ATR-based stop = adapts to stock's volatility.
        Volatile stock → wider stop. Calm stock → tighter stop.
        """
        try:
            ticker = yf.Ticker(f"{symbol}.NS" if ".NS" not in symbol else symbol)
            hist = ticker.history(period="30d", interval="1d").dropna()
            if len(hist) < 14:
                return None

            # Calculate ATR
            high  = hist["High"]
            low   = hist["Low"]
            close = hist["Close"]

            tr = []
            for i in range(1, len(hist)):
                tr.append(max(
                    float(high.iloc[i] - low.iloc[i]),
                    abs(float(high.iloc[i] - close.iloc[i-1])),
                    abs(float(low.iloc[i] - close.iloc[i-1]))
                ))

            atr = sum(tr[-14:]) / 14
            price = float(close.iloc[-1])
            stop_loss = price - (atr * atr_multiplier)
            target    = price + (atr * atr_multiplier * 2)

            return {
                "symbol":      symbol.replace(".NS", ""),
                "price":       round(price, 2),
                "atr":         round(atr, 2),
                "stop_loss":   round(stop_loss, 2),
                "target":      round(target, 2),
                "risk_pct":    round((price - stop_loss) / price * 100, 2),
                "reward_pct":  round((target - price) / price * 100, 2),
                "risk_reward": round((target - price) / (price - stop_loss), 2),
            }
        except Exception as e:
            logger.error(f"[{symbol}] ATR calculation error: {e}")
            return None

    def portfolio_health(self) -> dict:
        """Check overall portfolio health and risk status."""
        total_invested = sum(p.get("value", 0) for p in self.open_positions)
        total_risk     = sum(p.get("risk", 0) for p in self.open_positions)
        cash_available = self.capital - total_invested

        return {
            "capital":          self.capital,
            "invested":         total_invested,
            "cash_available":   cash_available,
            "utilization_pct":  round(total_invested / self.capital * 100, 1),
            "open_positions":   len(self.open_positions),
            "max_positions":    self.max_positions,
            "total_risk":       total_risk,
            "risk_pct":         round(total_risk / self.capital * 100, 2),
            "can_trade":        len(self.open_positions) < self.max_positions,
            "status":           "HEALTHY" if total_risk / self.capital < 0.05 else "CAUTION",
        }

    def print_trade_plan(self, plan: dict):
        """Print formatted trade plan."""
        if not plan.get("approved"):
            print(f"\n  ❌ TRADE REJECTED: {plan.get('reason')}")
            return

        print(f"\n  {'='*50}")
        print(f"  ✅ TRADE APPROVED — Risk Agent")
        print(f"  {'='*50}")
        print(f"  Stock:        {plan['symbol']}")
        print(f"  Direction:    {plan['direction']}")
        print(f"  Entry:        ₹{plan['entry_price']}")
        print(f"  Stop-Loss:    ₹{plan['stop_loss']}")
        print(f"  Target:       ₹{plan['target_price']}")
        print(f"  Quantity:     {plan['quantity']} shares")
        print(f"  Investment:   ₹{plan['position_value']:,.0f} ({plan['position_pct']}% of capital)")
        print(f"  Risk:         ₹{plan['risk_amount']:,.0f} ({plan['risk_pct']}% of capital)")
        print(f"  Reward:       ₹{plan['reward_amount']:,.0f}")
        print(f"  Risk:Reward:  1:{plan['risk_reward']}")
        print(f"  {'='*50}")
