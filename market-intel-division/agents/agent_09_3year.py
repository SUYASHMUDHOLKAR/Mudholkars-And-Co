"""Agent 9: 3-YEAR COMPOUNDER — Consistent compounders, dividend growers."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.base_agent import BaseTimeframeAgent

class ThreeYearAgent(BaseTimeframeAgent):
    AGENT_CONFIG = {
        "name": "3-Year Compounder", "timeframe": "3y", "interval": "1wk",
        "max_stocks": 500, "top_n": 30,
        "description": "3-year CAGR champions, consistent compounders, quality stocks",
    }

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    ThreeYearAgent(str(Path(__file__).parent.parent)).run()
