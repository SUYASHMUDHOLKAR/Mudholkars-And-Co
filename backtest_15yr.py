"""
backtest_15yr.py
----------------
Mudholkars and Co — 15-YEAR FULL BACKTEST

Simulates trading EVERY DAY from 2010 to 2026 using real NSE price data.
Tests the core signal strategy on Nifty 50 stocks.

Strategy:
  Entry signals: RSI<30 + MACD bullish + Above MA50 + Volume spike
  Exit: +15% target OR -7% stop-loss OR 21 days max hold
  Score threshold: ≥ 68 (minimum 3 signals agreeing)

Output:
  - Total trades, win rate, avg return
  - Year-by-year performance
  - Stock-by-stock performance
  - Signal accuracy (which signals actually work)
  - Monthly returns (compounded)
  - Maximum drawdown
  - Saves results to reports/backtest_15yr.json

Usage:
  python backtest_15yr.py
"""

import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator
from ta.volatility import AverageTrueRange

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger("Backtest15Yr")

BASE = Path(__file__).parent
REPORTS = BASE / "reports"
REPORTS.mkdir(exist_ok=True)

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

# Load ALL NSE stocks from universe
def _load_all_stocks():
    """Load all 2370+ NSE stocks from the stock universe."""
    try:
        config_file = BASE / "market-intel-division" / "config" / "nse_stocks.json"
        if config_file.exists():
            data = json.loads(config_file.read_text())
            # Extract symbols from the config
            if isinstance(data, list):
                return [s.get("symbol", s) if isinstance(s, dict) else s for s in data]
            elif isinstance(data, dict):
                all_stocks = []
                for category in data.values():
                    if isinstance(category, list):
                        for s in category:
                            if isinstance(s, dict):
                                all_stocks.append(s.get("symbol", ""))
                            else:
                                all_stocks.append(s)
                return [s for s in all_stocks if s]
    except Exception as e:
        logger.warning(f"Could not load full universe: {e}")
    
    # Fallback: Nifty 500 representative list
    return STOCKS_FALLBACK


STOCKS_FALLBACK = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "SBIN", "BAJFINANCE", "SUNPHARMA", "LT", "MARUTI",
    "HCLTECH", "ONGC", "NTPC", "COALINDIA", "HAL",
    "BHARTIARTL", "WIPRO", "TATASTEEL", "ITC", "TITAN",
    "AXISBANK", "KOTAKBANK", "ADANIENT", "TATAMOTORS", "POWERGRID",
    "DRREDDY", "CIPLA", "DIVISLAB", "NESTLEIND", "BAJAJ-AUTO",
    "HEROMOTOCO", "HINDALCO", "JSWSTEEL", "ULTRACEMCO", "TECHM",
    "ASIANPAINT", "BRITANNIA", "HINDUNILVR", "M&M", "INDUSINDBK",
    "TATAPOWER", "BEL", "BPCL", "GAIL", "VEDL",
    "DLF", "IRCTC", "PIIND", "GODREJPROP", "SIEMENS",
]

STOCKS = _load_all_stocks()

# Strategy params (from optimal_strategy.json)
TARGET_PCT = 15.0
STOP_LOSS_PCT = 7.0
MAX_HOLD_DAYS = 21
MIN_SCORE = 68
INITIAL_CAPITAL = 1000000
MAX_POSITIONS = 5
RISK_PER_TRADE_PCT = 2.0

# Signal scoring
SIGNAL_SCORES = {
    "RSI_LOW": 25,        # RSI < 30
    "RSI_MID": 10,        # RSI 30-50 (not overbought)
    "MACD_BULL": 20,      # MACD > Signal line
    "MACD_CROSS": 25,     # MACD just crossed above signal
    "ABOVE_MA50": 15,     # Price > 50-day MA
    "ABOVE_EMA20": 10,    # Price > 20-day EMA
    "VOLUME_SPIKE": 15,   # Volume > 1.5x 20-day avg
    "BREAKOUT_20D": 20,   # Price at 20-day high
}


# ═══════════════════════════════════════════════════════════════
# DATA DOWNLOAD
# ═══════════════════════════════════════════════════════════════

def download_data(symbol: str, years: int = 15) -> pd.DataFrame:
    """Download historical data for a stock."""
    try:
        ticker = yf.Ticker(f"{symbol}.NS")
        df = ticker.history(period=f"{years}y", interval="1d")
        if df.empty or len(df) < 200:
            return pd.DataFrame()
        return df
    except Exception as e:
        logger.warning(f"  Failed to download {symbol}: {e}")
        return pd.DataFrame()


def compute_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all technical signals for the entire history."""
    if len(df) < 60:
        return df

    close = df["Close"]
    volume = df["Volume"]

    # RSI
    df["rsi"] = RSIIndicator(close=close, window=14).rsi()

    # MACD
    macd_obj = MACD(close=close)
    df["macd"] = macd_obj.macd()
    df["macd_signal"] = macd_obj.macd_signal()
    df["macd_diff"] = df["macd"] - df["macd_signal"]
    df["macd_cross"] = (df["macd_diff"] > 0) & (df["macd_diff"].shift(1) <= 0)

    # Moving averages
    df["ma50"] = close.rolling(50).mean()
    df["ema20"] = EMAIndicator(close=close, window=20).ema_indicator()

    # Volume
    df["vol_avg20"] = volume.rolling(20).mean()
    df["vol_spike"] = volume > (df["vol_avg20"] * 1.5)

    # 20-day high breakout
    df["high_20d"] = close.rolling(20).max()
    df["breakout_20d"] = close >= df["high_20d"]

    # ATR for position sizing
    df["atr"] = AverageTrueRange(high=df["High"], low=df["Low"], close=close, window=14).average_true_range()

    return df


def calculate_score(row) -> tuple:
    """Calculate entry score and list of active signals for a given day."""
    score = 0
    signals = []

    try:
        rsi = float(row.get("rsi", 50))
        macd_diff = float(row.get("macd_diff", 0))
        macd_cross = bool(row.get("macd_cross", False))
        price = float(row.get("Close", 0))
        ma50 = float(row.get("ma50", 0))
        ema20 = float(row.get("ema20", 0))
        vol_spike = bool(row.get("vol_spike", False))
        breakout = bool(row.get("breakout_20d", False))

        if rsi < 30:
            score += SIGNAL_SCORES["RSI_LOW"]
            signals.append("RSI_LOW")
        elif rsi < 50:
            score += SIGNAL_SCORES["RSI_MID"]
            signals.append("RSI_MID")

        if macd_cross:
            score += SIGNAL_SCORES["MACD_CROSS"]
            signals.append("MACD_CROSS")
        elif macd_diff > 0:
            score += SIGNAL_SCORES["MACD_BULL"]
            signals.append("MACD_BULL")

        if price > ma50 and ma50 > 0:
            score += SIGNAL_SCORES["ABOVE_MA50"]
            signals.append("ABOVE_MA50")

        if price > ema20 and ema20 > 0:
            score += SIGNAL_SCORES["ABOVE_EMA20"]
            signals.append("ABOVE_EMA20")

        if vol_spike:
            score += SIGNAL_SCORES["VOLUME_SPIKE"]
            signals.append("VOLUME_SPIKE")

        if breakout:
            score += SIGNAL_SCORES["BREAKOUT_20D"]
            signals.append("BREAKOUT_20D")

    except (ValueError, TypeError):
        pass

    return score, signals


# ═══════════════════════════════════════════════════════════════
# BACKTEST ENGINE
# ═══════════════════════════════════════════════════════════════

def run_backtest():
    logger.info("=" * 65)
    logger.info("  🏢 MUDHOLKARS & CO — 15-YEAR BACKTEST")
    logger.info("  Period: 2010-2026 | Stocks: 50 | Strategy: Signal Consensus")
    logger.info("=" * 65)

    all_trades = []
    stock_stats = {}
    signal_stats = {s: {"wins": 0, "losses": 0, "total": 0} for s in SIGNAL_SCORES}
    yearly_pnl = {}
    monthly_returns = []

    capital = INITIAL_CAPITAL
    peak_capital = capital
    max_drawdown = 0

    stocks_done = 0

    for symbol in STOCKS:
        logger.info(f"\n📊 [{stocks_done+1}/{len(STOCKS)}] {symbol}...")
        df = download_data(symbol, 15)
        if df.empty:
            logger.warning(f"  No data for {symbol}")
            stocks_done += 1
            continue

        df = compute_signals(df)
        if "rsi" not in df.columns:
            stocks_done += 1
            continue

        # Drop NaN rows (first ~50 days don't have MA50)
        df = df.dropna(subset=["rsi", "ma50", "ema20"]).copy()
        if len(df) < 100:
            stocks_done += 1
            continue

        # Track per-stock
        stock_trades = []
        cooldown_until = None  # Don't re-enter same stock within 3 days of exit

        for i in range(60, len(df) - MAX_HOLD_DAYS - 1):
            row = df.iloc[i]
            entry_date = df.index[i]

            # Cooldown check
            if cooldown_until and entry_date < cooldown_until:
                continue

            score, signals = calculate_score(row)

            # Entry condition: score >= MIN_SCORE
            if score < MIN_SCORE:
                continue

            entry_price = float(df.iloc[i + 1]["Open"])  # Buy next day open
            if entry_price <= 0:
                continue

            target_price = entry_price * (1 + TARGET_PCT / 100)
            sl_price = entry_price * (1 - STOP_LOSS_PCT / 100)

            # Simulate holding period
            outcome = "EXPIRED"
            exit_price = entry_price
            exit_date = entry_date
            hold_days = 0

            for j in range(1, MAX_HOLD_DAYS + 1):
                if i + 1 + j >= len(df):
                    break
                day = df.iloc[i + 1 + j]
                hold_days = j

                # Check SL hit (using Low)
                if float(day["Low"]) <= sl_price:
                    outcome = "STOP_LOSS"
                    exit_price = sl_price
                    exit_date = df.index[i + 1 + j]
                    break

                # Check target hit (using High)
                if float(day["High"]) >= target_price:
                    outcome = "TARGET_HIT"
                    exit_price = target_price
                    exit_date = df.index[i + 1 + j]
                    break

                exit_price = float(day["Close"])
                exit_date = df.index[i + 1 + j]

            pnl_pct = (exit_price - entry_price) / entry_price * 100
            win = pnl_pct > 0

            trade = {
                "symbol": symbol,
                "entry_date": str(entry_date.date()),
                "exit_date": str(exit_date.date()) if hasattr(exit_date, 'date') else str(exit_date),
                "entry_price": round(entry_price, 2),
                "exit_price": round(exit_price, 2),
                "pnl_pct": round(pnl_pct, 2),
                "outcome": outcome,
                "win": win,
                "hold_days": hold_days,
                "score": score,
                "signals": signals,
                "year": entry_date.year,
            }
            all_trades.append(trade)
            stock_trades.append(trade)

            # Update signal stats
            for sig in signals:
                if sig in signal_stats:
                    signal_stats[sig]["total"] += 1
                    if win:
                        signal_stats[sig]["wins"] += 1
                    else:
                        signal_stats[sig]["losses"] += 1

            # Track yearly P&L
            year = entry_date.year
            yearly_pnl.setdefault(year, []).append(pnl_pct)

            # Capital simulation
            position_size = capital * (RISK_PER_TRADE_PCT / 100) / (STOP_LOSS_PCT / 100)
            position_size = min(position_size, capital * 0.2)  # max 20% per trade
            trade_pnl = position_size * (pnl_pct / 100)
            capital += trade_pnl
            peak_capital = max(peak_capital, capital)
            drawdown = (peak_capital - capital) / peak_capital * 100
            max_drawdown = max(max_drawdown, drawdown)

            # Cooldown: don't re-enter for 3 days
            cooldown_until = exit_date + timedelta(days=3) if hasattr(exit_date, 'date') else None

        # Stock stats
        if stock_trades:
            wins = sum(1 for t in stock_trades if t["win"])
            total = len(stock_trades)
            avg_ret = np.mean([t["pnl_pct"] for t in stock_trades])
            stock_stats[symbol] = {
                "trades": total,
                "wins": wins,
                "win_rate": round(wins / total * 100, 1),
                "avg_return": round(avg_ret, 2),
                "total_pnl_pct": round(sum(t["pnl_pct"] for t in stock_trades), 1),
            }
            logger.info(f"  {symbol}: {total} trades | WR={wins/total*100:.0f}% | Avg={avg_ret:+.2f}%")

        stocks_done += 1

    # ═══════════════════════════════════════════════════════════
    # FINAL RESULTS
    # ═══════════════════════════════════════════════════════════
    total_trades = len(all_trades)
    total_wins = sum(1 for t in all_trades if t["win"])
    total_losses = total_trades - total_wins
    overall_wr = (total_wins / total_trades * 100) if total_trades else 0
    avg_return = np.mean([t["pnl_pct"] for t in all_trades]) if all_trades else 0
    avg_win = np.mean([t["pnl_pct"] for t in all_trades if t["win"]]) if total_wins else 0
    avg_loss = np.mean([t["pnl_pct"] for t in all_trades if not t["win"]]) if total_losses else 0

    # Yearly breakdown
    yearly_summary = {}
    for year, pnls in sorted(yearly_pnl.items()):
        y_trades = len(pnls)
        y_wins = sum(1 for p in pnls if p > 0)
        y_avg = np.mean(pnls)
        y_total = sum(pnls)
        yearly_summary[year] = {
            "trades": y_trades,
            "win_rate": round(y_wins / y_trades * 100, 1) if y_trades else 0,
            "avg_return": round(y_avg, 2),
            "total_return": round(y_total, 1),
        }

    # Signal accuracy
    signal_accuracy = {}
    for sig, stats in signal_stats.items():
        if stats["total"] > 0:
            wr = stats["wins"] / stats["total"] * 100
            signal_accuracy[sig] = {
                "trades": stats["total"],
                "win_rate": round(wr, 1),
                "weight": round(0.5 + (wr / 100) * 1.5, 2),
            }

    # Best/worst stocks
    sorted_stocks = sorted(stock_stats.items(), key=lambda x: x[1]["avg_return"], reverse=True)
    prefer = [s[0] for s in sorted_stocks[:10] if s[1]["win_rate"] >= 55]
    avoid = [s[0] for s in sorted_stocks[-10:] if s[1]["win_rate"] < 45]

    # Final capital
    total_return_pct = (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100
    cagr = ((capital / INITIAL_CAPITAL) ** (1 / 15) - 1) * 100 if capital > 0 else 0

    # ═══════════════════════════════════════════════════════════
    # PRINT RESULTS
    # ═══════════════════════════════════════════════════════════
    print("\n" + "=" * 70)
    print("  📊 MUDHOLKARS & CO — 15-YEAR BACKTEST RESULTS")
    print("=" * 70)
    print(f"\n  Period:          2010-2026 (15 years)")
    print(f"  Stocks tested:   {stocks_done}")
    print(f"  Total trades:    {total_trades:,}")
    print(f"  Wins:            {total_wins:,} ({overall_wr:.1f}%)")
    print(f"  Losses:          {total_losses:,} ({100-overall_wr:.1f}%)")
    print(f"  Avg return/trade: {avg_return:+.2f}%")
    print(f"  Avg winning:     {avg_win:+.2f}%")
    print(f"  Avg losing:      {avg_loss:+.2f}%")
    print(f"\n  💰 CAPITAL GROWTH:")
    print(f"  Starting:        ₹{INITIAL_CAPITAL:,.0f}")
    print(f"  Ending:          ₹{capital:,.0f}")
    print(f"  Total return:    {total_return_pct:+.1f}%")
    print(f"  CAGR:            {cagr:.1f}% per year")
    print(f"  Max drawdown:    -{max_drawdown:.1f}%")
    print(f"\n  📅 YEARLY BREAKDOWN:")
    for year, data in sorted(yearly_summary.items()):
        bar = "█" * int(data["win_rate"] / 5)
        print(f"    {year}: {data['trades']:3d} trades | WR={data['win_rate']:4.1f}% {bar} | Return: {data['total_return']:+.0f}%")
    print(f"\n  📈 SIGNAL ACCURACY:")
    for sig, data in sorted(signal_accuracy.items(), key=lambda x: x[1]["win_rate"], reverse=True):
        print(f"    {sig:15s}: {data['win_rate']:5.1f}% win ({data['trades']:,} uses) → weight {data['weight']}")
    print(f"\n  ✅ PREFER: {prefer}")
    print(f"  ❌ AVOID:  {avoid}")
    print(f"\n  ⏱️ Time to ₹1Cr from ₹10L (at this CAGR): ", end="")
    if cagr > 0:
        years_to_1cr = np.log(10) / np.log(1 + cagr/100)
        print(f"{years_to_1cr:.1f} years")
    else:
        print("Never (negative returns)")
    print("=" * 70)

    # ═══════════════════════════════════════════════════════════
    # SAVE RESULTS
    # ═══════════════════════════════════════════════════════════
    results = {
        "backtest_date": datetime.now().isoformat(),
        "period": "2010-2026 (15 years)",
        "stocks_tested": stocks_done,
        "strategy": {
            "entry": "Score >= 68 (RSI + MACD + MA50 + Volume + Breakout)",
            "target": f"+{TARGET_PCT}%",
            "stop_loss": f"-{STOP_LOSS_PCT}%",
            "max_hold": f"{MAX_HOLD_DAYS} days",
        },
        "results": {
            "total_trades": total_trades,
            "wins": total_wins,
            "losses": total_losses,
            "win_rate": round(overall_wr, 1),
            "avg_return_per_trade": round(avg_return, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
        },
        "capital": {
            "initial": INITIAL_CAPITAL,
            "final": round(capital, 0),
            "total_return_pct": round(total_return_pct, 1),
            "cagr": round(cagr, 1),
            "max_drawdown_pct": round(max_drawdown, 1),
            "years_to_1cr": round(np.log(10) / np.log(1 + cagr/100), 1) if cagr > 0 else None,
        },
        "yearly": yearly_summary,
        "signal_accuracy": signal_accuracy,
        "stock_stats": stock_stats,
        "prefer_stocks": prefer,
        "avoid_stocks": avoid,
    }

    # Save
    with open(REPORTS / "backtest_15yr.json", "w") as f:
        json.dump(results, f, indent=2, default=str)
    logger.info(f"\n💾 Results saved: reports/backtest_15yr.json")

    # UPDATE LEARNING ENGINE with real data
    learning_state = {
        "min_score": MIN_SCORE,
        "signal_accuracy": {sig: data["weight"] for sig, data in signal_accuracy.items()},
        "stock_performance": {sym: {"wr": data["win_rate"], "avg": data["avg_return"]} for sym, data in stock_stats.items()},
        "pre_trained": False,
        "backtest_verified": True,
        "backtest_trades": total_trades,
        "backtest_win_rate": round(overall_wr, 1),
        "backtest_period": "15 years (2010-2026)",
        "prefer_stocks": prefer,
        "avoid_stocks": avoid,
    }
    with open(REPORTS / "learning_state.json", "w") as f:
        json.dump(learning_state, f, indent=2)
    logger.info("📚 Learning state updated with 15-year REAL data")

    return results


if __name__ == "__main__":
    run_backtest()
