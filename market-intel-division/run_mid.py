"""
run_mid.py
----------
Market Intelligence Division — Master Runner
Runs any or all of the 10 timeframe agents.

Usage:
  python run_mid.py --all              # Run ALL 10 agents
  python run_mid.py --agent 1          # Run Scalper only
  python run_mid.py --agent 7          # Run Annual Strategist
  python run_mid.py --agent 1 2 3      # Run multiple specific agents
  python run_mid.py --list             # Show all agents
"""

import sys
import logging
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from agents.agent_01_scalper import ScalperAgent
from agents.agent_02_daytrader import DayTraderAgent
from agents.agent_03_swing import SwingScoutAgent
from agents.agent_04_monthly import MonthlyAgent
from agents.agent_05_quarter import QuarterAgent
from agents.agent_06_halfyear import HalfYearAgent
from agents.agent_07_annual import AnnualAgent
from agents.agent_08_2year import TwoYearAgent
from agents.agent_09_3year import ThreeYearAgent
from agents.agent_10_legacy import LegacyAgent

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("MID")

AGENTS = {
    1:  ("Scalper (1 Hour)",     ScalperAgent),
    2:  ("Day Trader (1 Day)",   DayTraderAgent),
    3:  ("Swing Scout (1 Week)", SwingScoutAgent),
    4:  ("Monthly Tracker",      MonthlyAgent),
    5:  ("Quarter Analyst (3M)", QuarterAgent),
    6:  ("Half-Year (6M)",       HalfYearAgent),
    7:  ("Annual (1Y)",          AnnualAgent),
    8:  ("2-Year Builder",       TwoYearAgent),
    9:  ("3-Year Compounder",    ThreeYearAgent),
    10: ("Legacy (5Y+)",         LegacyAgent),
}

BASE_DIR = str(Path(__file__).parent)


def main():
    parser = argparse.ArgumentParser(description="Market Intelligence Division — Mudholkars and Co")
    parser.add_argument("--all",   action="store_true", help="Run all 10 agents")
    parser.add_argument("--agent", nargs="+", type=int, help="Agent numbers to run (1-10)")
    parser.add_argument("--list",  action="store_true", help="List all agents")
    args = parser.parse_args()

    if args.list:
        print("\n" + "=" * 60)
        print("  📊 MARKET INTELLIGENCE DIVISION — 10 Agents")
        print("=" * 60)
        for num, (name, _) in AGENTS.items():
            print(f"  Agent {num:2d}: {name}")
        print("=" * 60 + "\n")
        return

    to_run = []
    if args.all:
        to_run = list(AGENTS.keys())
    elif args.agent:
        to_run = [a for a in args.agent if a in AGENTS]
    else:
        parser.print_help()
        return

    print(f"\n{'='*60}")
    print(f"  🏛️ MARKET INTELLIGENCE DIVISION — Running {len(to_run)} agents")
    print(f"  {datetime.now().strftime('%d %b %Y %H:%M IST')}")
    print(f"{'='*60}\n")

    for num in to_run:
        name, AgentClass = AGENTS[num]
        logger.info(f"▶ Starting Agent #{num}: {name}")
        try:
            agent = AgentClass(BASE_DIR)
            agent.run()
        except Exception as e:
            logger.error(f"✘ Agent #{num} failed: {e}")
        logger.info(f"✔ Agent #{num} complete\n")


if __name__ == "__main__":
    main()
