"""
intel_agent.py
--------------
Main runner for the Global Intelligence Agent.
Mudholkars and Co — Agent #3

Workflow every 30 minutes:
  1. Scrape 25 RSS news sources
  2. Classify each article into 25 event buckets
  3. Score market impact (0-100) and direction
  4. Map events to Indian sectors and stocks
  5. Generate and save full intelligence report

Usage:
  python intel_agent.py           # run continuously every 30 min
  python intel_agent.py --once    # single run and exit
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

from news_scraper import NewsScraper
from event_classifier import EventClassifier
from impact_analyzer import ImpactAnalyzer
from sector_mapper import SectorMapper

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------

def setup_logging(logs_dir: str = "logs") -> None:
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(logs_dir) / f"intel_agent_{date.today().isoformat()}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )

logger = logging.getLogger("GlobalIntelAgent")


# ------------------------------------------------------------------
# Config loader
# ------------------------------------------------------------------

def load_config(path: str = "config/intel_config.json") -> dict:
    with open(path) as f:
        return json.load(f)


# ------------------------------------------------------------------
# Core run cycle
# ------------------------------------------------------------------

def run_cycle(config: dict) -> dict:
    """
    Execute one full intelligence cycle.
    Returns the complete analysis dict.
    """
    logger.info("=" * 60)
    logger.info("GLOBAL INTEL AGENT — Starting cycle")
    logger.info("=" * 60)

    scraper    = NewsScraper(config)
    classifier = EventClassifier(config)
    analyzer   = ImpactAnalyzer()
    mapper     = SectorMapper()

    # Step 1: Scrape
    logger.info("Step 1/4: Scraping news sources...")
    articles = scraper.fetch_all()
    logger.info(f"  Fetched {len(articles)} articles from {len(config['news_sources']['rss_feeds'])} sources")

    if not articles:
        logger.warning("No articles fetched. Check network connectivity.")
        return {}

    # Step 2: Classify
    logger.info("Step 2/4: Classifying into 25 event buckets...")
    articles = classifier.classify_all(articles)
    stats    = classifier.get_stats(articles)
    logger.info(f"  India-relevant: {stats['india_relevant']} | "
                f"Critical: {stats['by_severity'].get('CRITICAL',0)} | "
                f"High: {stats['by_severity'].get('HIGH',0)}")

    # Step 3: Analyze impact
    logger.info("Step 3/4: Scoring market impact...")
    articles = analyzer.analyze_all(articles)
    top10    = analyzer.get_top_events(articles, n=10)
    critical = analyzer.get_critical_only(articles)

    # Step 4: Map to sectors
    logger.info("Step 4/4: Mapping to Indian sectors and stocks...")
    articles = mapper.map_all(articles)
    sector_view = mapper.get_aggregate_sector_view(articles)

    # Build final report
    report = {
        "agent":          "GlobalIntelAgent",
        "company":        "Mudholkars and Co",
        "timestamp":      datetime.utcnow().isoformat() + "Z",
        "generated_ist":  datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %H:%M IST"),
        "stats":          stats,
        "top_10_events":  [_slim(a) for a in top10],
        "critical_events":[_slim(a) for a in critical],
        "sector_view":    sector_view,
        "all_articles":   [_slim(a) for a in articles],
    }

    # Save reports
    reports_dir = config.get("reporting", {}).get("reports_dir", "reports")
    _save_reports(report, reports_dir)

    # Print to console
    _print_report(report)

    return report


# ------------------------------------------------------------------
# Report helpers
# ------------------------------------------------------------------

def _slim(article: dict) -> dict:
    """Keep only key fields for cleaner JSON output."""
    return {
        "title":          article.get("title", ""),
        "source":         article.get("source", ""),
        "published":      article.get("published", ""),
        "category":       article.get("category", ""),
        "severity":       article.get("severity", ""),
        "direction":      article.get("direction", ""),
        "urgency":        article.get("urgency", ""),
        "impact_score":   article.get("impact_score", 0),
        "india_relevant": article.get("india_relevant", False),
        "summary_line":   article.get("summary_line", ""),
        "sector_impacts": article.get("sector_impacts", []),
        "url":            article.get("url", ""),
    }


def _save_reports(report: dict, reports_dir: str) -> None:
    Path(reports_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = Path(reports_dir) / f"intel_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"JSON report saved: {json_path}")

    txt_path = Path(reports_dir) / f"intel_{ts}.txt"
    with open(txt_path, "w") as f:
        f.write(_build_text_report(report))
    logger.info(f"Text report saved: {txt_path}")

    # Always overwrite latest.json for easy access
    latest = Path(reports_dir) / "intel_latest.json"
    with open(latest, "w") as f:
        json.dump(report, f, indent=2, default=str)


def _print_report(report: dict) -> None:
    print(_build_text_report(report))


def _build_text_report(report: dict) -> str:
    lines = []
    stats = report.get("stats", {})
    lines.append("=" * 65)
    lines.append("  GLOBAL INTELLIGENCE REPORT — Mudholkars and Co")
    lines.append(f"  {report.get('generated_ist', '')}")
    lines.append("=" * 65)

    lines.append(f"\nARTICLES ANALYSED  : {stats.get('total', 0)}")
    lines.append(f"India Relevant     : {stats.get('india_relevant', 0)}")
    lines.append(
        f"Severity Breakdown : "
        f"CRITICAL={stats.get('by_severity',{}).get('CRITICAL',0)}  "
        f"HIGH={stats.get('by_severity',{}).get('HIGH',0)}  "
        f"MEDIUM={stats.get('by_severity',{}).get('MEDIUM',0)}"
    )

    # Critical alerts
    critical = report.get("critical_events", [])
    if critical:
        lines.append(f"\n{'⚠ CRITICAL ALERTS':} ({len(critical)})")
        lines.append("-" * 40)
        for a in critical[:5]:
            lines.append(f"  [{a['category']:22s}] {a['title'][:70]}")
            lines.append(f"    → {a['summary_line']}")
            lines.append(f"    → Urgency: {a['urgency']}  |  Source: {a['source']}")

    # Top 10 events
    lines.append(f"\nTOP 10 EVENTS BY MARKET IMPACT")
    lines.append("-" * 40)
    for i, a in enumerate(report.get("top_10_events", []), 1):
        dirn_icon = "▲" if a["direction"] == "BULLISH" else ("▼" if a["direction"] == "BEARISH" else "◆")
        india = " 🇮🇳" if a.get("india_relevant") else ""
        lines.append(
            f"  {i:2d}. [{a['severity']:8s}] [{a['category']:22s}] "
            f"Score={a['impact_score']:3d}  {dirn_icon}{india}"
        )
        lines.append(f"      {a['title'][:75]}")
        if a.get("sector_impacts"):
            top_sectors = ", ".join(
                f"{s['sector']}({s['direction'][:4]})"
                for s in a["sector_impacts"][:3]
            )
            lines.append(f"      Sectors: {top_sectors}")

    # Sector aggregate view
    lines.append(f"\nINDIAN SECTOR OUTLOOK (from global news)")
    lines.append("-" * 40)
    for sector, data in report.get("sector_view", {}).items():
        dirn  = data.get("direction", "NEUTRAL")
        score = data.get("score", 0)
        stocks = ", ".join(s.replace(".NS","") for s in data.get("stocks",[])[:3])
        icon  = "▲" if "BULL" in dirn else ("▼" if "BEAR" in dirn else "◆")
        lines.append(
            f"  {icon} {sector:18s}: {dirn:14s} (score {score:+.1f})  |  {stocks}"
        )

    # Category breakdown
    lines.append(f"\nEVENTS BY CATEGORY")
    lines.append("-" * 40)
    for cat, count in sorted(
        stats.get("by_category", {}).items(), key=lambda x: x[1], reverse=True
    ):
        if count > 0:
            lines.append(f"  {cat:28s}: {count} articles")

    lines.append("\n" + "=" * 65)
    return "\n".join(lines)


# ------------------------------------------------------------------
# Scheduler
# ------------------------------------------------------------------

def run_continuously(config: dict) -> None:
    interval = config.get("schedule", {}).get("interval_minutes", 30) * 60
    logger.info(f"Global Intel Agent running every {interval//60} minutes. Press Ctrl+C to stop.")
    while True:
        try:
            run_cycle(config)
        except Exception as e:
            logger.error(f"Cycle error: {e}")
        logger.info(f"Next cycle in {interval//60} minutes...")
        time.sleep(interval)


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Global Intelligence Agent — Mudholkars and Co")
    parser.add_argument("--once",   action="store_true", help="Run one cycle and exit")
    parser.add_argument("--config", default="config/intel_config.json", help="Config file path")
    args = parser.parse_args()

    config = load_config(os.path.join(os.path.dirname(__file__), args.config))
    rep    = config.get("reporting", {})
    setup_logging(rep.get("logs_dir", "logs"))

    logger.info("Global Intelligence Agent — Mudholkars and Co")
    logger.info("Monitoring 25 global event categories across 25 news sources")

    if args.once:
        run_cycle(config)
    else:
        run_continuously(config)


if __name__ == "__main__":
    main()
