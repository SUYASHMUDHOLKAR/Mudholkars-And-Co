"""
india_agent.py
--------------
Main runner for India Market Analyst Agent.

Workflow:
  1. Reads latest Scout Agent report from reports/ directory
  2. Fetches current India-specific data (Nifty, Sensex, VIX, INR, SGX Nifty)
  3. Runs deep analysis engine
  4. Saves India-specific analysis report

Usage:
  python india_agent/india_agent.py                # analyze latest Scout report
  python india_agent/india_agent.py --report PATH  # analyze specific report
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, date
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from india_agent.india_tracker import IndiaTracker
from india_agent.analyst import IndiaAnalyst

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------

def setup_logging(logs_dir: str = "logs") -> None:
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(logs_dir) / f"india_agent_{date.today().isoformat()}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )

logger = logging.getLogger("IndiaAgent")


# ------------------------------------------------------------------
# Scout report reader
# ------------------------------------------------------------------

def find_latest_scout_report(reports_dir: str = "reports") -> Path:
    """Find the most recent Scout Agent report."""
    reports_path = Path(reports_dir)
    if not reports_path.exists():
        logger.error(f"Reports directory not found: {reports_dir}")
        return None

    snapshots = sorted(reports_path.glob("snapshot_*.json"), reverse=True)
    eod_reports = sorted(reports_path.glob("report_*.json"), reverse=True)

    # Prefer EOD reports, fallback to snapshots
    all_reports = eod_reports + snapshots
    if not all_reports:
        logger.warning("No Scout Agent reports found")
        return None

    return all_reports[0]


def load_scout_report(report_path: Path) -> dict:
    """Load Scout Agent JSON report."""
    try:
        with open(report_path, "r") as f:
            data = json.load(f)
        logger.info(f"Loaded Scout report: {report_path.name}")
        return data
    except Exception as e:
        logger.error(f"Failed to load Scout report: {e}")
        return {}


# ------------------------------------------------------------------
# Main analysis workflow
# ------------------------------------------------------------------

def run_analysis(scout_report_path: Path = None,
                 reports_dir: str = "reports") -> dict:
    """
    Execute the India Market analysis workflow.

    1. Load Scout Agent data (or fetch latest)
    2. Fetch India-specific data
    3. Run deep analysis
    4. Save India report
    """
    logger.info("=" * 60)
    logger.info("India Market Analyst Agent Started")
    logger.info("=" * 60)

    # Load Scout data
    if not scout_report_path:
        scout_report_path = find_latest_scout_report(reports_dir)
        if not scout_report_path:
            logger.error("No Scout report available. Run Scout Agent first.")
            sys.exit(1)

    scout_data = load_scout_report(scout_report_path)
    if not scout_data:
        logger.error("Failed to load Scout report")
        sys.exit(1)

    # Fetch India-specific data
    india_tracker = IndiaTracker()
    india_snapshot = india_tracker.get_full_snapshot()

    # Run deep analysis
    analyst = IndiaAnalyst()
    analysis = analyst.analyse(scout_data, india_snapshot)

    # Print summary to console
    print("\n" + analysis.get("summary", ""))

    # Save full JSON analysis
    output_dir = Path(reports_dir) / "india_analysis"
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"india_analysis_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(analysis, f, indent=2, default=str)
    logger.info(f"India analysis saved: {json_path}")

    # Save human-readable text report
    txt_path = output_dir / f"india_analysis_{ts}.txt"
    with open(txt_path, "w") as f:
        f.write(analysis.get("summary", ""))
    logger.info(f"Text report saved: {txt_path}")

    logger.info("=" * 60)
    logger.info("India Market Analyst Agent Complete")
    logger.info("=" * 60)

    return analysis


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="India Market Analyst Agent — Deep analysis of Scout Agent data"
    )
    parser.add_argument(
        "--report",
        type=str,
        default=None,
        help="Path to specific Scout Agent report JSON file"
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        default="reports",
        help="Directory containing Scout Agent reports (default: reports/)"
    )

    args = parser.parse_args()

    setup_logging()

    scout_path = Path(args.report) if args.report else None
    run_analysis(scout_path, args.reports_dir)


if __name__ == "__main__":
    main()
