"""Build the sample e-commerce database (deterministic, seed=42).

Usage: python data/build_db.py [--out data/shop.db]

Tables: categories, produits, clients, commandes, lignes_commande.
~800 clients, 60 products, ~6 000 orders over 2023-2024.
Revenue = orders with statut='livrée' (annulée/retournée excluded).
"""
import argparse
import os
import random
import sqlite3
from datetime import date, timedelta

SEED = 42

CATEGORIES = ["Électronique", "Maison", "Mode", "Sport", "Livres"]

PRODUCTS = {
    "Électronique": [
        "Écouteurs Bluetooth Aura", "Montre connectée Pulse", "Enceinte portable Boom",
        "Clavier mécanique Pro", "Souris ergonomique", "Webcam HD Stream",
        "Disque SSD 1To", "Chargeur GaN 65W", "Tablette 10 pouces",
        "Casque réducteur de bruit", "Drone caméra 4K", "Liseuse e-ink",
    ],
    "Maison": [
        "Aspirateur robot CleanBot", "Machine à café Expresso", "Airfryer XL",
        "Lampadaire LED design", "Set de casseroles Inox", "Robot pâtissier",
        "Humidificateur d'air", "Tapis berbère 160x230", "Batterie cuisine 5 pièces",
        "Centrale vapeur", "Fauteuil scandinave", "Étagère murale chêne",
    ],
    "Mode": [
        "Veste en jean brut", "Sneakers blanches", "Manteau en laine",
        "Jean slim stretch", "Robe d'été fleurie", "Baskets running",
        "Sac à dos cuir", "Pull en cachemire", "Chemise oxford",
        "Bottines chelsea", "Écharpe en soie", "Montre classique acier",
    ],
    "Sport": [
        "Vélo électrique Urban", "Tapis de yoga pro", "Haltères 2x10kg",
        "Raquette de tennis", "Sac de sport 40L", "Montre GPS running",
        "Vélo d'appartement", "Gants de boxe", "Skateboard complet",
        "Tente 2 places", "Chaussures trail", "Corde à sauter connectée",
    ],
    "Livres": [
        "Roman « L'ombre du phare »", "BD « Les cités obscures »",
        "Guide « Cuisiner de saison »", "Essai « L'attention volée »",
        "Polar « Nuit blanche à Lyon »", "Manga tome 1 « Ronin »",
        "Livre photo « Alpes »", "Roman « Le dernier train »",
        "Guide de voyage « Japon »", "Bande dessinée « Solaris »",
        "Recueil de poésie « Aube »", "Thriller « La faille »",
    ],
}

CITIES = ["Paris", "Lyon", "Marseille", "Toulouse", "Bordeaux", "Lille",
          "Nantes", "Strasbourg", "Nice", "Montpellier", "Villeurbanne", "Rennes"]

FIRST = ["Léa", "Hugo", "Chloé", "Louis", "Emma", "Raphaël", "Jade", "Arthur",
         "Manon", "Jules", "Camille", "Adam", "Sarah", "Nathan", "Inès",
         "Mohamed", "Yasmine", "Karim", "Sofia", "Mehdi"]
LAST = ["Martin", "Bernard", "Dubois", "Moreau", "Laurent", "Simon", "Michel",
        "Garcia", "David", "Bertrand", "Roux", "Vincent", "Fournier", "Morel",
        "Girard", "Bonnet", "Dupont", "Lambert", "Fontaine", "Rousseau",
        "Benali", "Haddad", "Bensalem", "Kaci", "Traoré"]

SCHEMA = """
CREATE TABLE categories (id INTEGER PRIMARY KEY, nom TEXT NOT NULL);
CREATE TABLE produits (
    id INTEGER PRIMARY KEY, nom TEXT NOT NULL,
    categorie_id INTEGER NOT NULL REFERENCES categories(id),
    prix REAL NOT NULL, cout REAL NOT NULL);
CREATE TABLE clients (
    id INTEGER PRIMARY KEY, nom TEXT NOT NULL,
    ville TEXT NOT NULL, segment TEXT NOT NULL);
CREATE TABLE commandes (
    id INTEGER PRIMARY KEY, client_id INTEGER NOT NULL REFERENCES clients(id),
    date TEXT NOT NULL, statut TEXT NOT NULL);
CREATE TABLE lignes_commande (
    id INTEGER PRIMARY KEY,
    commande_id INTEGER NOT NULL REFERENCES commandes(id),
    produit_id INTEGER NOT NULL REFERENCES produits(id),
    quantite INTEGER NOT NULL, prix_unitaire REAL NOT NULL);
CREATE INDEX idx_commandes_date ON commandes(date);
CREATE INDEX idx_lignes_commande ON lignes_commande(commande_id);
"""


def build(db_path: str) -> None:
    rng = random.Random(SEED)
    if os.path.exists(db_path):
        os.remove(db_path)
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.executescript(SCHEMA)

    for i, cat in enumerate(CATEGORIES, start=1):
        cur.execute("INSERT INTO categories VALUES (?, ?)", (i, cat))

    pid = 1
    product_ids = []
    for ci, cat in enumerate(CATEGORIES, start=1):
        for name in PRODUCTS[cat]:
            prix = round(rng.uniform(9.99, 899.99), 2)
            cout = round(prix * rng.uniform(0.35, 0.6), 2)
            cur.execute(
                "INSERT INTO produits VALUES (?, ?, ?, ?, ?)",
                (pid, name, ci, prix, cout))
            product_ids.append(pid)
            pid += 1

    for i in range(1, 801):
        nom = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        ville = rng.choice(CITIES)
        segment = "Professionnel" if rng.random() < 0.18 else "Particulier"
        cur.execute("INSERT INTO clients VALUES (?, ?, ?, ?)",
                    (i, nom, ville, segment))

    # orders: growth in 2024, December peak, weekend dip
    start = date(2023, 1, 1)
    oid = 1
    for day in range(730):
        d = start + timedelta(days=day)
        year_boost = 1.35 if d.year == 2024 else 1.0
        month_boost = 1.8 if d.month == 12 else (0.7 if d.month == 8 else 1.0)
        weekend_dip = 0.6 if d.weekday() >= 5 else 1.0
        n = int(rng.uniform(4, 10) * year_boost * month_boost * weekend_dip)
        for _ in range(n):
            r = rng.random()
            statut = ("livrée" if r < 0.90
                      else "annulée" if r < 0.96 else "retournée")
            cur.execute(
                "INSERT INTO commandes VALUES (?, ?, ?, ?)",
                (oid, rng.randint(1, 800), d.isoformat(), statut))
            for _ in range(rng.randint(1, 4)):
                prod = rng.choice(product_ids)
                cur.execute("SELECT prix FROM produits WHERE id=?", (prod,))
                prix = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO lignes_commande (commande_id, produit_id, quantite, prix_unitaire)"
                    " VALUES (?, ?, ?, ?)",
                    (oid, prod, rng.randint(1, 3), prix))
            oid += 1

    con.commit()
    n_orders = cur.execute("SELECT COUNT(*) FROM commandes").fetchone()[0]
    revenue = cur.execute(
        "SELECT ROUND(SUM(l.quantite * l.prix_unitaire), 2) FROM lignes_commande l"
        " JOIN commandes c ON c.id = l.commande_id WHERE c.statut = 'livrée'"
    ).fetchone()[0]
    con.close()
    print(f"built {db_path}: {n_orders} orders, revenue(livrée) = {revenue} €")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/shop.db")
    args = parser.parse_args()
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    build(args.out)
