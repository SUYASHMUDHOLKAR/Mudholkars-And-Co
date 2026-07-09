"""
company_daemon.py
-----------------
Mudholkars and Co — 24/7 Company Daemon (Auto-healing)

Runs the entire company non-stop. Knows when market is open/closed.
Auto-heals: restarts crashed agents, retries failed API calls.

Market hours:  9:15 AM - 3:30 PM IST (Mon-Fri) → AGGRESSIVE mode
Off hours:     3:30 PM - 9:15 AM / weekends    → RESEARCH mode

Usage:
  python company_daemon.py          # Start the company (runs forever)
  python company_daemon.py --status # Show company status
"""

import os
import sys
import json
import time
import logging
import signal
import traceback
import subprocess
from datetime import datetime, date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from threading import Thread, Event

BASE = Path(__file__).parent
IST = ZoneInfo("Asia/Kolkata")

# Logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler(f"logs/company_{date.today()}.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("CompanyDaemon")


# ═══════════════════════════════════════════════════════════
# MARKET AWARENESS
# ═══════════════════════════════════════════════════════════

def is_market_open() -> bool:
    """Check if NSE is currently open."""
    now = datetime.now(IST)
    # Weekday check (Mon=0, Sun=6)
    if now.weekday() >= 5:  # Saturday/Sunday
        return False
    # Time check: 9:15 AM to 3:30 PM
    market_open = now.replace(hour=9, minute=15, second=0)
    market_close = now.replace(hour=15, minute=30, second=0)
    return market_open <= now <= market_close


def is_pre_market() -> bool:
    """9:00 AM - 9:15 AM: pre-market session."""
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    return now.replace(hour=9, minute=0) <= now <= now.replace(hour=9, minute=15)


def is_post_market() -> bool:
    """3:30 PM - 4:00 PM: post-market analysis window."""
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    return now.replace(hour=15, minute=30) <= now <= now.replace(hour=16, minute=0)


def get_mode() -> str:
    """What mode should the company be in right now."""
    if is_market_open():
        return "TRADING"
    elif is_pre_market():
        return "PRE_MARKET"
    elif is_post_market():
        return "POST_MARKET"
    else:
        return "RESEARCH"


# ═══════════════════════════════════════════════════════════
# AGENT RUNNER WITH AUTO-HEAL
# ═══════════════════════════════════════════════════════════

def run_agent(name: str, cmd: list, cwd: str, timeout: int = 600) -> dict:
    """Run an agent with error handling and auto-retry."""
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"▶ {name} (attempt {attempt}/{max_retries})")
            result = subprocess.run(
                cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
            )
            if result.returncode == 0:
                logger.info(f"✔ {name} completed successfully")
                return {"status": "OK", "name": name}
            else:
                logger.warning(f"⚠ {name} exited with code {result.returncode}")
                if attempt < max_retries:
                    logger.info(f"  Retrying in 10s...")
                    time.sleep(10)
        except subprocess.TimeoutExpired:
            logger.error(f"✘ {name} timed out after {timeout}s")
            if attempt < max_retries:
                time.sleep(5)
        except Exception as e:
            logger.error(f"✘ {name} crashed: {e}")
            if attempt < max_retries:
                time.sleep(5)

    logger.error(f"✘ {name} FAILED after {max_retries} attempts — auto-healing skipped")
    return {"status": "FAILED", "name": name}


# ═══════════════════════════════════════════════════════════
# SCHEDULE DEFINITIONS
# ═══════════════════════════════════════════════════════════

PY = sys.executable

TRADING_SCHEDULE = {
    # During market hours: aggressive scanning every 15 min
    "full_pipeline": {
        "cmd": [PY, "full_pipeline.py", "--quick"],
        "cwd": str(BASE),
        "interval": 15 * 60,  # every 15 min
    },
}

PRE_MARKET_TASKS = {
    "morning_scan": {
        "cmd": [PY, "full_pipeline.py", "--quick"],
        "cwd": str(BASE),
    },
}

POST_MARKET_TASKS = {
    "eod_full_scan": {
        "cmd": [PY, "full_pipeline.py"],
        "cwd": str(BASE),
    },
    "sector_scan": {
        "cmd": [PY, "run_sectors.py", "--all", "--period", "1mo"],
        "cwd": str(BASE / "sector-intel-division"),
    },
}

RESEARCH_SCHEDULE = {
    # Off-hours: intelligence gathering every 30 min
    "global_intel": {
        "cmd": [PY, "intel_agent.py", "--once"],
        "cwd": str(BASE / "global-intel-agent"),
        "interval": 30 * 60,
    },
    "india_intel": {
        "cmd": [PY, "india_intel_agent.py", "--once"],
        "cwd": str(BASE / "india-intel-agent"),
        "interval": 30 * 60,
    },
    "social_scan": {
        "cmd": [PY, "social_media_agent.py", "--once"],
        "cwd": str(BASE / "social-media-agent"),
        "interval": 60 * 60,
    },
}


# ═══════════════════════════════════════════════════════════
# MAIN DAEMON LOOP
# ═══════════════════════════════════════════════════════════

class CompanyDaemon:
    """Runs Mudholkars and Co 24/7 with auto-healing."""

    def __init__(self):
        self.running = True
        self.last_run = {}
        self.stats = {
            "started": datetime.now(IST).isoformat(),
            "cycles": 0,
            "errors": 0,
            "trades_placed": 0,
        }
        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

    def run(self):
        logger.info("=" * 60)
        logger.info("  🏢 MUDHOLKARS AND CO — COMPANY STARTED")
        logger.info(f"  {datetime.now(IST).strftime('%d %b %Y %H:%M IST')}")
        logger.info("  Mode: 24/7 Auto-healing Daemon")
        logger.info("=" * 60)

        while self.running:
            try:
                mode = get_mode()
                now = datetime.now(IST)
                self.stats["cycles"] += 1

                if mode == "PRE_MARKET":
                    logger.info(f"🌅 PRE-MARKET MODE | {now.strftime('%H:%M')}")
                    if not self.last_run.get("pre_market_today"):
                        for name, task in PRE_MARKET_TASKS.items():
                            run_agent(name, task["cmd"], task["cwd"])
                        self.last_run["pre_market_today"] = now.date().isoformat()
                    time.sleep(60)

                elif mode == "TRADING":
                    logger.info(f"📈 TRADING MODE | {now.strftime('%H:%M')}")
                    for name, task in TRADING_SCHEDULE.items():
                        interval = task.get("interval", 900)
                        last = self.last_run.get(name, 0)
                        if time.time() - last >= interval:
                            run_agent(name, task["cmd"], task["cwd"])
                            self.last_run[name] = time.time()
                    time.sleep(60)  # check every minute

                elif mode == "POST_MARKET":
                    logger.info(f"📊 POST-MARKET MODE | {now.strftime('%H:%M')}")
                    if not self.last_run.get("post_market_today"):
                        for name, task in POST_MARKET_TASKS.items():
                            run_agent(name, task["cmd"], task["cwd"])
                        self.last_run["post_market_today"] = now.date().isoformat()
                    time.sleep(120)

                elif mode == "RESEARCH":
                    for name, task in RESEARCH_SCHEDULE.items():
                        interval = task.get("interval", 1800)
                        last = self.last_run.get(name, 0)
                        if time.time() - last >= interval:
                            run_agent(name, task["cmd"], task["cwd"])
                            self.last_run[name] = time.time()
                    time.sleep(120)

                # Save health status
                self._save_health()

            except Exception as e:
                self.stats["errors"] += 1
                logger.error(f"DAEMON ERROR: {e}")
                logger.error(traceback.format_exc())
                logger.info("Auto-healing: sleeping 30s then continuing...")
                time.sleep(30)

    def _save_health(self):
        """Save health status for monitoring."""
        health = {
            "status":   "RUNNING",
            "mode":     get_mode(),
            "uptime":   str(datetime.now(IST) - datetime.fromisoformat(self.stats["started"])),
            "cycles":   self.stats["cycles"],
            "errors":   self.stats["errors"],
            "last_check": datetime.now(IST).isoformat(),
        }
        Path("reports").mkdir(exist_ok=True)
        with open("reports/health.json", "w") as f:
            json.dump(health, f, indent=2)

    def _shutdown(self, signum, frame):
        logger.info("Shutdown signal received. Stopping gracefully...")
        self.running = False


# ═══════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Mudholkars and Co — 24/7 Daemon")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        health_file = Path("reports/health.json")
        if health_file.exists():
            with open(health_file) as f:
                h = json.load(f)
            print(f"\n  🏢 Company Status: {h['status']}")
            print(f"  Mode: {h['mode']}")
            print(f"  Uptime: {h['uptime']}")
            print(f"  Cycles: {h['cycles']} | Errors: {h['errors']}")
            print(f"  Last check: {h['last_check']}")
        else:
            print("  Company not running. Start with: python company_daemon.py")
    else:
        daemon = CompanyDaemon()
        daemon.run()
