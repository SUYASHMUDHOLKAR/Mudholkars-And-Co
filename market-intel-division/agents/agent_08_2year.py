"""Agent 8: 2-YEAR BUILDER — Medium-term wealth, turnaround stories."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.base_agent import BaseTimeframeAgent

class TwoYearAgent(BaseTimeframeAgent):
    AGENT_CONFIG = {
        "name": "2-Year Builder", "timeframe": "2y", "interval": "1wk",
        "max_stocks": 500, "top_n": 30,
        "description": "2-year wealth creators, turnaround stories, CAGR rank",
    }

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    TwoYearAgent(str(Path(__file__).parent.parent)).run()
