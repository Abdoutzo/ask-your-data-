# Quickstart

From zero to a working eval in about 5 minutes.

```bash
git clone https://github.com/Abdoutzo/ask-your-data
cd ask-your-data

python -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate on Windows

pip install -r requirements.txt
cp .env.example .env
```

## 1. Build the sample database

```bash
python data/build_db.py
```

Deterministic (seed=42): ~6 000 orders, 800 clients, 2023-2024.

## 2. Run the offline evals (no API key needed)

```bash
python evals/run_eval.py
```

Guardrail rejection tests, gold-SQL execution tests against expected
values, chart suggestion checks. Writes `evals/report.md`.

## 3. Unit tests

```bash
pytest tests/ -q
```

## 4. Try the demo

```bash
streamlit run app.py
```

Without an API key, SQL generation is disabled. Add one to `.env`:

```env
LLM_PROVIDER=mistral
MISTRAL_API_KEY=your_key_here
```

then ask questions in plain French and watch it write SQL, chart the
results, and explain them.
