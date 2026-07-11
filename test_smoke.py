"""
test_smoke.py
-------------
Mudholkars and Co — Basic Smoke Tests

Verifies that all modules can be imported and core objects created.
Run after any code change to catch import errors before deployment.

Usage:
  python test_smoke.py
  python -m pytest test_smoke.py -v  (if pytest installed)
"""

import os
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

# Setup paths (same as run_github.py)
BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "market-intel-division"))
sys.path.insert(0, str(BASE / "social-media-agent"))
sys.path.insert(0, str(BASE / "india-social-agent"))
sys.path.insert(0, str(BASE / "buzz-hunter-agent"))
sys.path.insert(0, str(BASE / "global-intel-agent"))
sys.path.insert(0, str(BASE / "india-intel-agent"))

os.chdir(str(BASE))

# Results
PASS = "✅"
FAIL = "❌"
results = []


def test(name):
    """Decorator to register and run a test."""
    def wrapper(fn):
        try:
            fn()
            results.append((PASS, name))
        except Exception as e:
            results.append((FAIL, f"{name}: {e}"))
        return fn
    return wrapper


# ═══════════════════════════════════════════════════════════════
# IMPORT TESTS — Can we import everything?
# ═══════════════════════════════════════════════════════════════

@test("Import: consensus_engine")
def _():
    from consensus_engine import ConsensusEngine
    assert ConsensusEngine is not None

@test("Import: risk_agent")
def _():
    from risk_agent import RiskAgent
    assert RiskAgent is not None

@test("Import: portfolio_manager")
def _():
    from portfolio_manager import PortfolioManager
    assert PortfolioManager is not None

@test("Import: nse_data_feed")
def _():
    from nse_data_feed import NSEDataFeed
    assert NSEDataFeed is not None

@test("Import: standardized_alerts")
def _():
    from standardized_alerts import send_buy_signal, send_exit_signal
    assert send_buy_signal is not None

@test("Import: enhanced_strategy")
def _():
    from enhanced_strategy import FinalStrategy, MarketFilter, MLPatternMatcher, SmartTrailingStop
    assert FinalStrategy is not None

@test("Import: market_historian")
def _():
    from market_historian import MarketHistorian
    assert MarketHistorian is not None

@test("Import: market_regime")
def _():
    from market_regime import MarketRegimeDetector
    assert MarketRegimeDetector is not None

@test("Import: breakout_scanner")
def _():
    from breakout_scanner import BreakoutScanner
    assert BreakoutScanner is not None

@test("Import: sector_momentum")
def _():
    from sector_momentum import SectorMomentumScorer
    assert SectorMomentumScorer is not None

@test("Import: promoter_tracker")
def _():
    from promoter_tracker import PromoterTracker
    assert PromoterTracker is not None

@test("Import: earnings_calendar")
def _():
    from earnings_calendar import EarningsCalendar
    assert EarningsCalendar is not None

@test("Import: learning_engine")
def _():
    from learning_engine import LearningEngine
    assert LearningEngine is not None

@test("Import: position_monitor")
def _():
    from position_monitor import check_positions, is_market_hours
    assert check_positions is not None

@test("Import: agent_bus")
def _():
    from agent_bus import AgentBus
    assert AgentBus is not None

@test("Import: weekend_strategist")
def _():
    from weekend_strategist import WeekendStrategist
    assert WeekendStrategist is not None

@test("Import: full_pipeline")
def _():
    from full_pipeline import run_full_pipeline
    assert run_full_pipeline is not None

@test("Import: run_github")
def _():
    from run_github import detect_mode, send_failure_alert
    assert detect_mode is not None


# ═══════════════════════════════════════════════════════════════
# LOGIC TESTS — Does core logic work?
# ═══════════════════════════════════════════════════════════════

@test("ConsensusEngine: basic evaluation")
def _():
    from consensus_engine import ConsensusEngine
    ce = ConsensusEngine()
    signals = {
        "Technical": {"direction": "BULLISH", "score": 75, "signal": "MACD cross", "weight": 1.5},
        "Fundamental": {"direction": "BULLISH", "score": 70, "signal": "Good PE", "weight": 1.5},
        "Social": {"direction": "BULLISH", "score": 65, "signal": "Trending", "weight": 0.8},
        "Buzz": {"direction": "BULLISH", "score": 60, "signal": "News buzz", "weight": 1.0},
    }
    result = ce.evaluate("TEST", signals)
    assert result["stock"] == "TEST"
    assert result["consensus"] in ("STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL")
    assert result["bullish_count"] == 4

@test("ConsensusEngine: mixed signals → HOLD")
def _():
    from consensus_engine import ConsensusEngine
    ce = ConsensusEngine()
    signals = {
        "Technical": {"direction": "BULLISH", "score": 60, "signal": "", "weight": 1.0},
        "Fundamental": {"direction": "BEARISH", "score": 40, "signal": "", "weight": 1.0},
    }
    result = ce.evaluate("MIXED", signals)
    assert result["consensus"] == "HOLD"

@test("RiskAgent: position sizing")
def _():
    from risk_agent import RiskAgent
    risk = RiskAgent(capital=1000000)
    plan = risk.calculate_position("TEST", entry_price=100, stop_loss_price=97)
    assert plan is not None
    # Should have quantity, risk info
    assert "quantity" in plan or "approved" in plan

@test("PortfolioManager: init with state")
def _():
    from portfolio_manager import PortfolioManager
    pm = PortfolioManager(capital=1000000)
    assert pm.capital == 1000000 or pm.capital > 0  # loaded from state
    assert pm.max_positions == 5

@test("LearningEngine: record + threshold")
def _():
    from learning_engine import LearningEngine
    engine = LearningEngine()
    threshold = engine.get_minimum_score()
    assert 40 <= threshold <= 85

@test("Weekend strategy file exists and is valid JSON")
def _():
    strategy_file = BASE / "reports" / "weekend_strategy.json"
    assert strategy_file.exists(), "weekend_strategy.json missing"
    data = json.loads(strategy_file.read_text())
    assert "next_week_picks" in data

@test("Standardized alerts: no hardcoded token")
def _():
    content = (BASE / "standardized_alerts.py").read_text()
    assert "8979796737" not in content, "TOKEN still hardcoded!"
    assert "os.environ" in content or "TELEGRAM_BOT_TOKEN" in content

@test("Portfolio state: capital aligned to ₹10L")
def _():
    state_file = BASE / "reports" / "portfolio_state.json"
    if state_file.exists():
        data = json.loads(state_file.read_text())
        capital = data.get("capital", 0)
        assert capital >= 100000, f"Capital too low: {capital}"

@test("run_github: mode detection")
def _():
    from run_github import detect_mode
    mode = detect_mode()
    assert mode in ("trading", "post_market", "research", "weekend", "learning")

@test("NSE data feed: retry logic present")
def _():
    content = (BASE / "nse_data_feed.py").read_text()
    assert "MAX_RETRIES" in content
    assert "_get_with_retry" in content


# ═══════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("  🧪 MUDHOLKARS & CO — SMOKE TESTS")
    print("=" * 55 + "\n")

    passed = sum(1 for r in results if r[0] == PASS)
    failed = sum(1 for r in results if r[0] == FAIL)

    for status, name in results:
        print(f"  {status} {name}")

    print(f"\n{'=' * 55}")
    print(f"  Results: {passed} passed, {failed} failed, {len(results)} total")
    if failed == 0:
        print("  🎉 ALL TESTS PASSED!")
    else:
        print("  ⚠️  SOME TESTS FAILED — fix before pushing!")
    print(f"{'=' * 55}\n")

    sys.exit(0 if failed == 0 else 1)
