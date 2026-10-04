"""Schema introspection.

Turns the SQLite schema into a compact text block for the SQL-generation
prompt, plus a machine-readable description used by the chart picker.
"""
import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Column:
    name: str
    dtype: str


@dataclass
class Table:
    name: str
    columns: List[Column] = field(default_factory=list)


def inspect_schema(db_path: str) -> Dict[str, Table]:
    con = sqlite3.connect(db_path)
    tables = {}
    for (name,) in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
            " AND name NOT LIKE 'sqlite_%' ORDER BY name"):
        cols = [Column(n, t) for _, n, t, _, _, _ in
                con.execute(f"PRAGMA table_info({name})")]
        tables[name] = Table(name, cols)
    con.close()
    return tables


# Human notes the model can't infer from DDL alone. This is the kind of
# context a real analyst gets on day one; the agent deserves it too.
BUSINESS_NOTES = """
- Revenue = SUM(quantite * prix_unitaire) over lignes_commande, ONLY for
  commandes with statut = 'livrée'. 'annulée' and 'retournée' are excluded.
- Dates are TEXT in YYYY-MM-DD format; use substr(date, 1, 7) for months.
- Margin per line = (prix_unitaire - cout) * quantite (cout lives in produits).
- segment is 'Particulier' or 'Professionnel'.
"""


def schema_prompt_block(db_path: str) -> str:
    tables = inspect_schema(db_path)
    lines = []
    for t in tables.values():
        cols = ", ".join(f"{c.name} {c.dtype}" for c in t.columns)
        lines.append(f"- {t.name}({cols})")
    return "Tables:\n" + "\n".join(lines) + "\n" + BUSINESS_NOTES
