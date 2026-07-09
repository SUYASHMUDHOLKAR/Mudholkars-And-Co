"""
Agent 1: SCALPER — 1 Hour Timeframe
Runs every hour during market hours (9:15 AM - 3:30 PM IST)
Finds: intraday movers, hourly breakouts, volume surges
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.base_agent import BaseTimeframeAgent

class ScalperAgent(BaseTimeframeAgent):
    AGENT_CONFIG = {
        "name":        "Scalper (1 Hour)",
        "timeframe":   "1d",
        "interval":    "1h",
        "max_stocks":  100,
        "top_n":       20,
        "description": "Intraday movers, hourly breakouts, volume surges",
    }

if __name__ == "__main__":
    import logging, argparse
    from pathlib import Path
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    agent = ScalperAgent(str(Path(__file__).parent.parent))
    agent.run()
