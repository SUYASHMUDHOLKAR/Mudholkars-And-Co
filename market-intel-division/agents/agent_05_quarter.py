"""Agent 5: QUARTER ANALYST — 3 Months. Runs quarterly after results season."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.base_agent import BaseTimeframeAgent

class QuarterAgent(BaseTimeframeAgent):
    AGENT_CONFIG = {
        "name": "Quarter Analyst (3M)", "timeframe": "3mo", "interval": "1d",
        "max_stocks": 500, "top_n": 30,
        "description": "Quarterly returns, earnings impact, guidance changes",
    }

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    QuarterAgent(str(Path(__file__).parent.parent)).run()
