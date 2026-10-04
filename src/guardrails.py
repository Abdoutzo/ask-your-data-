"""SQL guardrails.

Every generated query passes through here before it touches the database.
The rules are deliberately paranoid:

- exactly one statement, and it must be SELECT (WITH ... SELECT allowed)
- no writes, no DDL, no PRAGMA, no ATTACH, no multi-statements
- only allowlisted tables may be referenced
- a LIMIT is enforced (appended if missing)

Rejected queries raise GuardrailError with a human-readable reason, which
the UI shows instead of running anything.
"""
import re
from dataclasses import dataclass

import config

FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE|TRUNCATE|GRANT|"
    r"REVOKE|PRAGMA|ATTACH|DETACH|VACUUM|ANALYZE|EXPLAIN)\b",
    re.IGNORECASE,
)

TABLE_REF = re.compile(r"\b(?:FROM|JOIN)\s+([a-z_][a-z0-9_]*)", re.IGNORECASE)
HAS_LIMIT = re.compile(r"\bLIMIT\s+\d+", re.IGNORECASE)


class GuardrailError(ValueError):
    pass


@dataclass
class CheckedQuery:
    sql: str
    tables: list


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"--[^\n]*", " ", sql)
    return re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)


def check(sql: str) -> CheckedQuery:
    """Validate a generated query. Returns the (possibly LIMIT-amended)
    SQL or raises GuardrailError."""
    if not sql or not sql.strip():
        raise GuardrailError("empty query")
    cleaned = _strip_comments(sql).strip().rstrip(";").strip()

    if ";" in cleaned:
        raise GuardrailError("multiple statements are not allowed")
    if FORBIDDEN.search(cleaned):
        raise GuardrailError("only read-only SELECT queries are allowed")
    if not re.match(r"(?is)^\s*(WITH\b.*)?\s*SELECT\b", cleaned):
        raise GuardrailError("query must start with SELECT (or WITH ... SELECT)")

    tables = {m.group(1).lower() for m in TABLE_REF.finditer(cleaned)}
    # CTE names defined in a WITH clause are query-local, not real tables.
    cte_names = {m.group(1).lower() for m in
                 re.finditer(r"([a-z_][a-z0-9_]*)\s+AS\s*\(", cleaned,
                             re.IGNORECASE)}
    unknown = tables - config.ALLOWED_TABLES - cte_names
    if unknown:
        raise GuardrailError(
            f"unknown tables referenced: {', '.join(sorted(unknown))}")

    if not HAS_LIMIT.search(cleaned):
        cleaned += f" LIMIT {config.MAX_ROWS}"
    return CheckedQuery(sql=cleaned, tables=sorted(tables))
