# Data

## Sample database (generated)

`data/shop.db` is **not** committed — it's generated deterministically
from `data/build_db.py` (seed=42):

```bash
python data/build_db.py
```

You get a French e-commerce database: 5 categories, 60 products,
800 clients, ~6 000 orders over 2023-2024. Because the seed is fixed,
every eval in `evals/` is reproducible.

Conventions the agent relies on (also in `src/schema.py`):
- Revenue = `SUM(quantite * prix_unitaire)` on `lignes_commande`,
  only for `commandes.statut = 'livrée'`.
- Margin per line = `(prix_unitaire - cout) * quantite`.
- Dates are TEXT `YYYY-MM-DD`; months via `substr(date, 1, 7)`.

## Using your own database

Point `DB_PATH` at any SQLite file and update `ALLOWED_TABLES` in
`config.py` plus the business notes in `src/schema.py`. The guardrails,
chart picker and eval pattern transfer as-is.
