"""Agent 6: HALF-YEAR REVIEWER — 6 Months. Runs Jan & Jul."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.base_agent import BaseTimeframeAgent

class HalfYearAgent(BaseTimeframeAgent):
    AGENT_CONFIG = {
        "name": "Half-Year Reviewer (6M)", "timeframe": "6mo", "interval": "1d",
        "max_stocks": 500, "top_n": 30,
        "description": "6-month return rank, trend reversals, sector leaders",
    }

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    HalfYearAgent(str(Path(__file__).parent.parent)).run()
