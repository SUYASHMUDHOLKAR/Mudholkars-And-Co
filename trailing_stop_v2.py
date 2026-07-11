"""
trailing_stop_v2.py
-------------------
Advanced trailing stop with partial profit booking logic.

Implements a 3-stage exit strategy:
    Stage 1: +5%  → Sell half, move SL to breakeven
    Stage 2: +10% → Trail stop 3% below highest price
    Stage 3: Target hit → Sell all remaining

Usage:
    from trailing_stop_v2 import TrailingStopV2, calculate_exits
    
    ts = TrailingStopV2(entry_price=100, quantity=100, stop_loss=95, target=120)
    action = ts.check(current_price=106)
    # action = {"action": "SELL_HALF", "sell_qty": 50, "new_sl": 100, ...}
"""

import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class TrailingStopV2:
    """
    Trailing stop with partial profit booking across 3 stages.

    Stages:
        0 - Initial: holding full position, static stop loss
        1 - +5% hit: sold half, SL moved to breakeven
        2 - +10% hit: trailing stop at 3% below highest price
        3 - Target hit: sell all remaining

    Attributes:
        entry_price (float): Original entry price.
        quantity (int): Original total quantity.
        stop_loss (float): Current stop loss level.
        target (float): Final target price.
        stage (int): Current stage (0, 1, 2, 3).
        highest_price (float): Highest price seen since entry.
        shares_remaining (int): Number of shares still held.
        partial_booked (bool): Whether partial profit has been booked.
    """

    def __init__(self, entry_price: float, quantity: int, stop_loss: float, target: float):
        """
        Initialize the trailing stop manager.

        Args:
            entry_price: Price at which the position was entered.
            quantity: Total number of shares/units bought.
            stop_loss: Initial stop loss price.
            target: Target price for full exit.
        """
        self.entry_price = entry_price
        self.quantity = quantity
        self.stop_loss = stop_loss
        self.target = target

        # State tracking
        self.stage = 0
        self.highest_price = entry_price
        self.shares_remaining = quantity
        self.partial_booked = False

        logger.info(
            f"TrailingStopV2 initialized: entry={entry_price}, qty={quantity}, "
            f"sl={stop_loss}, target={target}"
        )

    def check(self, current_price: float) -> dict:
        """
        Check current price against exit levels and return action to take.

        Args:
            current_price: The current market price.

        Returns:
            dict with keys:
                - action: str — "SELL_HALF", "TRAIL", "SELL_ALL", "EXIT", or "HOLD"
                - sell_qty: int (if selling)
                - new_sl: float (if stop loss changes)
                - reason: str (explanation of the action)
        """
        try:
            # Update highest price tracking
            if current_price > self.highest_price:
                self.highest_price = current_price

            # Stage 3: Full target hit → Sell all
            if current_price >= self.target and self.shares_remaining > 0:
                self.stage = 3
                result = {
                    "action": "SELL_ALL",
                    "sell_qty": self.shares_remaining,
                    "reason": f"Full target hit at {current_price:.2f} (target={self.target:.2f})"
                }
                logger.info(f"SELL_ALL triggered: {result['reason']}")
                self.shares_remaining = 0
                return result

            # SL hit: Exit all remaining
            if current_price <= self.stop_loss and self.shares_remaining > 0:
                result = {
                    "action": "EXIT",
                    "sell_qty": self.shares_remaining,
                    "reason": f"Stop loss hit at {current_price:.2f} (sl={self.stop_loss:.2f})"
                }
                logger.info(f"EXIT triggered: {result['reason']}")
                self.shares_remaining = 0
                return result

            # Stage 2: +10% → Trail stop
            stage2_trigger = self.entry_price * 1.10
            if current_price >= stage2_trigger and self.stage < 2:
                self.stage = 2
                new_sl = self.highest_price * 0.97  # Trail 3% below high
                self.stop_loss = new_sl
                result = {
                    "action": "TRAIL",
                    "new_sl": round(new_sl, 2),
                    "reason": f"Trailing at +10%: new SL={new_sl:.2f} (3% below high of {self.highest_price:.2f})"
                }
                logger.info(f"TRAIL triggered: {result['reason']}")
                return result

            # If already in stage 2, keep updating trail
            if self.stage == 2:
                new_sl = self.highest_price * 0.97
                if new_sl > self.stop_loss:
                    self.stop_loss = new_sl
                    result = {
                        "action": "TRAIL",
                        "new_sl": round(new_sl, 2),
                        "reason": f"Trail updated: new SL={new_sl:.2f} (3% below high of {self.highest_price:.2f})"
                    }
                    logger.info(f"TRAIL updated: {result['reason']}")
                    return result

            # Stage 1: +5% → Sell half
            stage1_trigger = self.entry_price * 1.05
            if current_price >= stage1_trigger and self.stage < 1 and not self.partial_booked:
                self.stage = 1
                self.partial_booked = True
                sell_qty = self.quantity // 2
                self.shares_remaining -= sell_qty
                self.stop_loss = self.entry_price  # Move to breakeven
                result = {
                    "action": "SELL_HALF",
                    "sell_qty": sell_qty,
                    "new_sl": self.entry_price,
                    "reason": f"Partial profit at +5%: selling {sell_qty} shares, SL moved to breakeven ({self.entry_price:.2f})"
                }
                logger.info(f"SELL_HALF triggered: {result['reason']}")
                return result

            # No action needed
            return {
                "action": "HOLD",
                "reason": f"Holding: price={current_price:.2f}, stage={self.stage}, sl={self.stop_loss:.2f}, highest={self.highest_price:.2f}"
            }

        except Exception as e:
            logger.error(f"Error in TrailingStopV2.check: {e}")
            return {
                "action": "HOLD",
                "reason": f"Error occurred: {e}. Holding position."
            }

    def get_state(self) -> dict:
        """
        Get the current state of the trailing stop manager.

        Returns:
            dict with current state information.
        """
        return {
            "entry_price": self.entry_price,
            "quantity": self.quantity,
            "stop_loss": self.stop_loss,
            "target": self.target,
            "stage": self.stage,
            "highest_price": self.highest_price,
            "shares_remaining": self.shares_remaining,
            "partial_booked": self.partial_booked,
            "unrealized_pnl_pct": round(
                ((self.highest_price - self.entry_price) / self.entry_price) * 100, 2
            )
        }


def calculate_exits(entry: float, qty: int, sl: float, target: float) -> dict:
    """
    Pre-calculate all exit levels for a given trade setup.

    This function computes the price levels and quantities for each stage
    without needing live price data.

    Args:
        entry: Entry price.
        qty: Total quantity.
        sl: Initial stop loss price.
        target: Target price.

    Returns:
        dict with pre-calculated exit levels:
            - initial_sl: Initial stop loss
            - stage1_trigger: Price at +5%
            - stage1_sell_qty: Quantity to sell at stage 1
            - stage1_new_sl: New SL after stage 1 (breakeven)
            - stage2_trigger: Price at +10%
            - stage2_trail_pct: Trail percentage (3%)
            - stage3_trigger: Target price
            - stage3_sell_qty: Remaining quantity to sell at target
            - risk_reward: Risk/reward ratio
            - max_loss: Maximum loss in absolute terms
            - stage1_profit: Profit from partial booking
            - full_target_profit: Profit if full target hit (no partial)
    """
    try:
        stage1_trigger = entry * 1.05
        stage2_trigger = entry * 1.10
        stage1_sell_qty = qty // 2
        remaining_after_partial = qty - stage1_sell_qty

        # Calculate profits
        max_loss = (entry - sl) * qty
        stage1_profit = (stage1_trigger - entry) * stage1_sell_qty
        full_target_profit = (target - entry) * qty

        # Blended profit if partial at stage1 + remaining at target
        blended_profit = stage1_profit + ((target - entry) * remaining_after_partial)

        # Risk/reward ratio
        risk = entry - sl
        reward = target - entry
        risk_reward = round(reward / risk, 2) if risk > 0 else float('inf')

        return {
            "initial_sl": sl,
            "stage1_trigger": round(stage1_trigger, 2),
            "stage1_sell_qty": stage1_sell_qty,
            "stage1_new_sl": entry,
            "stage2_trigger": round(stage2_trigger, 2),
            "stage2_trail_pct": 3.0,
            "stage3_trigger": target,
            "stage3_sell_qty": remaining_after_partial,
            "risk_reward": risk_reward,
            "max_loss": round(max_loss, 2),
            "stage1_profit": round(stage1_profit, 2),
            "full_target_profit": round(full_target_profit, 2),
            "blended_profit": round(blended_profit, 2),
            "summary": (
                f"Entry: {entry} | SL: {sl} | Target: {target} | "
                f"R:R = 1:{risk_reward} | "
                f"Stage1 @{stage1_trigger:.2f} sell {stage1_sell_qty} | "
                f"Stage2 @{stage2_trigger:.2f} trail 3% | "
                f"Stage3 @{target} sell remaining {remaining_after_partial}"
            )
        }

    except Exception as e:
        logger.error(f"Error calculating exits: {e}")
        return {
            "error": str(e),
            "initial_sl": sl,
            "stage1_trigger": entry * 1.05,
            "stage2_trigger": entry * 1.10,
            "stage3_trigger": target
        }


if __name__ == "__main__":
    # Example usage
    print("=" * 60)
    print("TrailingStopV2 Demo")
    print("=" * 60)

    # Pre-calculate exits
    exits = calculate_exits(entry=100, qty=100, sl=95, target=120)
    print("\nPre-calculated exit levels:")
    for k, v in exits.items():
        print(f"  {k}: {v}")

    # Simulate price movement
    ts = TrailingStopV2(entry_price=100, quantity=100, stop_loss=95, target=120)

    prices = [99, 101, 103, 105, 106, 108, 110, 112, 115, 118, 120]
    print("\nSimulating price movement:")
    print("-" * 60)

    for price in prices:
        result = ts.check(price)
        if result["action"] != "HOLD":
            print(f"  Price={price:>6.2f} → {result['action']}: {result['reason']}")
        else:
            print(f"  Price={price:>6.2f} → HOLD (stage={ts.stage}, sl={ts.stop_loss:.2f})")

    print(f"\nFinal state: {ts.get_state()}")
