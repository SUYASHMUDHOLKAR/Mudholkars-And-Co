"""
agent.py
--------
Main scheduler loop for the Stock Trend Agent.

Schedule:
  - Every 15 minutes : fetch price data for all tracked symbols, run alert engine
  - Every 60 minutes : fetch technical indicators from Alpha Vantage, compute MAs
  - End of Day (EOD) : generate and save full daily report

Usage:
  python agent.py                  # run continuously
  python agent.py --once           # run one cycle and exit (useful for testing)
  python agent.py --report-only    # generate EOD report now and exit
"""

import os
import json
import time
import logging
import argparse
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

from trackers.price_tracker import PriceTracker
from trackers.indicator_tracker import IndicatorTracker
from trackers.alert_engine import AlertEngine

# ------------------------------------------------------------------
# Logging setup
# ------------------------------------------------------------------

def setup_logging(logs_dir: str, log_level: str = "INFO") -> None:
    Path(logs_dir).mkdir(parents=True, exist_ok=True)
    log_file = Path(logs_dir) / f"agent_{date.today().isoformat()}.log"

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )

logger = logging.getLogger("StockTrendAgent")


# ------------------------------------------------------------------
# Config loader
# ------------------------------------------------------------------

def load_config(path: str = "config/tracking_config.json") -> dict:
    with open(path, "r") as f:
        config = json.load(f)
    logger.info(f"Config loaded from {path}")
    return config


def get_all_symbols(config: dict) -> dict:
    """
    Flatten all ticker groups from config into categorised dict.
    Returns: { "category_name": [symbol, ...] }
    """
    tickers = config.get("tickers", {})
    groups = {}
    for group_name, items in tickers.items():
        groups[group_name] = [t["symbol"] for t in items]
    return groups


def get_priority_symbols(config: dict) -> list:
    """Return only critical + high priority index symbols for intraday tracking."""
    tickers = config.get("tickers", {})
    priority = []
    # Core indices + VIX always tracked every cycle
    for group in ["us_indices", "volatility", "asia_pacific_indices", "europe_indices"]:
        priority += [t["symbol"] for t in tickers.get(group, [])]
    return priority


def get_indicator_symbols(config: dict) -> list:
    """
    Return symbols to compute technical indicators for.
    No API quota — pandas-ta runs locally so all symbols can be tracked.
    """
    tickers = config.get("tickers", {})
    symbols = []
    # Run indicators on top US stocks + key indices
    for group in ["top_us_stocks", "us_indices", "asia_pacific_indices"]:
        symbols += [t["symbol"] for t in tickers.get(group, [])]
    return symbols


# ------------------------------------------------------------------
# Core run cycles
# ------------------------------------------------------------------

def run_price_cycle(price_tracker: PriceTracker,
                    alert_engine: AlertEngine,
                    symbols: list,
                    reports_dir: str) -> dict:
    """
    15-minute cycle: fetch prices for all symbols, run alert engine.
    Returns dict of all price data keyed by symbol.
    """
    logger.info(f"--- 15-MIN PRICE CYCLE | {datetime.now().strftime('%H:%M:%S')} ---")
    all_price_data = price_tracker.fetch_all(symbols)

    # Check for global selloff across all fetched data
    global_alert = alert_engine.check_global_selloff(all_price_data)
    if global_alert:
        logger.critical(str(global_alert))

    # Run per-symbol alerts
    all_alerts = alert_engine.evaluate_batch(all_price_data)

    # Print summary to console
    total_alerts = sum(len(v) for v in all_alerts.values())
    if total_alerts:
        logger.info(f"Alerts fired: {total_alerts} across {len(all_alerts)} symbols")
        for sym, alerts in all_alerts.items():
            for a in alerts:
                sev = a.get("severity", "")
                if sev in ("CRITICAL", "EXTREME"):
                    logger.warning(f"  {a['severity']:8s} | {sym:12s} | {a['message']}")
    else:
        logger.info("No alerts this cycle. Markets stable.")

    # Save snapshot to file
    snapshot = {
        "cycle":      "15min",
        "timestamp":  datetime.utcnow().isoformat() + "Z",
        "price_data": all_price_data,
        "alerts":     all_alerts,
    }
    _save_snapshot(snapshot, reports_dir, label="15min")
    return all_price_data


def run_indicator_cycle(indicator_tracker: IndicatorTracker,
                        price_tracker: PriceTracker,
                        alert_engine: AlertEngine,
                        symbols: list,
                        reports_dir: str) -> dict:
    """
    1-hour cycle: fetch technical indicators + compute MAs.
    Returns combined indicator + MA data.
    """
    logger.info(f"--- 1-HOUR INDICATOR CYCLE | {datetime.now().strftime('%H:%M:%S')} ---")
    all_indicators = {}
    all_ma_data    = {}

    for symbol in symbols:
        logger.info(f"Fetching indicators for {symbol}...")
        snapshot = indicator_tracker.get_full_snapshot(symbol)
        all_indicators[symbol] = snapshot

        ma = price_tracker.compute_moving_averages(symbol)
        if ma:
            all_ma_data[symbol] = ma

        # Run MA-specific alerts (golden/death cross)
        if ma:
            alerts = alert_engine._check_moving_averages(symbol, ma)
            for a in alerts:
                logger.warning(str(a))

    combined = {
        "cycle":      "1hour",
        "timestamp":  datetime.utcnow().isoformat() + "Z",
        "indicators": all_indicators,
        "ma_data":    all_ma_data,
    }
    _save_snapshot(combined, reports_dir, label="1hour")
    return combined


def generate_eod_report(price_tracker: PriceTracker,
                        indicator_tracker: IndicatorTracker,
                        alert_engine: AlertEngine,
                        config: dict,
                        reports_dir: str) -> None:
    """
    End-of-day: fetch full data for all symbols, generate JSON + TXT report.
    """
    logger.info("=" * 60)
    logger.info("GENERATING END-OF-DAY REPORT")
    logger.info("=" * 60)

    all_symbols_grouped = get_all_symbols(config)
    all_symbols_flat    = [s for syms in all_symbols_grouped.values() for s in syms]
    indicator_syms      = get_indicator_symbols(config)

    all_price_data  = price_tracker.fetch_all(all_symbols_flat)
    all_indicators  = {s: indicator_tracker.get_full_snapshot(s) for s in indicator_syms}
    all_ma_data     = {}
    for sym in indicator_syms:
        ma = price_tracker.compute_moving_averages(sym)
        if ma:
            all_ma_data[sym] = ma

    all_alerts = alert_engine.evaluate_batch(all_price_data, all_indicators, all_ma_data)
    global_alert = alert_engine.check_global_selloff(all_price_data)

    # Build report
    report = {
        "date":         date.today().isoformat(),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "summary":      _build_summary(all_price_data),
        "price_data":   all_price_data,
        "indicators":   all_indicators,
        "moving_avgs":  all_ma_data,
        "alerts":       all_alerts,
        "global_alert": global_alert.to_dict() if global_alert else None,
    }

    # Save JSON report
    Path(reports_dir).mkdir(parents=True, exist_ok=True)
    json_path = Path(reports_dir) / f"report_{date.today().isoformat()}.json"
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    logger.info(f"EOD report saved: {json_path}")

    # Save human-readable TXT report
    txt_path = Path(reports_dir) / f"report_{date.today().isoformat()}.txt"
    _write_txt_report(report, txt_path)
    logger.info(f"EOD text report saved: {txt_path}")


# ------------------------------------------------------------------
# Report helpers
# ------------------------------------------------------------------

def _build_summary(all_price_data: dict) -> dict:
    """Build a compact market summary from price data."""
    gainers, losers, unchanged = [], [], []

    for sym, data in all_price_data.items():
        if data.get("error"):
            continue
        pct = data.get("pct_change", 0)
        entry = {"symbol": sym, "pct_change": pct, "price": data.get("current_price")}
        if pct > 0.1:
            gainers.append(entry)
        elif pct < -0.1:
            losers.append(entry)
        else:
            unchanged.append(entry)

    gainers.sort(key=lambda x: x["pct_change"], reverse=True)
    losers.sort(key=lambda x: x["pct_change"])

    return {
        "total_tracked": len(all_price_data),
        "gainers":       len(gainers),
        "losers":        len(losers),
        "unchanged":     len(unchanged),
        "top_gainers":   gainers[:5],
        "top_losers":    losers[:5],
    }


def _save_snapshot(data: dict, reports_dir: str, label: str) -> None:
    Path(reports_dir).mkdir(parents=True, exist_ok=True)
    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(reports_dir) / f"snapshot_{label}_{ts}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def _write_txt_report(report: dict, path: Path) -> None:
    summary = report.get("summary", {})
    with open(path, "w") as f:
        f.write("=" * 65 + "\n")
        f.write(f"  STOCK TREND AGENT — DAILY REPORT\n")
        f.write(f"  Date: {report['date']}  |  Generated: {report['generated_at']}\n")
        f.write("=" * 65 + "\n\n")

        f.write(f"MARKET OVERVIEW\n{'-'*40}\n")
        f.write(f"  Total tracked : {summary.get('total_tracked', 0)}\n")
        f.write(f"  Gainers        : {summary.get('gainers', 0)}\n")
        f.write(f"  Losers         : {summary.get('losers', 0)}\n")
        f.write(f"  Unchanged      : {summary.get('unchanged', 0)}\n\n")

        f.write(f"TOP GAINERS\n{'-'*40}\n")
        for g in summary.get("top_gainers", []):
            f.write(f"  {g['symbol']:12s}  {g['pct_change']:+.2f}%  @ {g['price']}\n")

        f.write(f"\nTOP LOSERS\n{'-'*40}\n")
        for l in summary.get("top_losers", []):
            f.write(f"  {l['symbol']:12s}  {l['pct_change']:+.2f}%  @ {l['price']}\n")

        # Alert summary
        all_alerts = report.get("alerts", {})
        critical_alerts = [
            a for alerts in all_alerts.values()
            for a in alerts
            if a.get("severity") in ("CRITICAL", "EXTREME")
        ]
        f.write(f"\nCRITICAL ALERTS ({len(critical_alerts)})\n{'-'*40}\n")
        for a in critical_alerts:
            f.write(f"  [{a['severity']}] {a['symbol']:12s} — {a['message']}\n")

        if report.get("global_alert"):
            ga = report["global_alert"]
            f.write(f"\n*** {ga['type']} *** {ga['message']}\n")

        f.write("\n" + "=" * 65 + "\n")


# ------------------------------------------------------------------
# Scheduler
# ------------------------------------------------------------------

class AgentScheduler:
    """
    Manages timing for 15-min, 1-hour, and EOD cycles.
    Runs synchronously (single-threaded, no external dependencies).
    """

    def __init__(self, config: dict):
        self.config      = config
        sched            = config.get("schedule", {})
        self.interval_15 = sched.get("intraday_interval_minutes", 15) * 60
        self.interval_1h = 3600
        self.eod_time    = sched.get("eod_report_time", "18:00")
        self.tz          = ZoneInfo(sched.get("timezone", "Asia/Kolkata"))
        rep              = config.get("reporting", {})
        self.reports_dir = rep.get("reports_dir", "reports")

        self.price_tracker     = PriceTracker(config)
        self.indicator_tracker = IndicatorTracker(config)
        self.alert_engine      = AlertEngine(config)

        self._last_15min = 0.0
        self._last_1hour = 0.0
        self._eod_done   = False

    def run(self) -> None:
        logger.info("Stock Trend Agent started.")
        logger.info(f"  15-min price cycle every {self.interval_15 // 60} minutes")
        logger.info(f"  1-hour indicator cycle every 60 minutes")
        logger.info(f"  EOD report at {self.eod_time} {self.tz}")

        priority_syms  = get_priority_symbols(self.config)
        indicator_syms = get_indicator_symbols(self.config)

        while True:
            now = time.time()
            local_now = datetime.now(self.tz)

            # 15-min price cycle
            if now - self._last_15min >= self.interval_15:
                run_price_cycle(
                    self.price_tracker, self.alert_engine,
                    priority_syms, self.reports_dir
                )
                self._last_15min = now

            # 1-hour indicator cycle
            if now - self._last_1hour >= self.interval_1h:
                run_indicator_cycle(
                    self.indicator_tracker, self.price_tracker,
                    self.alert_engine, indicator_syms, self.reports_dir
                )
                self._last_1hour = now

            # EOD report — once per day at configured time
            eod_h, eod_m = map(int, self.eod_time.split(":"))
            is_eod = (local_now.hour == eod_h and local_now.minute == eod_m)
            today  = local_now.date().isoformat()

            if is_eod and not self._eod_done:
                generate_eod_report(
                    self.price_tracker, self.indicator_tracker,
                    self.alert_engine, self.config, self.reports_dir
                )
                self._eod_done = True
            elif not is_eod:
                self._eod_done = False  # reset for next day

            time.sleep(30)  # check every 30 seconds

    def run_once(self) -> None:
        """Single pass — useful for testing."""
        logger.info("Running single cycle (--once mode)...")
        priority_syms  = get_priority_symbols(self.config)
        indicator_syms = get_indicator_symbols(self.config)
        run_price_cycle(self.price_tracker, self.alert_engine, priority_syms, self.reports_dir)
        run_indicator_cycle(
            self.indicator_tracker, self.price_tracker,
            self.alert_engine, indicator_syms, self.reports_dir
        )
        logger.info("Single cycle complete.")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Stock Trend Agent")
    parser.add_argument("--config",      default="config/tracking_config.json",
                        help="Path to config file")
    parser.add_argument("--once",        action="store_true",
                        help="Run one cycle and exit")
    parser.add_argument("--report-only", action="store_true",
                        help="Generate EOD report now and exit")
    args = parser.parse_args()

    config = load_config(args.config)
    rep    = config.get("reporting", {})
    setup_logging(rep.get("logs_dir", "logs"), rep.get("log_level", "INFO"))

    # Create trackers/__init__.py so imports work
    Path("trackers/__init__.py").touch()

    scheduler = AgentScheduler(config)

    if args.once:
        scheduler.run_once()
    elif args.report_only:
        generate_eod_report(
            scheduler.price_tracker, scheduler.indicator_tracker,
            scheduler.alert_engine, config, rep.get("reports_dir", "reports")
        )
    else:
        scheduler.run()


if __name__ == "__main__":
    main()
