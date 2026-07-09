"""
Agent 2: DAY TRADER — 1 Day Timeframe
Runs once daily after market close (4 PM IST)
Finds: today's top gainers/losers, delivery %, daily breakouts
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.base_agent import BaseTimeframeAgent

class DayTraderAgent(BaseTimeframeAgent):
    AGENT_CONFIG = {
        "name":        "Day Trader (1 Day)",
        "timeframe":   "5d",
        "interval":    "1d",
        "max_stocks":  300,
        "top_n":       25,
        "description": "Daily gainers/losers, delivery %, momentum",
    }

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    agent = DayTraderAgent(str(Path(__file__).parent.parent))
    agent.run()
