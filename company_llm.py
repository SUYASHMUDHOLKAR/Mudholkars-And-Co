"""
company_llm.py
--------------
Mudholkars and Co — AI Brain (LLM-powered)

Uses FREE Groq API (fast LLM inference) to:
  1. Diagnose why pipeline failed
  2. Auto-suggest fixes
  3. Analyze trade decisions
  4. Explain agent signals in plain English
  5. Answer questions about your portfolio

Groq API: FREE tier — 14,400 requests/day
Model: llama3-8b-8192 (fast, free)
No GPU needed — runs in cloud

Setup:
  1. Get free API key: https://console.groq.com
  2. Add to .env: GROQ_API_KEY=your_key
"""

import os
import json
import logging
import requests
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama3-8b-8192"


class CompanyLLM:
    """
    AI brain for Mudholkars & Co.
    Diagnoses issues, explains decisions, auto-fixes code.
    Uses Groq's free LLM API.
    """

    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        if not self.api_key:
            # Try loading from .env
            env_file = Path(__file__).parent / ".env"
            if env_file.exists():
                for line in env_file.read_text().splitlines():
                    if line.startswith("GROQ_API_KEY="):
                        self.api_key = line.split("=", 1)[1].strip()

    def _ask(self, prompt: str, context: str = "") -> str:
        """Send query to LLM and get response."""
        if not self.api_key:
            return "GROQ_API_KEY not configured. Get free key at https://console.groq.com"

        system = """You are the AI brain of Mudholkars and Co, a stock trading company.
You monitor 47 agents that trade Indian stocks (NSE).
You analyze issues, explain signals, and suggest fixes.
Be concise, actionable, and specific. Always respond in plain English."""

        messages = [
            {"role": "system", "content": system},
        ]
        if context:
            messages.append({"role": "user", "content": f"Context:\n{context}"})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = requests.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": messages,
                    "max_tokens": 500,
                    "temperature": 0.3,
                },
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            else:
                return f"LLM error: {resp.status_code}"
        except Exception as e:
            return f"LLM unavailable: {e}"

    # ═══════════════════════════════════════════════════════════
    # AUTO-DIAGNOSE: Why did pipeline fail?
    # ═══════════════════════════════════════════════════════════

    def diagnose_failure(self, error_log: str) -> dict:
        """
        Given an error log, diagnose the issue and suggest fix.
        """
        prompt = f"""The trading pipeline failed with this error:
{error_log}

1. What is the root cause?
2. What is the exact fix?
3. Will it self-heal or needs manual fix?
Answer in 3 bullet points."""

        diagnosis = self._ask(prompt)
        return {
            "error": error_log[:200],
            "diagnosis": diagnosis,
            "timestamp": datetime.now(IST).isoformat(),
        }

    # ═══════════════════════════════════════════════════════════
    # EXPLAIN SIGNAL: Why did agents recommend this stock?
    # ═══════════════════════════════════════════════════════════

    def explain_signal(self, stock: str, signals: dict) -> str:
        """
        Explain in plain English why agents recommended this stock.
        """
        context = json.dumps(signals, indent=2)
        prompt = f"""The trading system recommended {stock} with these signals:
{context}

Explain in simple English (3-4 sentences):
- Why is this stock a BUY?
- What's the main risk?
- What would make you exit early?"""

        return self._ask(prompt, context)

    # ═══════════════════════════════════════════════════════════
    # PORTFOLIO ADVISOR: What should I do with my portfolio?
    # ═══════════════════════════════════════════════════════════

    def advise_portfolio(self, portfolio: dict, market_condition: str) -> str:
        """
        Give portfolio advice based on current holdings and market.
        """
        prompt = f"""Current portfolio: {json.dumps(portfolio, indent=2)}
Market condition: {market_condition}

As a trading advisor, in 3-4 sentences:
1. What should I do with current positions?
2. Any risks I should know?
3. What type of new trades to look for?"""

        return self._ask(prompt)

    # ═══════════════════════════════════════════════════════════
    # MARKET SUMMARY: What happened today?
    # ═══════════════════════════════════════════════════════════

    def summarize_day(self, report: dict) -> str:
        """
        Summarize the day's market activity in plain English.
        Send to Telegram every evening.
        """
        top_picks = report.get("top_10_events", [])[:3]
        sentiment = report.get("overall_sentiment", {})

        context = f"Market sentiment: {sentiment}\nTop events: {top_picks}"
        prompt = """Based on today's market data, write a 3-sentence summary:
1. What was the market mood today?
2. What were the 2 most important events?
3. What should a trader watch for tomorrow?
Keep it simple and actionable."""

        return self._ask(prompt, context)

    # ═══════════════════════════════════════════════════════════
    # AUTO-FIX CODE: Fix broken agent code
    # ═══════════════════════════════════════════════════════════

    def suggest_code_fix(self, broken_code: str, error: str) -> str:
        """
        Given broken Python code and error, suggest the fix.
        """
        prompt = f"""This Python code is broken:
```python
{broken_code[:500]}
```

Error: {error}

Provide ONLY the corrected code snippet (no explanation).
Focus on the minimal fix needed."""

        return self._ask(prompt)

    # ═══════════════════════════════════════════════════════════
    # WEEKLY INTELLIGENCE BRIEF
    # ═══════════════════════════════════════════════════════════

    def weekly_brief(self, trades: list, market_data: dict) -> str:
        """
        Generate weekly intelligence brief combining all data.
        """
        wins = [t for t in trades if t.get("pnl", 0) > 0]
        losses = [t for t in trades if t.get("pnl", 0) <= 0]

        context = f"""
Trades this week: {len(trades)}
Wins: {len(wins)} | Losses: {len(losses)}
Total PnL: ₹{sum(t.get('pnl',0) for t in trades):+,.0f}
Market: {json.dumps(market_data, indent=2)}
"""
        prompt = """Write a weekly performance brief for a stock trader (4-5 sentences):
1. How did the week go overall?
2. What patterns worked / didn't work?
3. What should be the focus next week?
4. Any market conditions to watch?
Make it insightful and actionable."""

        return self._ask(prompt, context)


# ═══════════════════════════════════════════════════════════
# RUNNER: Use LLM in pipeline
# ═══════════════════════════════════════════════════════════

def enhance_pipeline_with_llm(pipeline_report: dict) -> dict:
    """
    Add LLM intelligence to pipeline output.
    Called at end of each pipeline run.
    """
    llm = CompanyLLM()

    # Only run if API key exists
    if not llm.api_key:
        return pipeline_report

    try:
        # Add plain English summary to report
        if pipeline_report.get("final_calls"):
            for call in pipeline_report["final_calls"][:3]:
                explanation = llm.explain_signal(
                    call.get("stock", ""),
                    {
                        "confidence": call.get("confidence"),
                        "agents": call.get("agents"),
                        "entry": call.get("entry"),
                        "target": call.get("target"),
                    }
                )
                call["llm_explanation"] = explanation

        pipeline_report["llm_summary"] = llm.summarize_day(pipeline_report)
        logger.info("LLM enhancement added to pipeline report")

    except Exception as e:
        logger.warning(f"LLM enhancement skipped: {e}")

    return pipeline_report


if __name__ == "__main__":
    print("🧠 Testing Company LLM...")
    llm = CompanyLLM()
    if llm.api_key:
        result = llm.advise_portfolio(
            {"HAL": {"qty": 18, "entry": 4507, "target": 5183}},
            "SIDEWAYS market, FII selling"
        )
        print(f"LLM advice: {result}")
    else:
        print("Add GROQ_API_KEY to .env")
        print("Free key: https://console.groq.com")
