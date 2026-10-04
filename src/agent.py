"""The agent: question -> SQL -> guardrails -> results -> chart -> insight.

Every step is observable: the caller gets the generated SQL, the
guardrail verdict, the rows, the chart spec and the insight. Nothing
is hidden, because an analyst who can't show their work isn't an
analyst.
"""
import time
from dataclasses import dataclass, field

import config
from src import charts, insights
from src.charts import ChartSpec
from src.execute import Result, execute
from src.guardrails import CheckedQuery, GuardrailError, check
from src.sqlgen import Generation, LLMClient, generate_sql


@dataclass
class Answer:
    question: str
    sql: str = ""
    refused: bool = False
    refusal_reason: str = ""
    result: Result | None = None
    chart: ChartSpec = field(default_factory=lambda: ChartSpec(kind="table"))
    insight: str = ""
    latency_s: float = 0.0
    cost_usd: float = 0.0


def ask(question: str, db_path: str = config.DB_PATH,
        llm: LLMClient | None = None,
        sql_override: str | None = None,
        insight_override=None) -> Answer:
    """Answer a question. sql_override bypasses generation (used by evals,
    tests and demo mode to exercise the pipeline deterministically).
    insight_override is either a fixed string or a callable(result) used
    instead of the LLM insight (demo mode without an API key)."""
    t0 = time.time()
    llm = llm or LLMClient()
    ans = Answer(question=question)

    if sql_override is not None:
        gen = Generation(sql=sql_override)
    else:
        gen = generate_sql(question, db_path, llm)
    ans.cost_usd = gen.cost_usd
    if gen.refused:
        ans.refused = True
        ans.refusal_reason = ("no LLM key configured" if not llm.enabled
                              else "question out of scope for this database")
        ans.latency_s = time.time() - t0
        return ans
    ans.sql = gen.sql

    try:
        checked: CheckedQuery = check(gen.sql)
    except GuardrailError as e:
        ans.refused = True
        ans.refusal_reason = f"rejected by guardrails: {e}"
        ans.latency_s = time.time() - t0
        return ans

    try:
        ans.result = execute(checked, db_path)
    except Exception as e:
        ans.refused = True
        ans.refusal_reason = f"execution failed: {e}"
        ans.latency_s = time.time() - t0
        return ans

    ans.chart = charts.suggest(ans.result)
    if insight_override is not None:
        ans.insight = (insight_override(ans.result)
                       if callable(insight_override) else insight_override)
    else:
        ans.insight = insights.generate_insight(question, ans.sql,
                                                ans.result, llm)
    ans.latency_s = time.time() - t0 + gen.latency_s
    return ans
