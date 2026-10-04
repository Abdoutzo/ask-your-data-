"""Central configuration.

Everything tunable lives here and can be overridden with environment
variables (see .env.example). I got tired of hunting magic numbers
across files, so this is the single source of truth.
"""
import os


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


# --- embeddings -----------------------------------------------------------
EMBEDDING_MODEL = _env(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
)
# multilingual MPNet: decent French, small enough to run on a laptop.

# --- LLM ------------------------------------------------------------------
LLM_PROVIDER = _env("LLM_PROVIDER", "mistral")  # mistral | openai | none
MISTRAL_API_KEY = _env("MISTRAL_API_KEY", "")
MISTRAL_MODEL = _env("MISTRAL_MODEL", "mistral-large-latest")
OPENAI_API_KEY = _env("OPENAI_API_KEY", "")
OPENAI_MODEL = _env("OPENAI_MODEL", "gpt-4o-mini")

# --- retrieval ------------------------------------------------------------
CHUNK_STRATEGY = _env("CHUNK_STRATEGY", "recursive")  # fixed | recursive | semantic
TOP_K = _env_int("TOP_K", 5)
FIXED_CHUNK_SIZE = _env_int("FIXED_CHUNK_SIZE", 400)      # characters
FIXED_CHUNK_OVERLAP = _env_int("FIXED_CHUNK_OVERLAP", 60)
RECURSIVE_CHUNK_SIZE = _env_int("RECURSIVE_CHUNK_SIZE", 500)
SEMANTIC_BREAK_THRESHOLD = _env_float("SEMANTIC_BREAK_THRESHOLD", 0.75)

# --- eval -----------------------------------------------------------------
EVAL_CORPUS = _env("EVAL_CORPUS", "data/sample/contracts.json")
EVAL_QUESTIONS = _env("EVAL_QUESTIONS", "evals/questions.jsonl")
EVAL_REPORT = _env("EVAL_REPORT", "evals/report.md")

# Rough per-1k-token prices (USD), used for cost estimates in evals.
# Update when providers change pricing; these are approximations.
TOKEN_PRICES = {
    "mistral-large-latest": {"input": 0.002, "output": 0.006},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
}
