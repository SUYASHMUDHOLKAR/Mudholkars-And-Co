"""
run_github.py
-------------
Mudholkars and Co — GitHub Actions Entry Point (v2.0)

Single entry point for all GitHub Actions runs.
Routes to the correct mode based on day/time.
Sends failure alerts via Telegram if anything crashes.

Modes:
  Mon-Fri 9:00-15:30  → TRADING: full pipeline + position monitor
  Mon-Fri 16:00       → POST-MARKET: full pipeline (EOD) + portfolio update
  Mon-Fri other hours  → RESEARCH: news scan only
  Saturday            → WEEKEND: global intel + weekend strategist
  Sunday              → LEARNING: self-improvement review

Usage:
  python run_github.py           # auto-detect mode
  python run_github.py --mode trading
  python run_github.py --mode weekend
"""

import os
import sys
import logging
import traceback
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Fix ALL import paths
BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "market-intel-division"))
sys.path.insert(0, str(BASE / "social-media-agent"))
sys.path.insert(0, str(BASE / "india-social-agent"))
sys.path.insert(0, str(BASE / "buzz-hunter-agent"))
sys.path.insert(0, str(BASE / "global-intel-agent"))
sys.path.insert(0, str(BASE / "india-intel-agent"))

os.chdir(str(BASE))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("GitHub")

IST = ZoneInfo("Asia/Kolkata")


def send_failure_alert(mode: str, error: str):
    """Send a Telegram alert when the pipeline fails."""
    try:
        from standardized_alerts import _send
        now = datetime.now(IST).strftime("%d %b %H:%M IST")
        msg = (f"🚨 <b>PIPELINE FAILURE</b>\n"
               f"━━━━━━━━━━━━━━━━━━━━━\n\n"
               f"⏰ {now}\n"
               f"📋 Mode: {mode}\n"
               f"❌ Error:\n<code>{error[:500]}</code>\n\n"
               f"🔧 Check GitHub Actions logs.")
        _send(msg)
    except Exception:
        # If even alert sending fails, just log it
        logger.error("Failed to send failure alert to Telegram")


def run_trading_mode():
    """Run full pipeline + position monitor during market hours."""
    logger.info("📈 TRADING MODE — Running full pipeline...")

    from full_pipeline import run_full_pipeline
    report = run_full_pipeline(quick=True)  # Quick mode for 15-min runs

    # Also check open positions
    logger.info("🔍 Checking open positions...")
    from position_monitor import check_positions
    actions = check_positions()
    if actions:
        logger.info(f"  ⚡ {len(actions)} exit actions triggered!")

    # Send buy signals if we have new calls
    if report and report.get("final_calls"):
        try:
            from standardized_alerts import send_buy_signal
            for call in report["final_calls"][:3]:  # max 3 alerts
                send_buy_signal(
                    stock=call["stock"],
                    price=call["entry"],
                    target=call["target"],
                    stoploss=call["stop_loss"],
                    quantity=call["quantity"],
                    confidence=int(call["confidence"]),
                    reasons=[f"{call['agents']} agents agree", f"R:R = 1:{call['risk_reward']}"],
                )
        except Exception as e:
            logger.warning(f"Failed to send buy alerts: {e}")

    return report


def run_post_market_mode():
    """Run full pipeline (deep scan) + send EOD portfolio update."""
    logger.info("📊 POST-MARKET MODE — Deep scan + portfolio update...")

    from full_pipeline import run_full_pipeline
    report = run_full_pipeline(quick=False)

    # Send portfolio update
    try:
        import json
        state_file = BASE / "reports" / "portfolio_state.json"
        if state_file.exists():
            state = json.loads(state_file.read_text())
            from standardized_alerts import send_portfolio_update

            positions = state.get("positions", [])
            send_portfolio_update(
                capital=state.get("capital", 1000000),
                invested=sum(p.get("cost", 0) for p in positions),
                total_pnl=state.get("pnl", 0),
                trades_today=0,
                wins=0, losses=0,
                positions=positions,
            )
    except Exception as e:
        logger.warning(f"Portfolio update alert failed: {e}")

    return report


def run_research_mode():
    """Run news/intel scan only (off-hours)."""
    logger.info("📚 RESEARCH MODE — News scan...")

    try:
        from intel_agent import run_cycle, load_config
        config = load_config(str(BASE / "global-intel-agent/config/intel_config.json"))
        os.chdir(str(BASE / "global-intel-agent"))
        run_cycle(config)
        os.chdir(str(BASE))
    except Exception as e:
        logger.warning(f"Global Intel scan: {e}")
        os.chdir(str(BASE))

    # Also check positions even during research hours
    try:
        from position_monitor import check_positions
        check_positions()
    except Exception as e:
        logger.warning(f"Position monitor: {e}")


def run_weekend_mode():
    """Run weekend strategist + global intel."""
    logger.info("📚 WEEKEND MODE — Strategy + Intel...")

    # Run global intel
    try:
        from intel_agent import run_cycle, load_config
        config = load_config(str(BASE / "global-intel-agent/config/intel_config.json"))
        os.chdir(str(BASE / "global-intel-agent"))
        run_cycle(config)
        os.chdir(str(BASE))
    except Exception as e:
        logger.warning(f"Global Intel: {e}")
        os.chdir(str(BASE))

    # Run weekend strategist
    try:
        from weekend_strategist import WeekendStrategist
        result = WeekendStrategist().run()

        # Send weekly report
        if result:
            from standardized_alerts import send_weekly_report
            picks = result.get("next_week_picks", [])
            rotation = result.get("sector_rotation", {})
            send_weekly_report(
                week_pnl=0,
                total_trades=0,
                win_rate=0,
                best_trade="",
                next_week_picks=picks[:5],
                sector_hot=rotation.get("money_flowing_in", []),
                sector_avoid=rotation.get("money_flowing_out", []),
            )
    except Exception as e:
        logger.warning(f"Weekend Strategist: {e}")


def run_learning_mode():
    """Sunday learning review — self-improvement cycle."""
    logger.info("🧠 LEARNING MODE — Self-improvement review...")

    try:
        from learning_engine import LearningEngine
        engine = LearningEngine()
        engine.run_weekly_review()
    except Exception as e:
        logger.warning(f"Learning engine: {e}")

    # Also run market historian to update patterns
    try:
        from market_historian import MarketHistorian
        historian = MarketHistorian()
        historian.study_market()
    except Exception as e:
        logger.warning(f"Market Historian: {e}")


def detect_mode() -> str:
    """Auto-detect which mode to run based on day/time."""
    now = datetime.now(IST)
    hour = now.hour
    dow = now.weekday()  # 0=Mon, 6=Sun

    if dow == 6:  # Sunday
        return "learning"
    elif dow == 5:  # Saturday
        return "weekend"
    elif 9 <= hour <= 15:
        return "trading"
    elif hour == 16:
        return "post_market"
    else:
        return "research"


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["trading", "post_market", "research", "weekend", "learning"],
                        help="Force a specific mode")
    args = parser.parse_args()

    mode = args.mode or detect_mode()
    now = datetime.now(IST)

    logger.info(f"🏢 Mudholkars & Co | {now.strftime('%d %b %H:%M IST')} | "
                f"Day={now.strftime('%A')} | Mode={mode.upper()}")

    try:
        if mode == "trading":
            run_trading_mode()
        elif mode == "post_market":
            run_post_market_mode()
        elif mode == "weekend":
            run_weekend_mode()
        elif mode == "learning":
            run_learning_mode()
        else:
            run_research_mode()

        logger.info("✅ Cycle complete")

    except Exception as e:
        error_msg = traceback.format_exc()
        logger.error(f"❌ Pipeline FAILED: {e}\n{error_msg}")

        # Send failure alert
        send_failure_alert(mode, str(e) + "\n" + error_msg[-300:])

        sys.exit(1)


if __name__ == "__main__":
    main()
