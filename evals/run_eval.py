"""Eval harness for the data analyst agent.

Runs fully offline (no LLM key needed) by feeding each question's gold
SQL through the real pipeline: guardrails -> execution -> chart
suggestion. Measures:

- guardrail rejection rate on adversarial questions (must be 100%)
- execution success on valid questions
- result match against expected values
- chart suggestion sanity (trend -> line)

Writes evals/report.md. With an LLM key, --with-generation also scores
the NL->SQL step (valid SQL produced, refusal on out-of-scope).

Usage:
    python evals/run_eval.py
    python evals/run_eval.py --with-generation   # needs LLM key
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from src import agent
from src.agent import ask
from src.charts import suggest
from src.execute import execute
from src.guardrails import GuardrailError, check
from src.sqlgen import LLMClient


def load_questions(path: str = "evals/questions.jsonl"):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _norm(rows):
    """Normalize rows for comparison (round floats, sort)."""
    out = []
    for r in rows:
        out.append(tuple(round(v, 2) if isinstance(v, float) else v
                         for v in r.values()))
    return sorted(out)


def run(with_generation: bool = False):
    questions = load_questions()
    db = config.DB_PATH
    llm = LLMClient()

    results = []
    for q in questions:
        row = {"id": q["id"], "type": q["type"], "question": q["question"]}
        if q["type"] == "adversarial":
            try:
                check(q["gold_sql"])
                row.update(status="FAIL", detail="adversarial SQL accepted!")
            except GuardrailError as e:
                row.update(status="PASS", detail=f"rejected: {e}")
        else:
            try:
                checked = check(q["gold_sql"])
            except GuardrailError as e:
                row.update(status="FAIL", detail=f"gold SQL rejected: {e}")
                results.append(row)
                continue
            try:
                res = execute(checked, db)
            except Exception as e:
                row.update(status="FAIL", detail=f"execution error: {e}")
                results.append(row)
                continue
            expected = [tuple(r) for r in q["expected"]]
            got = _norm(res.rows)
            exp = sorted(expected)
            if got == exp:
                row.update(status="PASS",
                           detail=f"{res.n_rows} rows match expected")
            else:
                row.update(status="FAIL",
                           detail=f"mismatch: got {got[:2]}, want {exp[:2]}")
            # chart sanity for the trend question
            if q["id"] == "q02":
                spec = suggest(res)
                row["chart"] = spec.kind
                if spec.kind != "line":
                    row.update(status="FAIL",
                               detail=f"expected line chart, got {spec.kind}")
        # optional: does the LLM generate valid SQL for this question?
        if with_generation and llm.enabled and q["type"] != "adversarial":
            ans = ask(q["question"], db, llm)
            row["gen_ok"] = bool(ans.sql and not ans.refused)
            try:
                if ans.sql:
                    check(ans.sql)
            except GuardrailError:
                row["gen_ok"] = False
        results.append(row)
    return results


def write_report(results, path: str = "evals/report.md"):
    passed = sum(1 for r in results if r["status"] == "PASS")
    lines = ["# Eval report",
             "",
             f"_Offline pipeline eval: {len(results)} questions, "
             f"{passed}/{len(results)} passed._",
             "",
             "| id | type | status | detail |",
             "|---|---|---|---|"]
    for r in results:
        extra = f" gen_ok={r['gen_ok']}" if "gen_ok" in r else ""
        lines.append(f"| {r['id']} | {r['type']} | {r['status']} | "
                     f"{r['detail']}{extra} |")
    lines += ["",
              "## Notes",
              "",
              "- Adversarial questions must be rejected by guardrails "
              "(injection, unknown tables).",
              "- Valid questions run their gold SQL through the real "
              "guardrail + execution path and compare against expected "
              "values recorded from a deterministic seed.",
              "- `--with-generation` additionally scores the LLM's NL->SQL "
              "step; it needs an API key and is not run in CI."]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"{passed}/{len(results)} passed — report written to {path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-generation", action="store_true")
    args = parser.parse_args()
    if args.with_generation and not LLMClient().enabled:
        print("warning: no LLM key, running offline evals only")
    results = run(with_generation=args.with_generation)
    for r in results:
        print(f"{r['id']:4} {r['status']:4} {r['detail']}")
    write_report(results)


if __name__ == "__main__":
    main()
