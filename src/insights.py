"""Plain-language insights.

Takes the question, the SQL that was run, and a compact summary of the
results, and asks the LLM to write 2-3 sentences a non-technical person
would understand. Numbers are pre-computed so the model reports them
instead of inventing them.
"""
from src.execute import Result
from src.sqlgen import LLMClient


def _summarize(result: Result, max_rows: int = 10) -> str:
    lines = [f"colonnes: {', '.join(result.columns)}",
             f"lignes: {result.n_rows}"]
    for r in result.rows[:max_rows]:
        lines.append(", ".join(f"{k}={v}" for k, v in r.items()))
    if result.n_rows > max_rows:
        lines.append(f"... ({result.n_rows - max_rows} autres lignes)")
    return "\n".join(lines)


SYSTEM = """Tu es un analyste data. On te donne une question, la requête SQL
exécutée et un résumé des résultats. Écris 2-3 phrases en français qui
répondent à la question pour un non-technique : cite les chiffres clés,
dis ce qui est notable (hausse, baisse, écart), et ne rajoute rien qui
ne figure pas dans les résultats."""


def generate_insight(question: str, sql: str, result: Result,
                     llm: LLMClient | None = None) -> str:
    llm = llm or LLMClient()
    if not llm.enabled or result.n_rows == 0:
        return ""
    user = (f"Question : {question}\nSQL : {sql}\n"
            f"Résultats :\n{_summarize(result)}")
    text, _, _ = llm.complete(SYSTEM, user)
    return text.strip()
