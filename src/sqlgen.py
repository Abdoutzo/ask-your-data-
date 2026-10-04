"""Natural language -> SQL via LLM.

The prompt carries the schema, the business notes, and strict output
rules (SQL only, in a code fence). If the question is out of scope for
the database, the model must return the literal token NO_ANSWER instead
of inventing SQL — the agent turns that into a graceful refusal.
"""
import re
import time
from dataclasses import dataclass

import requests

import config
from src.schema import schema_prompt_block

SYSTEM = """Tu es un analyste data qui écrit du SQL (dialecte SQLite).
On te donne le schéma d'une base e-commerce et une question en français.
Règles :
- Réponds avec UNIQUEMENT la requête SQL dans un bloc ```sql, rien d'autre.
- SELECT uniquement (WITH ... SELECT autorisé). Aucune écriture.
- Utilise uniquement les tables du schéma.
- Si la question ne peut pas être répondue avec ces données, réponds exactement : NO_ANSWER.
- Dates au format texte YYYY-MM-DD ; mois = substr(date, 1, 7)."""

_CODE_FENCE = re.compile(r"```sql\s*(.*?)```", re.DOTALL | re.IGNORECASE)


@dataclass
class Generation:
    sql: str = ""
    refused: bool = False
    latency_s: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0


class LLMClient:
    """Minimal REST client (same shape as the RAG project's)."""

    def __init__(self, provider: str = config.LLM_PROVIDER):
        self.provider = provider
        if provider == "mistral":
            self.url = "https://api.mistral.ai/v1/chat/completions"
            self.key = config.MISTRAL_API_KEY
            self.model = config.MISTRAL_MODEL
        elif provider == "openai":
            self.url = "https://api.openai.com/v1/chat/completions"
            self.key = config.OPENAI_API_KEY
            self.model = config.OPENAI_MODEL
        elif provider == "none":
            self.url = self.key = self.model = ""
        else:
            raise ValueError(f"unknown LLM provider: {provider}")

    @property
    def enabled(self) -> bool:
        return self.provider != "none" and bool(self.key)

    def complete(self, system: str, user: str) -> tuple[str, int, int]:
        resp = requests.post(
            self.url,
            headers={"Authorization": f"Bearer {self.key}"},
            json={"model": self.model,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": user}],
                  "temperature": 0.0},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        usage = data.get("usage", {})
        return (data["choices"][0]["message"]["content"],
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0))

    def estimate_cost(self, pt: int, ct: int) -> float:
        prices = config.TOKEN_PRICES.get(self.model, {"input": 0, "output": 0})
        return pt / 1000 * prices["input"] + ct / 1000 * prices["output"]


def generate_sql(question: str, db_path: str = config.DB_PATH,
                 llm: LLMClient | None = None) -> Generation:
    llm = llm or LLMClient()
    if not llm.enabled:
        return Generation(refused=True)  # no key: can't generate, won't fake it
    prompt = schema_prompt_block(db_path) + f"\nQuestion : {question}"
    t0 = time.time()
    text, pt, ct = llm.complete(SYSTEM, prompt)
    latency = time.time() - t0
    if "NO_ANSWER" in text:
        return Generation(refused=True, latency_s=latency,
                          prompt_tokens=pt, completion_tokens=ct,
                          cost_usd=llm.estimate_cost(pt, ct))
    m = _CODE_FENCE.search(text)
    sql = m.group(1).strip() if m else text.strip()
    return Generation(sql=sql, latency_s=latency,
                      prompt_tokens=pt, completion_tokens=ct,
                      cost_usd=llm.estimate_cost(pt, ct))
