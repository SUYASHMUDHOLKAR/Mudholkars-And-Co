"""Agent 3: SWING SCOUT — 1 Week. Runs every Friday. Weekly breakouts, sector rotation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.base_agent import BaseTimeframeAgent

class SwingScoutAgent(BaseTimeframeAgent):
    AGENT_CONFIG = {
        "name": "Swing Scout (1 Week)", "timeframe": "1mo", "interval": "1d",
        "max_stocks": 300, "top_n": 25,
        "description": "Weekly breakouts, sector rotation, swing candidates",
    }

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    SwingScoutAgent(str(Path(__file__).parent.parent)).run()
