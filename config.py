"""Central configuration. Env-overridable, see .env.example."""
import os


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


# --- LLM ------------------------------------------------------------------
LLM_PROVIDER = _env("LLM_PROVIDER", "mistral")  # mistral | openai | none
MISTRAL_API_KEY = _env("MISTRAL_API_KEY", "")
MISTRAL_MODEL = _env("MISTRAL_MODEL", "mistral-large-latest")
OPENAI_API_KEY = _env("OPENAI_API_KEY", "")
OPENAI_MODEL = _env("OPENAI_MODEL", "gpt-4o-mini")

# --- database -------------------------------------------------------------
DB_PATH = _env("DB_PATH", "data/shop.db")

# --- safety ---------------------------------------------------------------
# Only these tables may appear in generated SQL.
ALLOWED_TABLES = {"categories", "produits", "clients", "commandes",
                  "lignes_commande"}
MAX_ROWS = _env_int("MAX_ROWS", 500)       # hard cap on returned rows
QUERY_TIMEOUT_S = _env_int("QUERY_TIMEOUT_S", 10)

# Rough per-1k-token prices (USD), for cost estimates.
TOKEN_PRICES = {
    "mistral-large-latest": {"input": 0.002, "output": 0.006},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
}
