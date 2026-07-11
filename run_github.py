"""
run_github.py — Simple wrapper for GitHub Actions
Handles all path issues. Runs the right mode based on time.
"""
import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# Fix ALL import paths
BASE = Path(__file__).parent
for d in [BASE, BASE/"market-intel-division", BASE/"social-media-agent", 
          BASE/"india-social-agent", BASE/"buzz-hunter-agent",
          BASE/"global-intel-agent", BASE/"india-intel-agent"]:
    sys.path.insert(0, str(d))

os.chdir(str(BASE))

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("GitHub")

IST = ZoneInfo("Asia/Kolkata")
now = datetime.now(IST)
hour = now.hour
dow = now.weekday()  # 0=Mon, 6=Sun

logger.info(f"🏢 Mudholkars & Co | {now.strftime('%d %b %H:%M IST')} | Day={dow}")

try:
    # Weekend
    if dow >= 5:
        logger.info("📚 WEEKEND MODE")
        try:
            os.chdir(str(BASE/"global-intel-agent"))
            exec(open("intel_agent.py").read().replace("if __name__", "if False"))
            from intel_agent import run_cycle, load_config
            config = load_config(str(BASE/"global-intel-agent/config/intel_config.json"))
            run_cycle(config)
        except Exception as e:
            logger.warning(f"Global Intel: {e}")
        
        os.chdir(str(BASE))
        try:
            from weekend_strategist import WeekendStrategist
            WeekendStrategist().run()
        except Exception as e:
            logger.warning(f"Weekend Strategist: {e}")

    # Trading hours (9-15 IST)
    elif 9 <= hour <= 15:
        logger.info("📈 TRADING MODE")
        os.chdir(str(BASE))
        exec(open("full_pipeline.py").read().replace("if __name__", "if False"))
        # full_pipeline imports and runs

    # Post market (16)
    elif hour == 16:
        logger.info("📊 POST-MARKET")
        os.chdir(str(BASE))
        exec(open("full_pipeline.py").read().replace("if __name__", "if False"))

    # Research
    else:
        logger.info("📚 RESEARCH MODE")
        # Just run news scan
        try:
            os.chdir(str(BASE/"global-intel-agent"))
            sys.argv = ["intel_agent.py", "--once"]
            exec(open("intel_agent.py").read())
        except Exception as e:
            logger.warning(f"Intel: {e}")

    logger.info("✅ Cycle complete")

except Exception as e:
    logger.error(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
