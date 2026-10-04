# ask-your-data

A natural-language data analyst: ask questions in plain French, get SQL, charts, and explanations back.

![demo walkthrough](assets/demo.svg)

## Why this exists

"Quel est le chiffre d'affaires par mois en 2024 ?" shouldn't require knowing SQL. This agent reads the database schema, generates the query, runs it through paranoid guardrails (SELECT-only, allowlisted tables, injection rejection), executes it, picks the right chart, and explains the result in plain language. The generated SQL is always shown — an analyst who can't show their work isn't an analyst.

The part I'm proudest of isn't the generation, it's the containment: every query passes through `src/guardrails.py` before touching the database, and `evals/` proves the adversarial cases get rejected.

## What it does

- **NL → SQL** via LLM, with schema + business rules in the prompt
- **Guardrails**: one statement, SELECT-only, known tables only, LIMIT enforced, comments stripped
- **Safe execution** with timeout, rows returned as dicts
- **Automatic charting**: time series → line, categories → bar, else table
- **Insights**: 2-3 plain-language sentences with the actual numbers
- **Graceful refusal** when the question is out of scope or no LLM key is set

## Results

Offline eval: 14 questions (12 valid + 2 adversarial), gold SQL through the real guardrail + execution path, deterministic database.

| check | result |
|---|---|
| adversarial rejection | 2/2 rejected (injection, unknown table) |
| valid execution | 12/12 executed |
| result match | 12/12 match expected values |
| chart sanity | trend question → line chart ✓ |

*Run `python evals/run_eval.py` to reproduce. `--with-generation` additionally scores the LLM's NL→SQL step (needs API key).*

## Architecture

```text
question (French)
   │  src/sqlgen.py — schema + business notes -> SQL (or NO_ANSWER)
   ▼
src/guardrails.py — SELECT-only, allowlisted tables, LIMIT enforced
   │
   ▼  src/execute.py (timeout, dict rows)
results ──► src/charts.py — line/bar/table heuristic -> Plotly
   │
   ▼  src/insights.py — plain-language summary with real numbers
answer: insight + chart + data + generated SQL (expandable)
```

## Quickstart

See [QUICKSTART.md](QUICKSTART.md). The short version:

```bash
pip install -r requirements.txt
python data/build_db.py
python evals/run_eval.py     # offline evals, no API key needed
streamlit run app.py         # demo UI: full NL mode with a key,
                             # verified-question demo mode without one
```

The demo above was recorded with `scripts/record_demo.py` (Playwright →
animated SVG), running the app with no API key: the curated questions use
verified SQL, everything else (guardrails, execution, charting) runs for real.

## Repo map

```text
src/schema.py      schema introspection + business notes for the prompt
src/sqlgen.py      NL -> SQL via LLM (NO_ANSWER on out-of-scope)
src/guardrails.py  paranoid SQL validation
src/execute.py     timeout-guarded execution
src/charts.py      deterministic chart suggestion + Plotly rendering
src/insights.py    plain-language summaries
src/agent.py       orchestrator: question -> answer
data/build_db.py   deterministic sample e-commerce database
evals/run_eval.py  offline harness; writes evals/report.md
app.py             Streamlit chat demo (Render-ready)
```

## Limitations (honest ones)

- SQL quality depends on the LLM; the evals measure everything *around* generation, and `--with-generation` measures generation itself when you have a key.
- The chart picker is a heuristic. It handles the common shapes; exotic result sets fall back to a table, which is the honest choice.
- Single-table-permission model: `ALLOWED_TABLES` is coarse. Row-level security is out of scope here.
- French-first prompts, like the RAG project. The pipeline is language-agnostic.

## License

MIT
