"""
base_agent.py
-------------
Base class for all 10 MID timeframe agents.
Each agent just specifies its timeframe config — the base does the rest.
"""

import json
import logging
import sys
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent))
from core.stock_universe import StockUniverse
from core.timeframe_analyzer import TimeframeAnalyzer
from core.technical_analyst import TechnicalAnalyst
from core.fundamental_analyst import FundamentalAnalyst

logger = logging.getLogger(__name__)


class BaseTimeframeAgent:
    """
    Base agent for all MID timeframe agents.
    Subclass and set AGENT_CONFIG to create each specific agent.
    """

    # Override these in each agent
    AGENT_CONFIG = {
        "name":         "BaseAgent",
        "timeframe":    "1y",
        "interval":     "1d",
        "max_stocks":   200,    # how many stocks to analyze per run
        "top_n":        20,     # how many to show in report
        "description":  "Base timeframe agent",
    }

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.universe = StockUniverse(str(self.base_dir))
        self.analyzer = TimeframeAnalyzer()
        self.ta_colleague = TechnicalAnalyst()
        self.fa_colleague = FundamentalAnalyst()
        self.cfg      = self.AGENT_CONFIG

    def run(self) -> dict:
        """Execute one full cycle of this agent."""
        name      = self.cfg["name"]
        timeframe = self.cfg["timeframe"]
        interval  = self.cfg["interval"]
        max_s     = self.cfg["max_stocks"]
        top_n     = self.cfg["top_n"]

        logger.info("=" * 60)
        logger.info(f"  {name} — Analyzing ALL NSE stocks ({timeframe} timeframe)")
        logger.info("=" * 60)

        # Get stock universe
        all_stocks = self.universe.get_all_stocks()
        yf_symbols = self.universe.get_yf_symbols(all_stocks[:max_s])
        logger.info(f"Universe: {len(yf_symbols)} stocks to analyze")

        # Analyze
        results = self.analyzer.analyze_batch(yf_symbols, period=timeframe,
                                              interval=interval, max_stocks=max_s)

        if not results:
            logger.warning("No results. Market may be closed or data unavailable.")
            return {}

        # Extract insights
        top_performers = self.analyzer.get_top_performers(results, top_n)
        worst_performers = self.analyzer.get_worst_performers(results, top_n)
        near_highs     = self.analyzer.get_near_highs(results)
        near_lows      = self.analyzer.get_near_lows(results)
        momentum       = self.analyzer.get_high_momentum(results, top_n)
        consistent     = self.analyzer.get_consistent_performers(results, top_n)
        multibaggers   = self.analyzer.get_multibaggers(results)

        report = {
            "agent":            name,
            "company":          "Mudholkars and Co",
            "department":       "Market Intelligence Division",
            "timeframe":        timeframe,
            "timestamp":        datetime.utcnow().isoformat() + "Z",
            "ist_time":         datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y %H:%M IST"),
            "stocks_analyzed":  len(results),
            "top_performers":   [self._slim(r) for r in top_performers],
            "worst_performers": [self._slim(r) for r in worst_performers],
            "near_highs":       [self._slim(r) for r in near_highs[:10]],
            "near_lows":        [self._slim(r) for r in near_lows[:10]],
            "high_momentum":    [self._slim(r) for r in momentum],
            "consistent":       [self._slim(r) for r in consistent],
            "multibaggers":     [self._slim(r) for r in multibaggers[:10]],
            "summary": {
                "total_analyzed":    len(results),
                "positive_return":   sum(1 for r in results if r["pct_return"] > 0),
                "negative_return":   sum(1 for r in results if r["pct_return"] < 0),
                "avg_return":        round(sum(r["pct_return"] for r in results) / len(results), 2) if results else 0,
                "multibagger_count": len(multibaggers),
                "near_high_count":   len(near_highs),
                "near_low_count":    len(near_lows),
            },
        }

        # ======================================================
        # COLLEAGUE ORCHESTRATION
        # Top 10 stocks → Deep Technical + Fundamental Analysis
        # ======================================================
        logger.info(f"Sending top {min(10, len(top_performers))} stocks to TA & FA colleagues...")
        deep_analysis = []
        for r in top_performers[:10]:
            symbol = r.get("symbol", "")
            if not symbol:
                continue

            ta_result = self.ta_colleague.analyze(symbol)
            fa_result = self.fa_colleague.analyze(symbol)

            entry = {
                "symbol":     symbol.replace(".NS", ""),
                "timeframe_return": r.get("pct_return"),
                "technical":  None,
                "fundamental": None,
                "combined_verdict": "ANALYZING",
            }

            if ta_result:
                entry["technical"] = {
                    "score":          ta_result["technical_score"],
                    "recommendation": ta_result["recommendation"],
                    "trend":          ta_result["trend"]["direction"],
                    "signals":        ta_result["signals"][:3],
                }

            if fa_result:
                entry["fundamental"] = {
                    "score":          fa_result["fundamental_score"],
                    "classification": fa_result["classification"],
                    "pe":             fa_result["valuation"]["pe"],
                    "roe":            fa_result["profitability"]["roe"],
                    "signals":        fa_result["signals"][:3],
                }

            # Combined verdict
            ta_score = (ta_result or {}).get("technical_score", 50)
            fa_score = (fa_result or {}).get("fundamental_score", 50)
            combined = (ta_score + fa_score) / 2

            if combined >= 65:
                entry["combined_verdict"] = "STRONG BUY"
            elif combined >= 55:
                entry["combined_verdict"] = "BUY"
            elif combined >= 45:
                entry["combined_verdict"] = "HOLD"
            elif combined >= 35:
                entry["combined_verdict"] = "SELL"
            else:
                entry["combined_verdict"] = "AVOID"

            entry["combined_score"] = round(combined, 1)
            deep_analysis.append(entry)

        report["deep_analysis"] = deep_analysis
        logger.info(f"Deep analysis complete for {len(deep_analysis)} stocks")

        # Save
        self._save(report)
        self._print_report(report)
        return report

    def _slim(self, r: dict) -> dict:
        """Keep essential fields for report."""
        return {
            "symbol":          r.get("symbol", "").replace(".NS", ""),
            "pct_return":      r.get("pct_return"),
            "cagr":            r.get("cagr"),
            "last_price":      r.get("last_price"),
            "period_high":     r.get("period_high"),
            "period_low":      r.get("period_low"),
            "recent_momentum": r.get("recent_momentum"),
            "consistency_pct": r.get("consistency_pct"),
            "volume_trend":    r.get("volume_trend"),
            "near_period_high": r.get("near_period_high"),
            "rank":            r.get("rank"),
        }

    def _save(self, report: dict):
        reports_dir = self.base_dir / "reports"
        reports_dir.mkdir(exist_ok=True)
        name = self.cfg["name"].lower().replace(" ", "_")
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")

        with open(reports_dir / f"{name}_{ts}.json", "w") as f:
            json.dump(report, f, indent=2, default=str)
        with open(reports_dir / f"{name}_latest.json", "w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Report saved: reports/{name}_latest.json")

    def _print_report(self, report: dict):
        cfg = self.cfg
        s   = report.get("summary", {})
        print(f"\n{'='*60}")
        print(f"  📊 {cfg['name']} — {cfg['description']}")
        print(f"  {report.get('ist_time', '')}")
        print(f"  Timeframe: {cfg['timeframe']} | Stocks: {s.get('total_analyzed',0)}")
        print(f"{'='*60}")
        print(f"  Market: {s.get('positive_return',0)} green | {s.get('negative_return',0)} red | Avg: {s.get('avg_return',0):+.1f}%")
        print(f"  Multibaggers (100%+): {s.get('multibagger_count',0)} | Near Highs: {s.get('near_high_count',0)}")

        print(f"\n  🏆 TOP PERFORMERS ({cfg['timeframe']})")
        print("  " + "-" * 50)
        for r in report.get("top_performers", [])[:10]:
            sym  = r.get("symbol", "")
            ret  = r.get("pct_return", 0)
            cagr = r.get("cagr")
            mom  = r.get("recent_momentum", 0)
            cagr_str = f"CAGR={cagr:.1f}%" if cagr else ""
            print(f"    #{r.get('rank',0):3d}  {sym:14s}  Return: {ret:+8.1f}%  {cagr_str}  Mom: {mom:+.1f}%")

        print(f"\n  📉 WORST PERFORMERS")
        print("  " + "-" * 50)
        for r in report.get("worst_performers", [])[:5]:
            sym = r.get("symbol", "")
            ret = r.get("pct_return", 0)
            print(f"    #{r.get('rank',0):3d}  {sym:14s}  Return: {ret:+8.1f}%")

        mb = report.get("multibaggers", [])
        if mb:
            print(f"\n  🚀 MULTIBAGGERS (100%+ return in {cfg['timeframe']})")
            print("  " + "-" * 50)
            for r in mb[:5]:
                print(f"    {r['symbol']:14s}  +{r['pct_return']:.0f}%")

        # Deep Analysis from TA + FA colleagues
        deep = report.get("deep_analysis", [])
        if deep:
            print(f"\n  🧠 DEEP ANALYSIS (TA + FA Colleagues)")
            print("  " + "-" * 55)
            print(f"  {'Stock':<12s} {'Return':<9s} {'TA Score':<10s} {'FA Score':<10s} {'Combined':<10s} {'Verdict'}")
            print("  " + "-" * 55)
            for d in deep[:10]:
                sym    = d.get("symbol", "")
                ret    = d.get("timeframe_return", 0)
                ta_s   = d.get("technical", {})
                fa_s   = d.get("fundamental", {})
                ta_scr = str(ta_s.get("score", "—")) if ta_s else "—"
                fa_scr = str(fa_s.get("score", "—")) if fa_s else "—"
                comb   = str(d.get("combined_score", "—"))
                verdict= d.get("combined_verdict", "—")
                print(f"    {sym:<12s} {ret:+6.1f}%   TA={ta_scr:<5s}   FA={fa_scr:<5s}   {comb:<5s}   → {verdict}")

                # Show key signals
                if ta_s and ta_s.get("signals"):
                    print(f"      📈 {ta_s['signals'][0]}")
                if fa_s and fa_s.get("signals"):
                    print(f"      📊 {fa_s['signals'][0]}")

        print(f"\n{'='*60}")
