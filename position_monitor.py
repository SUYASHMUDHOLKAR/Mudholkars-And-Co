"""
position_monitor.py
-------------------
Mudholkars and Co — POSITION EXIT MONITOR

Checks open positions every 15 minutes during market hours.
Sends EXIT alert via Telegram if:
  - Stop-loss hit
  - Target hit
  - Trailing stop triggered (after +3% profit, trail SL at -2%)

Runs inside the GitHub Actions cron OR locally.

Usage:
  python position_monitor.py          # check once
  python position_monitor.py --loop   # run every 15 min during market hours
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

import yfinance as yf

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
os.chdir(str(BASE))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("PositionMonitor")

IST = ZoneInfo("Asia/Kolkata")
STATE_FILE = BASE / "reports" / "portfolio_state.json"

# Trailing stop params
TRAIL_ACTIVATE_PCT = 3.0   # start trailing after +3% profit
TRAIL_DISTANCE_PCT = 2.0   # trail 2% below highest price


def _load_positions() -> list:
    """Load open positions from portfolio state."""
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
            return data.get("positions", [])
    except Exception as e:
        logger.error(f"Failed to load positions: {e}")
    return []


def _save_positions(positions: list):
    """Update portfolio state with modified positions."""
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text())
        else:
            data = {}
        data["positions"] = positions
        data["last_monitor_check"] = datetime.now(IST).isoformat()
        STATE_FILE.write_text(json.dumps(data, indent=2, default=str))
    except Exception as e:
        logger.error(f"Failed to save positions: {e}")


def _get_current_price(symbol: str) -> float:
    """Get current market price for a stock."""
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        info = ticker.fast_info
        price = info.get("lastPrice", 0) or info.get("last_price", 0)
        if not price:
            # Fallback: last close
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
        return float(price) if price else 0
    except Exception as e:
        logger.warning(f"  Price fetch failed for {symbol}: {e}")
        return 0


def _send_telegram(msg: str) -> bool:
    """Send alert via standardized alerts."""
    try:
        from standardized_alerts import send_exit_signal, _send
        return _send(msg)
    except Exception:
        try:
            import requests
            token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
            chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
            if token and chat_id:
                requests.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
                    timeout=10
                )
                return True
        except Exception:
            pass
    return False


def check_positions() -> list:
    """
    Check all open positions against current prices.
    Uses TrailingStopV2 for smart partial profit booking.
    Returns list of actions taken.
    """
    positions = _load_positions()
    if not positions:
        logger.info("  No open positions to monitor.")
        return []

    # Import trailing stop v2
    try:
        from trailing_stop_v2 import TrailingStopV2
        use_v2 = True
    except ImportError:
        use_v2 = False

    actions = []
    modified = False

    for pos in positions[:]:
        stock = pos.get("stock", "")
        entry = pos.get("entry_price", 0)
        sl = pos.get("stop_loss", 0)
        target = pos.get("target", 0)
        qty = pos.get("quantity", 0)
        trailing_high = pos.get("trailing_high", entry)

        if not stock or not entry:
            continue

        price = _get_current_price(stock)
        if price <= 0:
            logger.warning(f"  ⚠️ Could not get price for {stock}")
            continue

        pnl_pct = (price - entry) / entry * 100
        pnl_abs = (price - entry) * qty

        logger.info(f"  {stock}: ₹{price:.2f} (entry ₹{entry:.2f}) | "
                    f"P&L: {pnl_pct:+.1f}% (₹{pnl_abs:+,.0f}) | "
                    f"SL: ₹{sl:.2f} | TGT: ₹{target:.2f}")

        # ── TrailingStopV2: Smart partial profit booking ──
        if use_v2:
            stage = pos.get("trailing_stage", 0)
            ts = TrailingStopV2(entry, qty, sl, target)
            ts.stage = stage
            ts.highest_price = trailing_high
            ts.shares_remaining = pos.get("shares_remaining", qty)
            ts.partial_booked = pos.get("partial_booked", False)

            result = ts.check(price)
            action_type = result.get("action", "HOLD")

            if action_type == "SELL_HALF":
                sell_qty = result.get("sell_qty", qty // 2)
                pos["shares_remaining"] = qty - sell_qty
                pos["partial_booked"] = True
                pos["stop_loss"] = entry  # move to breakeven
                pos["trailing_stage"] = 1
                modified = True
                logger.info(f"    📈 PARTIAL PROFIT: Sell {sell_qty} @ ₹{price:.2f} (+5%)")

                msg = (f"📈 <b>PARTIAL PROFIT — {stock}</b>\n"
                       f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                       f"💰 Selling {sell_qty} shares @ ₹{price:.2f}\n"
                       f"📊 Profit: +5% on half position\n"
                       f"🛡️ SL moved to breakeven (₹{entry:.2f})\n"
                       f"📌 Remaining {pos['shares_remaining']} shares trailing...\n\n"
                       f"⏰ {datetime.now(IST).strftime('%H:%M IST')}")
                _send_telegram(msg)

                actions.append({"stock": stock, "action": "SELL_HALF", "price": price,
                               "qty_sold": sell_qty, "pnl_pct": 5.0})
                continue  # don't check old SL/target

            elif action_type == "TRAIL":
                new_sl = result.get("new_sl", sl)
                if new_sl > pos["stop_loss"]:
                    pos["stop_loss"] = round(new_sl, 2)
                    pos["trailing_stage"] = 2
                    modified = True
                    logger.info(f"    📈 Trailing SL raised to ₹{new_sl:.2f}")

            elif action_type == "SELL_ALL":
                # Full target hit on remaining shares
                pos["trailing_stage"] = 3
                # Fall through to target hit logic below

            # Update state
            pos["trailing_stage"] = ts.stage if ts.stage > pos.get("trailing_stage", 0) else pos.get("trailing_stage", 0)

        # Update trailing high
        if price > trailing_high:
            pos["trailing_high"] = price
            trailing_high = price
            modified = True

        # Calculate trailing stop (activates after TRAIL_ACTIVATE_PCT profit)
        trailing_sl = sl  # default to original SL
        if pnl_pct >= TRAIL_ACTIVATE_PCT:
            trailing_sl = trailing_high * (1 - TRAIL_DISTANCE_PCT / 100)
            if trailing_sl > sl:
                pos["stop_loss"] = round(trailing_sl, 2)
                sl = trailing_sl
                modified = True
                logger.info(f"    📈 Trailing SL updated: ₹{sl:.2f}")

        # ── CHECK: STOP-LOSS HIT ──
        if price <= sl:
            action = {
                "stock": stock,
                "action": "EXIT",
                "reason": "STOP_LOSS_HIT",
                "price": price,
                "entry": entry,
                "pnl": round(pnl_abs, 2),
                "pnl_pct": round(pnl_pct, 1),
            }
            actions.append(action)

            # Send Telegram alert
            msg = (f"🛑 <b>STOP-LOSS HIT — {stock}</b>\n"
                   f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                   f"📤 Current Price: ₹{price:.2f}\n"
                   f"📥 Entry was: ₹{entry:.2f}\n"
                   f"📊 P&L: <b>₹{pnl_abs:+,.0f} ({pnl_pct:+.1f}%)</b>\n\n"
                   f"<b>📋 ACTION:</b>\n"
                   f"  GTT should auto-sell. Check Groww NOW.\n"
                   f"  If not sold, SELL MARKET immediately.\n\n"
                   f"⏰ {datetime.now(IST).strftime('%H:%M IST')}")
            _send_telegram(msg)
            logger.info(f"  🛑 {stock}: SL HIT at ₹{price:.2f} | P&L: ₹{pnl_abs:+,.0f}")

            # Mark position for removal
            pos["status"] = "EXIT_SL"
            modified = True

        # ── CHECK: TARGET HIT ──
        elif price >= target:
            action = {
                "stock": stock,
                "action": "EXIT",
                "reason": "TARGET_HIT",
                "price": price,
                "entry": entry,
                "pnl": round(pnl_abs, 2),
                "pnl_pct": round(pnl_pct, 1),
            }
            actions.append(action)

            # Send Telegram alert
            msg = (f"✅ <b>TARGET HIT — {stock}</b> 🎯\n"
                   f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                   f"📤 Current Price: ₹{price:.2f}\n"
                   f"📥 Entry was: ₹{entry:.2f}\n"
                   f"📊 P&L: <b>₹{pnl_abs:+,.0f} ({pnl_pct:+.1f}%)</b>\n\n"
                   f"<b>📋 ACTION:</b>\n"
                   f"  GTT should auto-sell. Check Groww.\n"
                   f"  Book profits! Well done. 🎉\n\n"
                   f"⏰ {datetime.now(IST).strftime('%H:%M IST')}")
            _send_telegram(msg)
            logger.info(f"  🎯 {stock}: TARGET HIT at ₹{price:.2f} | P&L: ₹{pnl_abs:+,.0f}")

            # Mark position for removal
            pos["status"] = "EXIT_TARGET"
            modified = True

    # Update state
    if modified:
        # Remove exited positions
        active = [p for p in positions if p.get("status") not in ("EXIT_SL", "EXIT_TARGET")]
        exited = [p for p in positions if p.get("status") in ("EXIT_SL", "EXIT_TARGET")]
        _save_positions(active)

        # Log exits to closed_trades
        if exited:
            try:
                data = json.loads(STATE_FILE.read_text())
                closed = data.get("closed_trades", [])
                for p in exited:
                    closed.append({
                        **p,
                        "exit_date": datetime.now(IST).strftime("%Y-%m-%d %H:%M"),
                        "exit_reason": p.get("status", "UNKNOWN"),
                    })
                data["closed_trades"] = closed
                STATE_FILE.write_text(json.dumps(data, indent=2, default=str))
            except Exception:
                pass

    if not actions:
        logger.info("  ✅ All positions within range. No exits needed.")

    return actions


def is_market_hours() -> bool:
    """Check if Indian market is currently open."""
    now = datetime.now(IST)
    if now.weekday() >= 5:  # Weekend
        return False
    hour_min = now.hour * 100 + now.minute
    return 915 <= hour_min <= 1530


def run_loop():
    """Run position monitor every 15 minutes during market hours."""
    logger.info("🔄 Position Monitor started in loop mode")
    while True:
        if is_market_hours():
            logger.info(f"\n⏰ {datetime.now(IST).strftime('%H:%M IST')} — Checking positions...")
            check_positions()
            time.sleep(900)  # 15 minutes
        else:
            logger.info(f"  Market closed. Sleeping 30 min...")
            time.sleep(1800)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true", help="Run every 15 min")
    args = parser.parse_args()

    if args.loop:
        run_loop()
    else:
        logger.info("🔍 Position Monitor — Single check")
        actions = check_positions()
        if actions:
            print(f"\n⚡ {len(actions)} EXIT actions triggered!")
            for a in actions:
                print(f"  {a['stock']}: {a['reason']} | P&L: ₹{a['pnl']:+,.0f} ({a['pnl_pct']:+.1f}%)")
