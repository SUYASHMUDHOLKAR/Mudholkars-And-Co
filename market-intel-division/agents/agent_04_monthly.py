"""Agent 4: MONTHLY TRACKER — 1 Month. Runs 1st of every month."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.base_agent import BaseTimeframeAgent

class MonthlyAgent(BaseTimeframeAgent):
    AGENT_CONFIG = {
        "name": "Monthly Tracker", "timeframe": "1mo", "interval": "1d",
        "max_stocks": 500, "top_n": 30,
        "description": "Monthly return rank, FII/DII sector flow, momentum builders",
    }

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    MonthlyAgent(str(Path(__file__).parent.parent)).run()
