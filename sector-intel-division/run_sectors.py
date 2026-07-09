"""
run_sectors.py
--------------
Sector Intelligence Division — Mudholkars and Co

Runs analysis for ALL 25 Indian market sectors.
Each sector = 1 agent tracking 10-30 stocks in that sector.

Usage:
  python run_sectors.py --all              # Analyze ALL 25 sectors
  python run_sectors.py --sector IT        # Analyze IT sector only
  python run_sectors.py --sector BANKING PHARMA AUTO  # Multiple
  python run_sectors.py --list             # List all sectors
  python run_sectors.py --period 3mo       # Custom timeframe (default: 1mo)
"""

import json
import logging
import argparse
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

from core.sector_universe import SECTORS, get_all_sectors, get_sector_stocks
from core.sector_analyzer import SectorAnalyzer

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger("SectorIntel")


def run_sector(sector_name: str, period: str = "1mo") -> dict:
    """Run analysis for one sector."""
    stocks = get_sector_stocks(sector_name)
    if not stocks:
        logger.warning(f"Sector '{sector_name}' not found")
        return {}

    analyzer = SectorAnalyzer()
    logger.info(f"Analyzing {sector_name} ({len(stocks)} stocks, {period})...")
    result = analyzer.analyze_sector(sector_name, stocks, period)
    return result


def run_all_sectors(period: str = "1mo") -> list:
    """Run analysis for all 25 sectors."""
    all_results = []
    for sector_name in get_all_sectors():
        result = run_sector(sector_name, period)
        if result and not result.get("error"):
            all_results.append(result)

    # Sort by sector return
    all_results.sort(key=lambda x: x.get("sector_return", 0), reverse=True)

    # Assign ranks
    for rank, r in enumerate(all_results, 1):
        r["sector_rank"] = rank

    return all_results


def save_report(results: list, period: str):
    """Save full sector report."""
    Path("reports").mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    report = {
        "agent":       "SectorIntelDivision",
        "company":     "Mudholkars and Co",
        "timestamp":   datetime.utcnow().isoformat() + "Z",
        "ist_time":    datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %H:%M IST"),
        "period":      period,
        "sectors_analyzed": len(results),
        "sector_ranking":  [{
            "rank":         r.get("sector_rank"),
            "sector":       r.get("sector"),
            "return":       r.get("sector_return"),
            "signal":       r.get("sector_signal"),
            "breadth":      r.get("breadth_pct"),
            "stocks":       r.get("stocks_analyzed"),
            "top_stock":    r.get("top_performers", [{}])[0].get("ticker", "") if r.get("top_performers") else "",
            "top_return":   r.get("top_performers", [{}])[0].get("pct_return", 0) if r.get("top_performers") else 0,
        } for r in results],
        "full_data": results,
    }

    with open(f"reports/sector_intel_{ts}.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    with open("reports/sector_intel_latest.json", "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"Report saved: reports/sector_intel_latest.json")
    return report


def print_report(results: list, period: str):
    """Print sector ranking table."""
    ist = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %H:%M IST")
    print(f"\n{'='*70}")
    print(f"  🏭 SECTOR INTELLIGENCE DIVISION — Mudholkars and Co")
    print(f"  {ist}  |  Period: {period}")
    print(f"{'='*70}")
    print(f"\n  {'#':<4}{'SECTOR':<22}{'Return':<10}{'Signal':<18}{'Breadth':<10}{'Top Stock':<12}{'TopRet'}")
    print("  " + "-" * 68)

    for r in results:
        rank    = r.get("sector_rank", 0)
        sector  = r.get("sector", "")
        ret     = r.get("sector_return", 0)
        signal  = r.get("sector_signal", "")
        breadth = r.get("breadth_pct", 0)
        top     = r.get("top_performers", [])
        top_stk = top[0].get("ticker", "") if top else ""
        top_ret = top[0].get("pct_return", 0) if top else 0

        icon = "▲" if "BULL" in signal else ("▼" if "BEAR" in signal else "◆")
        print(f"  {rank:<4}{sector:<22}{ret:+6.1f}%   {icon} {signal:<16}{breadth:5.0f}%   {top_stk:<12}{top_ret:+.1f}%")

    # Summary
    bull = sum(1 for r in results if "BULL" in r.get("sector_signal", ""))
    bear = sum(1 for r in results if "BEAR" in r.get("sector_signal", ""))
    neut = len(results) - bull - bear
    print(f"\n  MARKET BREADTH: {bull} bullish sectors | {bear} bearish | {neut} neutral")

    # Rotation signal
    if bull >= 15:
        print("  📢 BROAD MARKET RALLY — money flowing into most sectors")
    elif bear >= 15:
        print("  📢 BROAD SELLOFF — most sectors under pressure")
    elif bull > bear:
        print(f"  📢 SECTOR ROTATION — money moving into {results[0]['sector']}, {results[1]['sector']}")
    else:
        print(f"  📢 DEFENSIVE MODE — avoid {results[-1]['sector']}, {results[-2]['sector']}")

    print(f"\n{'='*70}")


def main():
    parser = argparse.ArgumentParser(description="Sector Intelligence Division — Mudholkars and Co")
    parser.add_argument("--all",     action="store_true", help="Analyze all 25 sectors")
    parser.add_argument("--sector",  nargs="+", help="Specific sector(s) to analyze")
    parser.add_argument("--period",  default="1mo", help="Timeframe: 5d, 1mo, 3mo, 6mo, 1y (default: 1mo)")
    parser.add_argument("--list",    action="store_true", help="List all sectors")
    args = parser.parse_args()

    if args.list:
        print(f"\n{'='*60}")
        print(f"  🏭 SECTOR INTELLIGENCE — 25 Indian Market Sectors")
        print(f"{'='*60}")
        for i, (name, data) in enumerate(SECTORS.items(), 1):
            stocks = data.get("stocks", [])
            print(f"  {i:2d}. {name:<22} ({len(stocks)} stocks)  {data.get('description','')}")
        print(f"{'='*60}\n")
        return

    if args.all:
        results = run_all_sectors(args.period)
        save_report(results, args.period)
        print_report(results, args.period)
    elif args.sector:
        results = []
        for s in args.sector:
            r = run_sector(s.upper(), args.period)
            if r and not r.get("error"):
                results.append(r)
                # Print sector detail
                print(f"\n  📊 {r['sector']} | Return: {r['sector_return']:+.1f}% | Signal: {r['sector_signal']}")
                print(f"  Breadth: {r['breadth_pct']:.0f}% green | {r['stocks_analyzed']} stocks")
                print(f"  Top: ", end="")
                for t in r.get("top_performers", [])[:3]:
                    print(f"{t['ticker']}({t['pct_return']:+.1f}%) ", end="")
                print()
        if results:
            save_report(results, args.period)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
