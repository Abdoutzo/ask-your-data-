"""Safe query execution.

Runs a guardrail-checked query with a timeout and returns rows as a list
of dicts plus column names. Timeouts and errors become plain
ExecutionErrors — the agent turns them into "I couldn't answer that"
instead of tracebacks.
"""
import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List

import config
from src.guardrails import CheckedQuery


class ExecutionError(RuntimeError):
    pass


@dataclass
class Result:
    columns: List[str]
    rows: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def n_rows(self) -> int:
        return len(self.rows)

    def col_values(self, col: str) -> List[Any]:
        return [r[col] for r in self.rows]


def _timeout_handler(signum, frame):
    raise ExecutionError("query timed out")


def execute(checked: CheckedQuery, db_path: str = config.DB_PATH) -> Result:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        # sqlite3 has no per-query timeout; use progress handler as a
        # watchdog (checks every 10k VM ops, plenty granular here).
        import time
        deadline = time.time() + config.QUERY_TIMEOUT_S

        def watchdog():
            if time.time() > deadline:
                return 1
            return 0

        con.set_progress_handler(watchdog, 10000)
        try:
            cur = con.execute(checked.sql)
        except sqlite3.Error as e:
            raise ExecutionError(f"SQL error: {e}")
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = [dict(r) for r in cur.fetchall()]
        return Result(columns=columns, rows=rows)
    finally:
        con.close()
