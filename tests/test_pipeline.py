"""Pipeline tests. Run with: pytest tests/ -q

Guardrail tests and chart tests need no database; execution tests use
the sample DB (built by data/build_db.py).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from src.charts import ChartSpec, suggest
from src.execute import Result, execute
from src.guardrails import GuardrailError, check


# --- guardrails -----------------------------------------------------------
def test_rejects_drop():
    with pytest.raises(GuardrailError):
        check("DROP TABLE clients; --")


def test_rejects_multi_statement():
    with pytest.raises(GuardrailError):
        check("SELECT 1; SELECT 2")


def test_rejects_unknown_table():
    with pytest.raises(GuardrailError):
        check("SELECT * FROM sqlite_master")


def test_rejects_non_select():
    with pytest.raises(GuardrailError):
        check("UPDATE clients SET ville='Paris'")


def test_accepts_valid_select():
    q = check("SELECT ville, COUNT(*) FROM clients GROUP BY ville")
    assert "clients" in q.tables


def test_appends_limit():
    q = check("SELECT * FROM produits")
    assert "LIMIT" in q.sql.upper()


def test_allows_with_select():
    q = check(
        "WITH monthly AS ("
        " SELECT substr(date, 1, 7) AS m, COUNT(*) AS n FROM commandes"
        " GROUP BY m) "
        "SELECT m, n FROM monthly ORDER BY m")
    assert q.sql.upper().startswith("WITH")


# --- charts ---------------------------------------------------------------
def test_suggest_line_for_time_series():
    r = Result(columns=["mois", "ca"],
               rows=[{"mois": "2024-01", "ca": 100.0},
                     {"mois": "2024-02", "ca": 120.0}])
    assert suggest(r).kind == "line"


def test_suggest_bar_for_categories():
    r = Result(columns=["ville", "n"],
               rows=[{"ville": "Paris", "n": 10},
                     {"ville": "Lyon", "n": 7}])
    assert suggest(r).kind == "bar"


def test_suggest_table_for_empty():
    assert suggest(Result(columns=["a"], rows=[])).kind == "table"


# --- execution ------------------------------------------------------------
def _db():
    db = config.DB_PATH
    if not os.path.exists(db):
        from data.build_db import build
        build(db)
    return db


def test_execute_simple():
    res = execute(check("SELECT COUNT(*) AS n FROM clients"), _db())
    assert res.rows[0]["n"] == 800


def test_execute_revenue_positive():
    res = execute(check(
        "SELECT SUM(l.quantite * l.prix_unitaire) AS ca "
        "FROM lignes_commande l JOIN commandes c ON c.id = l.commande_id "
        "WHERE c.statut = 'livrée'"), _db())
    assert res.rows[0]["ca"] > 0
