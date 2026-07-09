"""Agent 7: ANNUAL STRATEGIST — 1 Year. Runs monthly. 52-week analysis."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.base_agent import BaseTimeframeAgent

class AnnualAgent(BaseTimeframeAgent):
    AGENT_CONFIG = {
        "name": "Annual Strategist (1Y)", "timeframe": "1y", "interval": "1wk",
        "max_stocks": 500, "top_n": 30,
        "description": "52-week highs/lows, annual return rank, yearly multibaggers",
    }

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    AnnualAgent(str(Path(__file__).parent.parent)).run()
