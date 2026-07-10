"""
telegram_bot.py
---------------
Mudholkars and Co — Telegram Notification System

Sends trade calls, alerts, and updates to your phone.
Works even when laptop is closed (runs on GitHub Actions).

Setup:
  1. Open Telegram → search @BotFather → /newbot
  2. Name it "Mudholkars Agent" 
  3. Get the token (looks like: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz)
  4. Search @userinfobot to get your chat_id
  5. Add both to GitHub Secrets
"""

import os
import requests
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)


class TelegramBot:
    """Sends notifications to your Telegram."""

    def __init__(self, token: str = None, chat_id: str = None):
        self.token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "")
        self.base_url = f"https://api.telegram.org/bot{self.token}"

    def send(self, message: str) -> bool:
        """Send a message to your Telegram."""
        if not self.token or not self.chat_id:
            logger.warning("Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
            return False
        try:
            resp = requests.post(f"{self.base_url}/sendMessage", json={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
            }, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    # ─────────────────────────────────────────────────────
    # Pre-built notification templates
    # ─────────────────────────────────────────────────────

    def send_buy_signal(self, stock: str, price: float, target: float,
                        stoploss: float, confidence: int, reasons: list):
        """Send BUY alert."""
        msg = (
            f"🟢 <b>BUY SIGNAL — {stock}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Entry: ₹{price:.2f}\n"
            f"🎯 Target: ₹{target:.2f} (+{(target-price)/price*100:.1f}%)\n"
            f"🛑 Stop-Loss: ₹{stoploss:.2f} (-{(price-stoploss)/price*100:.1f}%)\n"
            f"📊 Confidence: {confidence}%\n\n"
            f"<b>Reasons:</b>\n"
        )
        for r in reasons[:4]:
            msg += f"  • {r}\n"
        msg += f"\n⏰ {datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%H:%M IST')}"
        msg += f"\n\n<i>Open Groww → Buy {stock} → Set GTT</i>"
        return self.send(msg)

    def send_sell_signal(self, stock: str, price: float, reason: str, pnl: float):
        """Send SELL/EXIT alert."""
        icon = "✅" if pnl > 0 else "❌"
        msg = (
            f"{icon} <b>EXIT — {stock}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📤 Exit at: ₹{price:.2f}\n"
            f"📊 P&L: ₹{pnl:+.2f}\n"
            f"📝 Reason: {reason}\n\n"
            f"⏰ {datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%H:%M IST')}"
        )
        return self.send(msg)

    def send_morning_report(self, market_bias: str, calls: list, fii_status: str):
        """Send morning market brief."""
        msg = (
            f"🌅 <b>GOOD MORNING — Market Brief</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 Market Bias: {market_bias}\n"
            f"🏦 FII: {fii_status}\n\n"
        )
        if calls:
            msg += "<b>Today's Calls:</b>\n"
            for c in calls[:5]:
                msg += f"  🟢 {c['stock']} — ₹{c.get('price',0):.0f} (Confidence: {c.get('confidence',0)}%)\n"
        else:
            msg += "⏸️ No high-conviction trades today. WAIT.\n"
        msg += f"\n⏰ {datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%d %b %Y %H:%M IST')}"
        return self.send(msg)

    def send_portfolio_update(self, capital: float, pnl: float, positions: list):
        """Send portfolio status update."""
        msg = (
            f"💼 <b>Portfolio Update</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Capital: ₹{capital:,.2f}\n"
            f"📊 Total P&L: ₹{pnl:+,.2f}\n\n"
        )
        if positions:
            msg += "<b>Open Positions:</b>\n"
            for p in positions:
                msg += f"  • {p.get('stock','')} @ ₹{p.get('entry',0):.0f}\n"
        else:
            msg += "No open positions.\n"
        msg += f"\n⏰ {datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%H:%M IST')}"
        return self.send(msg)

    def send_alert(self, title: str, message: str):
        """Send custom alert."""
        msg = f"🚨 <b>{title}</b>\n━━━━━━━━━━━━━━━━━━━━━\n{message}"
        return self.send(msg)

    def send_meeting_summary(self, hot_stocks: list, market_signal: str):
        """Send agent meeting summary."""
        msg = (
            f"🤝 <b>Agent Meeting Summary</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 Market: {market_signal}\n\n"
        )
        if hot_stocks:
            msg += "<b>Hot Stocks (3+ agents agree):</b>\n"
            for h in hot_stocks[:5]:
                msg += f"  🔥 {h.get('stock','')} — {h.get('total_agents',0)} agents, {h.get('consensus','?')}\n"
        msg += f"\n⏰ {datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%H:%M IST')}"
        return self.send(msg)


# Quick test
if __name__ == "__main__":
    bot = TelegramBot()
    if bot.token and bot.chat_id:
        bot.send("🏢 Mudholkars & Co — Bot is LIVE! ✅")
        print("✅ Test message sent!")
    else:
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
