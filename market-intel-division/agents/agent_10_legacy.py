"""Agent 10: LEGACY INVESTOR — 5 Year + Inception. The ultimate wealth creator finder."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.base_agent import BaseTimeframeAgent

class LegacyAgent(BaseTimeframeAgent):
    AGENT_CONFIG = {
        "name": "Legacy Investor (5Y+)", "timeframe": "5y", "interval": "1mo",
        "max_stocks": 500, "top_n": 30,
        "description": "5-year wealth creators, multibagger hall of fame, CAGR champions since inception",
    }

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
    LegacyAgent(str(Path(__file__).parent.parent)).run()
