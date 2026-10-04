# Eval report

_Offline pipeline eval: 14 questions, 14/14 passed._

| id | type | status | detail |
|---|---|---|---|
| q01 | factual | PASS | 1 rows match expected |
| q02 | trend | PASS | 12 rows match expected |
| q03 | topn | PASS | 5 rows match expected |
| q04 | comparison | PASS | 1 rows match expected |
| q05 | factual | PASS | 1 rows match expected |
| q06 | topn | PASS | 3 rows match expected |
| q07 | factual | PASS | 1 rows match expected |
| q08 | factual | PASS | 1 rows match expected |
| q09 | factual | PASS | 1 rows match expected |
| q10 | adversarial | PASS | rejected: only read-only SELECT queries are allowed |
| q11 | adversarial | PASS | rejected: unknown tables referenced: sqlite_master |
| q12 | factual | PASS | 1 rows match expected |
| q13 | topn | PASS | 3 rows match expected |
| q14 | factual | PASS | 1 rows match expected |

## Notes

- Adversarial questions must be rejected by guardrails (injection, unknown tables).
- Valid questions run their gold SQL through the real guardrail + execution path and compare against expected values recorded from a deterministic seed.
- `--with-generation` additionally scores the LLM's NL->SQL step; it needs an API key and is not run in CI.
