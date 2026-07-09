"""
run_all_agents.py
-----------------
Mudholkars and Co — Master Agent Scheduler

Runs all 4 agents independently on their optimal schedules.
Each agent runs in its own background thread.
This is your shift manager — start this one file, all employees work.

Schedule:
  Scout Agent        → every 15 minutes (market hours priority)
  India Analyst      → every 60 minutes (triggered after Scout)
  Global Intel Agent → every 30 minutes
  India Intel Agent  → every 30 minutes (offset by 15 min from Global)

Usage:
  python run_all_agents.py           # start all agents
  python run_all_agents.py --status  # show agent status
  python run_all_agents.py --once    # run all once and exit
"""

import os
import sys
import time
import logging
import argparse
import threading
import subprocess
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------

BASE_DIR   = Path(__file__).parent
SCOUT_DIR  = BASE_DIR / "stock-trend-agent"
GLOBAL_DIR = BASE_DIR / "global-intel-agent"
INDIA_DIR  = BASE_DIR / "india-intel-agent"
LOGS_DIR   = BASE_DIR / "logs"

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

def setup_logging():
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / f"master_{date.today().isoformat()}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )

logger = logging.getLogger("MasterScheduler")

# ------------------------------------------------------------------
# Agent definitions
# ------------------------------------------------------------------

AGENTS = {
    "Scout": {
        "id":          "scout",
        "description": "Market price watcher — 38+ global symbols",
        "dir":         SCOUT_DIR,
        "cmd":         [sys.executable, "agent.py", "--once"],
        "interval_s":  15 * 60,      # every 15 minutes
        "start_delay": 0,            # starts immediately
        "enabled":     True,
    },
    "IndiaAnalyst": {
        "id":          "india_analyst",
        "description": "Global → India sector impact analysis",
        "dir":         SCOUT_DIR,
        "cmd":         [sys.executable, "india_agent/india_agent.py"],
        "interval_s":  60 * 60,      # every 60 minutes
        "start_delay": 5 * 60,       # starts 5 min after Scout first run
        "enabled":     True,
    },
    "GlobalIntel": {
        "id":          "global_intel",
        "description": "25 global news sources × 25 world event categories",
        "dir":         GLOBAL_DIR,
        "cmd":         [sys.executable, "intel_agent.py", "--once"],
        "interval_s":  30 * 60,      # every 30 minutes
        "start_delay": 2 * 60,       # starts 2 min after launch
        "enabled":     True,
    },
    "IndiaIntel": {
        "id":          "india_intel",
        "description": "25 Indian news sources × 25 India-specific categories",
        "dir":         INDIA_DIR,
        "cmd":         [sys.executable, "india_intel_agent.py", "--once"],
        "interval_s":  30 * 60,      # every 30 minutes
        "start_delay": 17 * 60,      # offset by 17 min (avoids overlap with GlobalIntel)
        "enabled":     True,
    },
    "GlobalSocial": {
        "id":          "global_social",
        "description": "Global social media sentiment — 12 financial media + trends",
        "dir":         BASE_DIR / "social-media-agent",
        "cmd":         [sys.executable, "social_media_agent.py", "--once"],
        "interval_s":  30 * 60,      # every 30 minutes
        "start_delay": 8 * 60,       # starts 8 min after launch
        "enabled":     True,
    },
    "IndiaSocial": {
        "id":          "india_social",
        "description": "India social media sentiment — NSE ticker buzz + trends",
        "dir":         BASE_DIR / "india-social-agent",
        "cmd":         [sys.executable, "india_social_agent.py", "--once"],
        "interval_s":  30 * 60,      # every 30 minutes
        "start_delay": 22 * 60,      # offset from GlobalSocial
        "enabled":     True,
    },
}

# ------------------------------------------------------------------
# Agent runner thread
# ------------------------------------------------------------------

class AgentThread(threading.Thread):
    """Runs a single agent on its defined schedule in a background thread."""

    def __init__(self, name: str, agent_cfg: dict, once: bool = False):
        super().__init__(name=name, daemon=True)
        self.name       = name
        self.cfg        = agent_cfg
        self.once       = once
        self.run_count  = 0
        self.last_run   = None
        self.last_status= None
        self.next_run   = None
        self._stop_evt  = threading.Event()
        self.log        = logging.getLogger(f"Agent.{name}")

    def run(self):
        delay = self.cfg["start_delay"]
        if delay > 0:
            self.log.info(f"Starting in {delay//60}m {delay%60}s...")
            if self._stop_evt.wait(timeout=delay):
                return

        while not self._stop_evt.is_set():
            self._execute()
            if self.once:
                break
            interval = self.cfg["interval_s"]
            self.next_run = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%H:%M:%S")
            self.log.info(f"Next run in {interval//60} min")
            if self._stop_evt.wait(timeout=interval):
                break

    def _execute(self):
        self.run_count += 1
        self.last_run  = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%H:%M:%S IST")
        self.log.info(f"▶  Run #{self.run_count} | {self.cfg['description']}")

        try:
            result = subprocess.run(
                self.cfg["cmd"],
                cwd=str(self.cfg["dir"]),
                capture_output=False,
                timeout=10 * 60,   # max 10 min per run
            )
            self.last_status = "OK" if result.returncode == 0 else f"EXIT {result.returncode}"
            self.log.info(f"✔  Run #{self.run_count} complete — {self.last_status}")
        except subprocess.TimeoutExpired:
            self.last_status = "TIMEOUT"
            self.log.error(f"✘  Run #{self.run_count} timed out after 10 min")
        except Exception as e:
            self.last_status = f"ERROR: {e}"
            self.log.error(f"✘  Run #{self.run_count} error: {e}")

    def stop(self):
        self._stop_evt.set()


# ------------------------------------------------------------------
# Status display
# ------------------------------------------------------------------

def print_status(threads: dict):
    now = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %H:%M:%S IST")
    print("\n" + "=" * 65)
    print(f"  Mudholkars and Co — Agent Army Status")
    print(f"  {now}")
    print("=" * 65)
    print(f"  {'Agent':15s} {'Runs':>5s}  {'Last Run':12s}  {'Status':12s}  {'Interval':10s}")
    print("-" * 65)
    for name, t in threads.items():
        interval = AGENTS[name]["interval_s"] // 60
        status   = t.last_status or "waiting..."
        last     = t.last_run or "not yet"
        print(
            f"  {'✅ ' + name:17s} {t.run_count:>5d}  {last:12s}  {status:12s}  every {interval}min"
        )
    print("=" * 65 + "\n")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Mudholkars and Co — Master Agent Scheduler")
    parser.add_argument("--once",   action="store_true", help="Run all agents once and exit")
    parser.add_argument("--status", action="store_true", help="Show schedule and exit")
    args = parser.parse_args()

    setup_logging()

    if args.status:
        print("\n" + "=" * 65)
        print("  Mudholkars and Co — Agent Schedule")
        print("=" * 65)
        for name, cfg in AGENTS.items():
            interval = cfg["interval_s"] // 60
            delay    = cfg["start_delay"] // 60
            status   = "ENABLED" if cfg["enabled"] else "DISABLED"
            print(f"  {name:15s} | {status:8s} | every {interval:3d}min | starts after {delay}min | {cfg['description']}")
        print("=" * 65 + "\n")
        return

    print("\n" + "=" * 65)
    print("  🏢  Mudholkars and Co — Agent Army Starting")
    print(f"  {datetime.now(ZoneInfo('Asia/Kolkata')).strftime('%d %b %Y %H:%M IST')}")
    print("=" * 65)
    print(f"  {'Agent':15s}  {'Schedule':15s}  {'Description'}")
    print("-" * 65)
    for name, cfg in AGENTS.items():
        if cfg["enabled"]:
            mins = cfg["interval_s"] // 60
            print(f"  ✅ {name:13s}  every {mins:3d} min    {cfg['description']}")
    print("=" * 65)
    print("  Press Ctrl+C to stop all agents\n")

    # Start all agent threads
    threads = {}
    for name, cfg in AGENTS.items():
        if cfg["enabled"]:
            t = AgentThread(name, cfg, once=args.once)
            t.start()
            threads[name] = t
            logger.info(f"Started agent thread: {name}")

    if args.once:
        # Wait for all to finish
        logger.info("Running all agents once...")
        for t in threads.values():
            t.join(timeout=15 * 60)
        print_status(threads)
        logger.info("All agents completed one run.")
        return

    # Status heartbeat every 5 minutes
    try:
        while True:
            time.sleep(5 * 60)
            print_status(threads)
    except KeyboardInterrupt:
        logger.info("Shutting down all agents...")
        for t in threads.values():
            t.stop()
        print("\n  All agents stopped. Goodbye.\n")


if __name__ == "__main__":
    main()
