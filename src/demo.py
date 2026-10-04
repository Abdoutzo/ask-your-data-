"""Offline demo mode: curated questions answered without an LLM key.

The SQL below is the same gold SQL used by the eval harness, so it is
verified against the deterministic database. Only the generation and
insight steps are stubbed — guardrails, execution and charting run for
real, which is the honest way to demo the pipeline offline.
"""
from src.execute import Result


def _eur(x: float) -> str:
    return f"{x:,.2f}".replace(",", " ").replace(".", ",") + " \u20ac"


def _int(x: float) -> str:
    return f"{int(x):,}".replace(",", " ")


DEMO_QUESTIONS = [
    {
        "id": "ca-2024",
        "question": "Quel est le chiffre d'affaires total en 2024 ?",
        "sql": (
            "SELECT ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS ca "
            "FROM lignes_commande l JOIN commandes c ON c.id = l.commande_id "
            "WHERE c.statut = 'livr\u00e9e' AND substr(c.date, 1, 4) = '2024'"
        ),
        "insight": lambda r: (
            f"Le chiffre d'affaires des commandes livr\u00e9es en 2024 "
            f"s'\u00e9l\u00e8ve \u00e0 {_eur(r.rows[0]['ca'])}."
        ),
    },
    {
        "id": "ca-mois-2024",
        "question": "Quel est le chiffre d'affaires par mois en 2024 ?",
        "sql": (
            "SELECT substr(c.date, 1, 7) AS mois, "
            "ROUND(SUM(l.quantite * l.prix_unitaire), 2) AS ca "
            "FROM lignes_commande l JOIN commandes c ON c.id = l.commande_id "
            "WHERE c.statut = 'livr\u00e9e' AND substr(c.date, 1, 4) = '2024' "
            "GROUP BY mois ORDER BY mois"
        ),
        "insight": lambda r: (
            "Le chiffre d'affaires mensuel culmine en d\u00e9cembre 2024 "
            f"({_eur(r.rows[-1]['ca'])}), nettement au-dessus des autres mois "
            "\u2014 probablement l'effet des f\u00eates de fin d'ann\u00e9e."
        ),
    },
    {
        "id": "top-produits",
        "question": "Quels sont les 5 produits les plus vendus en quantit\u00e9 ?",
        "sql": (
            "SELECT p.nom, SUM(l.quantite) AS qte FROM lignes_commande l "
            "JOIN commandes c ON c.id = l.commande_id "
            "JOIN produits p ON p.id = l.produit_id "
            "WHERE c.statut = 'livr\u00e9e' "
            "GROUP BY p.nom ORDER BY qte DESC LIMIT 5"
        ),
        "insight": lambda r: (
            f"Le produit le plus vendu en quantit\u00e9 est "
            f"\u00ab {r.rows[0]['nom']} \u00bb ({_int(r.rows[0]['qte'])} unit\u00e9s), "
            f"devant \u00ab {r.rows[1]['nom']} \u00bb ({_int(r.rows[1]['qte'])})."
        ),
    },
    {
        "id": "marge-categorie",
        "question": "Quelle cat\u00e9gorie g\u00e9n\u00e8re le plus de marge ?",
        "sql": (
            "SELECT cat.nom AS categorie, "
            "ROUND(SUM((l.prix_unitaire - p.cout) * l.quantite), 2) AS marge "
            "FROM lignes_commande l JOIN commandes c ON c.id = l.commande_id "
            "JOIN produits p ON p.id = l.produit_id "
            "JOIN categories cat ON cat.id = p.categorie_id "
            "WHERE c.statut = 'livr\u00e9e' "
            "GROUP BY cat.nom ORDER BY marge DESC LIMIT 1"
        ),
        "insight": lambda r: (
            f"La cat\u00e9gorie \u00ab {r.rows[0]['categorie']} \u00bb g\u00e9n\u00e8re "
            f"la plus grosse marge : {_eur(r.rows[0]['marge'])}."
        ),
    },
    {
        "id": "panier-moyen",
        "question": "Quel est le panier moyen des commandes livr\u00e9es ?",
        "sql": (
            "SELECT ROUND(AVG(total), 2) AS panier_moyen FROM ("
            "SELECT SUM(l.quantite * l.prix_unitaire) AS total "
            "FROM lignes_commande l JOIN commandes c ON c.id = l.commande_id "
            "WHERE c.statut = 'livr\u00e9e' GROUP BY l.commande_id)"
        ),
        "insight": lambda r: (
            f"Le panier moyen des commandes livr\u00e9es est de "
            f"{_eur(r.rows[0]['panier_moyen'])}."
        ),
    },
    {
        "id": "taux-retours",
        "question": "Quel est le taux de commandes retourn\u00e9es (en %) ?",
        "sql": (
            "SELECT ROUND(100.0 * SUM(CASE WHEN statut = 'retourn\u00e9e' "
            "THEN 1 ELSE 0 END) / COUNT(*), 2) AS taux FROM commandes"
        ),
        "insight": lambda r: (
            f"{str(r.rows[0]['taux']).replace('.', ',')} % des commandes "
            "ont \u00e9t\u00e9 retourn\u00e9es."
        ),
    },
]


def get_demo(demo_id: str) -> dict:
    for d in DEMO_QUESTIONS:
        if d["id"] == demo_id:
            return d
    raise KeyError(f"unknown demo question: {demo_id}")


def insight_for(demo: dict, result: Result) -> str:
    fn = demo["insight"]
    return fn(result) if callable(fn) else str(fn)
