import os
"""
buzz_hunter.py
--------------
🕵️ Buzz Hunter Agent — Mudholkars and Co

This agent has ONE job: Find stocks that are buzzing on the internet.
It scans news, volume, price, and Google to find what everyone is talking about.

Usage:
  python buzz_hunter.py           # continuous (every 30 min)
  python buzz_hunter.py --once    # single scan
"""

import json
import time
import logging
import argparse
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

from buzz_scanner import BuzzScanner
from buzz_scorer import BuzzScorer

def setup_logging():
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[
            logging.FileHandler(f"logs/buzz_{date.today()}.log"),
            logging.StreamHandler(),
        ],
    )

logger = logging.getLogger("BuzzHunter")


def run_cycle() -> dict:
    logger.info("🕵️ BUZZ HUNTER — Scanning the internet for stock buzz...")

    scanner = BuzzScanner()
    scorer  = BuzzScorer()

    # Scan everything
    raw_data = scanner.scan_all()

    # Score and rank
    scored = scorer.score_all(raw_data)

    # Split India vs Global
    from buzz_scanner import INDIA_STOCKS
    india_buzz  = [s for s in scored if s["ticker"] in INDIA_STOCKS]
    global_buzz = [s for s in scored if s["ticker"] not in INDIA_STOCKS]

    report = {
        "agent":       "BuzzHunter",
        "company":     "Mudholkars and Co",
        "timestamp":   datetime.utcnow().isoformat() + "Z",
        "ist_time":    datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %H:%M IST"),
        "total_stocks_buzzing": len(scored),
        "india_buzz":  india_buzz[:15],
        "global_buzz": global_buzz[:15],
        "all_buzz":    scored[:25],
        "raw_data": {
            "news_mentions":  raw_data.get("news_mentions", {}),
            "volume_spikes":  len(raw_data.get("volume_spikes", [])),
            "top_gainers":    len(raw_data.get("price_momentum", {}).get("top_gainers", [])),
        },
    }

    # Save
    Path("reports").mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"reports/buzz_{ts}.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    with open("reports/buzz_latest.json", "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Print
    _print_report(report)
    return report


def _print_report(report: dict):
    print("\n" + "=" * 60)
    print("  🕵️ BUZZ HUNTER REPORT — Mudholkars and Co")
    print(f"  {report.get('ist_time', '')}")
    print("=" * 60)
    print(f"\n  Total Stocks Buzzing: {report['total_stocks_buzzing']}")

    # India
    india = report.get("india_buzz", [])
    if india:
        print(f"\n  🇮🇳 TOP BUZZING — INDIAN STOCKS")
        print("  " + "-" * 50)
        for i, s in enumerate(india[:10], 1):
            sig = s.get("signals_fired", 0)
            raw = s.get("raw", {})
            details = []
            if raw.get("mentions"):
                details.append(f"News:{raw['mentions']}")
            if raw.get("volume_ratio"):
                details.append(f"Vol:{raw['volume_ratio']}x")
            if raw.get("pct_change"):
                details.append(f"Price:{raw['pct_change']:+.1f}%")
            detail_str = " | ".join(details)

            print(f"    #{i:2d}  {s['ticker']:12s}  Buzz: {s['total']:3d}/100  "
                  f"{s.get('label','')}  [{sig} signals]")
            print(f"         {detail_str}")

    # Global
    glob = report.get("global_buzz", [])
    if glob:
        print(f"\n  🌍 TOP BUZZING — GLOBAL STOCKS")
        print("  " + "-" * 50)
        for i, s in enumerate(glob[:10], 1):
            raw = s.get("raw", {})
            details = []
            if raw.get("mentions"):
                details.append(f"News:{raw['mentions']}")
            if raw.get("volume_ratio"):
                details.append(f"Vol:{raw['volume_ratio']}x")
            if raw.get("pct_change"):
                details.append(f"Price:{raw['pct_change']:+.1f}%")
            detail_str = " | ".join(details)

            print(f"    #{i:2d}  {s['ticker']:8s}  Buzz: {s['total']:3d}/100  "
                  f"{s.get('label','')}  [{s.get('signals_fired',0)} signals]")
            print(f"         {detail_str}")

    print("\n" + "=" * 60)


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(description="🕵️ Buzz Hunter — Mudholkars and Co")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    setup_logging()
    logger.info("🕵️ Buzz Hunter Agent — Mudholkars and Co")
    logger.info("Job: Find stocks buzzing on the internet. Nothing else.")

    if args.once:
        run_cycle()
    else:
        logger.info("Scanning every 30 minutes. Ctrl+C to stop.")
        while True:
            try:
                run_cycle()
            except Exception as e:
                logger.error(f"Cycle error: {e}")
            time.sleep(30 * 60)


if __name__ == "__main__":
    main()
