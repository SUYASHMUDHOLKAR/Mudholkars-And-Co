"""
standardized_alerts.py
----------------------
Mudholkars and Co — STANDARDIZED TELEGRAM ALERTS

ONE consistent format. No confusion. Every message is actionable.

Message Types (you'll receive ONLY these 5 types):
  1. MORNING BRIEF     — 9:30 AM daily (what to expect today)
  2. BUY SIGNAL        — when to buy (exact entry, target, SL)
  3. EXIT SIGNAL       — when to sell (hit target or SL)
  4. PORTFOLIO UPDATE  — end of day P&L
  5. WEEKLY REPORT     — Sunday strategy for next week

That's it. No noise. Only actionable.
"""

import requests
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TOKEN = "8979796737:AAGhw3n5YyO556A-rw60Oxbm7eJNWAF6pGo"
CHAT_ID = "6621137200"
IST = ZoneInfo("Asia/Kolkata")


def _send(msg: str) -> bool:
    try:
        r = requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                         json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
                         timeout=10)
        return r.status_code == 200
    except:
        return False


def _time():
    return datetime.now(IST).strftime("%H:%M")


# ═══════════════════════════════════════════════════════════════
# TYPE 1: MORNING BRIEF (9:30 AM daily)
# ═══════════════════════════════════════════════════════════════

def send_morning_brief(market_bias: str, fii_signal: str,
                       top_picks: list, avoid: list,
                       open_positions: list):
    """
    Sent once at 9:30 AM. Tells you what to expect today.
    """
    msg = f"☀️ <b>MORNING BRIEF</b> | {_time()}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"📊 Market: <b>{market_bias}</b>\n"
    msg += f"🏦 FII: {fii_signal}\n\n"

    if open_positions:
        msg += "<b>📌 YOUR POSITIONS:</b>\n"
        for p in open_positions:
            msg += f"  • {p['stock']} @ ₹{p['entry']:.0f} → TGT ₹{p['target']:.0f}\n"
        msg += "\n"

    if top_picks:
        msg += "<b>🎯 TODAY'S WATCHLIST:</b>\n"
        for i, p in enumerate(top_picks[:5], 1):
            msg += f"  {i}. {p['stock']} (Score {p['score']}) — ₹{p['price']:.0f}\n"
        msg += "\n"

    if avoid:
        msg += f"🔴 Avoid: {', '.join(avoid[:5])}\n\n"

    msg += "⏳ Waiting for live confirmation before BUY signal..."
    return _send(msg)


# ═══════════════════════════════════════════════════════════════
# TYPE 2: BUY SIGNAL (only when agents confirm — actionable!)
# ═══════════════════════════════════════════════════════════════

def send_buy_signal(stock: str, price: float, target: float,
                    stoploss: float, quantity: int,
                    confidence: int, reasons: list,
                    order_type: str = "CNC"):
    """
    Sent ONLY when you should BUY. Clear instructions.
    order_type: CNC (delivery/swing) or MIS (intraday)
    """
    risk = round((price - stoploss) / price * 100, 1)
    reward = round((target - price) / price * 100, 1)
    invest = round(price * quantity, 0)

    msg = f"🟢 <b>BUY — {stock}</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"💰 Entry:    ₹{price:.2f}\n"
    msg += f"🎯 Target:   ₹{target:.2f} (+{reward}%)\n"
    msg += f"🛑 SL:       ₹{stoploss:.2f} (-{risk}%)\n"
    msg += f"📦 Qty:      {quantity}\n"
    msg += f"💵 Invest:   ₹{invest:,.0f}\n"
    msg += f"📊 Confidence: {confidence}%\n\n"

    msg += f"<b>📋 ACTION:</b>\n"
    msg += f"  1. Open Groww\n"
    msg += f"  2. Search '{stock}'\n"
    msg += f"  3. BUY | {order_type} | Market | Qty {quantity}\n"
    msg += f"  4. Set GTT SELL @ ₹{target:.0f}\n"
    msg += f"  5. Set GTT SL @ ₹{stoploss:.0f}\n\n"

    if order_type == "MIS":
        msg += "⚠️ INTRADAY — must exit by 3:15 PM\n\n"

    msg += "<b>Why:</b>\n"
    for r in reasons[:3]:
        msg += f"  • {r}\n"

    msg += f"\n⏰ {_time()}"
    return _send(msg)


# ═══════════════════════════════════════════════════════════════
# TYPE 3: EXIT SIGNAL (when to sell)
# ═══════════════════════════════════════════════════════════════

def send_exit_signal(stock: str, exit_price: float, entry_price: float,
                     quantity: int, reason: str):
    """
    Sent when you should EXIT a position.
    """
    pnl = (exit_price - entry_price) * quantity
    pnl_pct = (exit_price - entry_price) / entry_price * 100
    icon = "✅" if pnl > 0 else "❌"

    msg = f"{icon} <b>EXIT — {stock}</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"📤 Sell at:  ₹{exit_price:.2f}\n"
    msg += f"📥 Entry was: ₹{entry_price:.2f}\n"
    msg += f"📊 P&L:     <b>₹{pnl:+,.0f} ({pnl_pct:+.1f}%)</b>\n"
    msg += f"📝 Reason:  {reason}\n\n"

    msg += f"<b>📋 ACTION:</b>\n"
    if "TARGET" in reason.upper():
        msg += "  GTT should have auto-sold. Check Groww.\n"
    elif "STOP" in reason.upper():
        msg += "  GTT should have auto-sold. Check Groww.\n"
    else:
        msg += f"  Sell {stock} NOW on Groww at market.\n"
        msg += f"  Also cancel other GTT order.\n"

    msg += f"\n⏰ {_time()}"
    return _send(msg)


# ═══════════════════════════════════════════════════════════════
# TYPE 4: PORTFOLIO UPDATE (end of day)
# ═══════════════════════════════════════════════════════════════

def send_portfolio_update(capital: float, invested: float,
                          total_pnl: float, trades_today: int,
                          wins: int, losses: int,
                          positions: list):
    """
    Sent at 4 PM daily. Your scoreboard.
    """
    msg = f"📊 <b>END OF DAY</b> | {_time()}\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"💰 Capital:   ₹{capital:,.0f}\n"
    msg += f"📈 Invested:  ₹{invested:,.0f}\n"
    msg += f"📊 Total P&L: <b>₹{total_pnl:+,.0f}</b>\n"
    msg += f"🎯 Today:     {trades_today} trades | {wins}W {losses}L\n\n"

    if positions:
        msg += "<b>Open Positions:</b>\n"
        for p in positions:
            curr_pnl = p.get('current_pnl', 0)
            icon = "🟢" if curr_pnl >= 0 else "🔴"
            msg += f"  {icon} {p['stock']} @ ₹{p['entry']:.0f} → ₹{curr_pnl:+.0f}\n"
    else:
        msg += "No open positions. Cash ready.\n"

    msg += f"\n🤖 Agents scanning overnight for tomorrow..."
    return _send(msg)


# ═══════════════════════════════════════════════════════════════
# TYPE 5: WEEKLY REPORT (Sunday evening)
# ═══════════════════════════════════════════════════════════════

def send_weekly_report(week_pnl: float, total_trades: int,
                       win_rate: float, best_trade: str,
                       next_week_picks: list, sector_hot: list,
                       sector_avoid: list):
    """
    Sent Sunday 8 PM. Week summary + next week plan.
    """
    msg = f"📋 <b>WEEKLY REPORT</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"<b>This Week:</b>\n"
    msg += f"  💰 P&L: ₹{week_pnl:+,.0f}\n"
    msg += f"  📊 Trades: {total_trades} | Win Rate: {win_rate:.0f}%\n"
    if best_trade:
        msg += f"  🏆 Best: {best_trade}\n"
    msg += "\n"

    msg += f"<b>Next Week Plan:</b>\n"
    for i, p in enumerate(next_week_picks[:5], 1):
        msg += f"  {i}. {p['stock']} (Score {p['score']})\n"
    msg += "\n"

    msg += f"<b>Sectors:</b>\n"
    msg += f"  🟢 Hot: {', '.join(sector_hot[:3])}\n"
    msg += f"  🔴 Avoid: {', '.join(sector_avoid[:3])}\n"

    msg += f"\n⏰ Monday 9:30 AM: Live scan starts"
    return _send(msg)


# ═══════════════════════════════════════════════════════════════
# TEST
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("Sending test message...")
    _send("🏢 <b>Mudholkars & Co</b>\n\nAlert system reconfigured.\nYou will now receive ONLY 5 types of messages:\n\n1️⃣ Morning Brief (9:30 AM)\n2️⃣ BUY Signal (when to buy)\n3️⃣ EXIT Signal (when to sell)\n4️⃣ Portfolio Update (4 PM)\n5️⃣ Weekly Report (Sunday)\n\nNo noise. Only actionable alerts. ✅")
    print("✅ Sent")
