import os
"""
india_intel_agent.py
--------------------
Main runner for India Intelligence Agent.
Mudholkars and Co — Agent #3

Same architecture as Global Intel Agent but 100% India-focused.
25 Indian news sources × 25 India-specific categories.

Every 30 minutes:
  1. Scrape 25 Indian RSS sources
  2. Classify into 25 India categories
  3. Score market impact → Nifty impact estimate
  4. Map to affected NSE stocks
  5. Save report

Usage:
  python india_intel_agent.py           # continuous
  python india_intel_agent.py --once    # single run
"""

import json
import time
import logging
import argparse
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

from india_news_scraper import IndiaNewsScraper
from india_event_classifier import IndiaEventClassifier
from india_impact_analyzer import IndiaImpactAnalyzer

# ------------------------------------------------------------------
# Logging
# ------------------------------------------------------------------

def setup_logging(logs_dir: str = "logs") -> None:
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(logs_dir) / f"india_intel_{date.today().isoformat()}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )

logger = logging.getLogger("IndiaIntelAgent")


def load_config(path: str = "config/india_intel_config.json") -> dict:
    with open(path) as f:
        return json.load(f)


# ------------------------------------------------------------------
# Core cycle
# ------------------------------------------------------------------

def run_cycle(config: dict) -> dict:
    logger.info("=" * 60)
    logger.info("INDIA INTEL AGENT — Starting cycle")
    logger.info("=" * 60)

    scraper    = IndiaNewsScraper(config)
    classifier = IndiaEventClassifier(config)
    analyzer   = IndiaImpactAnalyzer(config)

    # Step 1: Scrape
    logger.info("Step 1/3: Scraping Indian news sources...")
    articles = scraper.fetch_all()
    if not articles:
        logger.warning("No articles fetched.")
        return {}

    # Step 2: Classify
    logger.info("Step 2/3: Classifying into 25 India categories...")
    articles = classifier.classify_all(articles)
    stats    = classifier.get_stats(articles)
    logger.info(
        f"  Critical={stats['by_severity']['CRITICAL']}  "
        f"High={stats['by_severity']['HIGH']}  "
        f"Total={stats['total']}"
    )

    # Step 3: Analyze impact
    logger.info("Step 3/3: Scoring Nifty/sector impact...")
    articles = analyzer.analyze_all(articles)
    top10    = analyzer.get_top_events(articles, n=10)
    critical = analyzer.get_critical_only(articles)

    # Build sector aggregate
    sector_view = _build_sector_view(articles)

    report = {
        "agent":          "IndiaIntelAgent",
        "company":        "Mudholkars and Co",
        "timestamp":      datetime.utcnow().isoformat() + "Z",
        "generated_ist":  datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %H:%M IST"),
        "stats":          stats,
        "top_10_events":  [_slim(a) for a in top10],
        "critical_events":[_slim(a) for a in critical],
        "sector_view":    sector_view,
        "all_articles":   [_slim(a) for a in articles],
    }

    _save_reports(report, config.get("reporting", {}).get("reports_dir", "reports"))
    _print_report(report, config)
    return report


# ------------------------------------------------------------------
# Sector aggregate view
# ------------------------------------------------------------------

def _build_sector_view(articles: list) -> dict:
    """Aggregate all article impacts into per-sector score."""
    SCORE_MAP = {"BULLISH": 2, "MIXED": 0, "NEUTRAL": 0, "BEARISH": -2}
    scores = {}

    for a in articles:
        sector = a.get("primary_sector", "BROAD_MARKET")
        dirn   = a.get("direction", "MIXED")
        imp    = a.get("impact_score", 10)
        weight = imp / 100.0
        delta  = SCORE_MAP.get(dirn, 0) * weight

        if sector not in scores:
            scores[sector] = {"score": 0.0, "events": []}
        scores[sector]["score"] += delta
        scores[sector]["events"].append({
            "title":    a.get("title", "")[:70],
            "category": a.get("category", ""),
            "severity": a.get("severity", ""),
            "impact":   imp,
        })

    for sector, data in scores.items():
        s = data["score"]
        if s >= 2:
            data["direction"] = "STRONGLY_BULLISH"
        elif s >= 0.5:
            data["direction"] = "BULLISH"
        elif s <= -2:
            data["direction"] = "STRONGLY_BEARISH"
        elif s <= -0.5:
            data["direction"] = "BEARISH"
        else:
            data["direction"] = "NEUTRAL"
        data["score"]  = round(s, 2)
        data["events"] = sorted(data["events"], key=lambda x: x["impact"], reverse=True)[:3]

    return dict(sorted(scores.items(), key=lambda x: x[1]["score"], reverse=True))


# ------------------------------------------------------------------
# Report helpers
# ------------------------------------------------------------------

def _slim(a: dict) -> dict:
    return {
        "title":           a.get("title", ""),
        "source":          a.get("source", ""),
        "published":       a.get("published", ""),
        "category":        a.get("category", ""),
        "severity":        a.get("severity", ""),
        "direction":       a.get("direction", ""),
        "urgency":         a.get("urgency", ""),
        "impact_score":    a.get("impact_score", 0),
        "nifty_impact":    a.get("nifty_impact", ""),
        "primary_sector":  a.get("primary_sector", ""),
        "affected_stocks": a.get("affected_stocks", []),
        "summary_line":    a.get("summary_line", ""),
        "url":             a.get("url", ""),
    }


def _save_reports(report: dict, reports_dir: str) -> None:
    Path(reports_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_path = Path(reports_dir) / f"india_intel_{ts}.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"JSON saved: {json_path}")

    txt_path = Path(reports_dir) / f"india_intel_{ts}.txt"
    with open(txt_path, "w") as f:
        f.write(_build_text_report(report))
    logger.info(f"Text saved: {txt_path}")

    # Always overwrite latest
    Path(reports_dir).mkdir(exist_ok=True)
    with open(Path(reports_dir) / "india_intel_latest.json", "w") as f:
        json.dump(report, f, indent=2, default=str)


def _print_report(report: dict, config: dict) -> None:
    print(_build_text_report(report))


def _build_text_report(report: dict) -> str:
    lines = []
    stats = report.get("stats", {})
    sv    = stats.get("by_severity", {})

    lines.append("=" * 65)
    lines.append("  🇮🇳  INDIA INTELLIGENCE REPORT — Mudholkars and Co")
    lines.append(f"  {report.get('generated_ist', '')}")
    lines.append("=" * 65)
    lines.append(f"\nARTICLES ANALYSED  : {stats.get('total', 0)}")
    lines.append(
        f"Severity           : "
        f"CRITICAL={sv.get('CRITICAL',0)}  "
        f"HIGH={sv.get('HIGH',0)}  "
        f"MEDIUM={sv.get('MEDIUM',0)}"
    )

    # Critical alerts
    critical = report.get("critical_events", [])
    if critical:
        lines.append(f"\n⚠  CRITICAL INDIA ALERTS ({len(critical)})")
        lines.append("-" * 45)
        for a in critical[:6]:
            icon = "▲" if a["direction"] == "BULLISH" else ("▼" if a["direction"] == "BEARISH" else "◆")
            lines.append(f"  {icon} [{a['category']:25s}] {a['title'][:62]}")
            lines.append(f"      → {a['summary_line']}")
            lines.append(f"      → Nifty Impact: {a.get('nifty_impact','N/A')}  |  Urgency: {a['urgency']}")
            if a.get("affected_stocks"):
                stocks = ", ".join(a["affected_stocks"][:4])
                lines.append(f"      → Stocks Watch: {stocks}")

    # Top 10
    lines.append(f"\nTOP 10 EVENTS BY MARKET IMPACT")
    lines.append("-" * 45)
    for i, a in enumerate(report.get("top_10_events", []), 1):
        icon = "▲" if a["direction"] == "BULLISH" else ("▼" if a["direction"] == "BEARISH" else "◆")
        lines.append(
            f"  {i:2d}. [{a['severity']:8s}] {icon}  Score={a['impact_score']:3d}  "
            f"[{a['category']:25s}]"
        )
        lines.append(f"      {a['title'][:72]}")
        lines.append(f"      Nifty: {a.get('nifty_impact','N/A'):20s}  "
                     f"Stocks: {', '.join(a.get('affected_stocks',[])[:3])}")

    # Sector view
    lines.append(f"\nNSE SECTOR OUTLOOK (from India news today)")
    lines.append("-" * 45)
    for sector, data in report.get("sector_view", {}).items():
        dirn  = data.get("direction", "NEUTRAL")
        score = data.get("score", 0)
        icon  = "▲" if "BULL" in dirn else ("▼" if "BEAR" in dirn else "◆")
        top_event = data.get("events", [{}])[0].get("title", "")[:45] if data.get("events") else ""
        lines.append(
            f"  {icon} {sector:22s}: {dirn:18s} ({score:+.1f})  ← {top_event}"
        )

    # Category breakdown
    lines.append(f"\nEVENTS BY CATEGORY")
    lines.append("-" * 45)
    for cat, cnt in sorted(
        stats.get("by_category", {}).items(), key=lambda x: x[1], reverse=True
    ):
        if cnt > 0:
            lines.append(f"  {cat:30s}: {cnt}")

    lines.append("\n" + "=" * 65)
    return "\n".join(lines)


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="India Intelligence Agent — Mudholkars and Co")
    parser.add_argument("--once",   action="store_true")
    parser.add_argument("--config", default="config/india_intel_config.json")
    args = parser.parse_args()

    config = load_config(os.path.join(os.path.dirname(__file__), args.config))
    setup_logging(config.get("reporting", {}).get("logs_dir", "logs"))

    logger.info("India Intelligence Agent — Mudholkars and Co")
    logger.info("25 Indian news sources × 25 India-specific event categories")

    if args.once:
        run_cycle(config)
    else:
        interval = config.get("schedule", {}).get("interval_minutes", 30) * 60
        logger.info(f"Running every {interval//60} minutes. Ctrl+C to stop.")
        while True:
            try:
                run_cycle(config)
            except Exception as e:
                logger.error(f"Cycle error: {e}")
            logger.info(f"Next cycle in {interval//60} min...")
            time.sleep(interval)


if __name__ == "__main__":
    main()
