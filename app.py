"""Streamlit demo: ask questions about the shop data in plain language.

Run locally:  streamlit run app.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

import config
from src import charts
from src.agent import ask
from src.demo import DEMO_QUESTIONS, get_demo, insight_for
from src.sqlgen import LLMClient

st.set_page_config(page_title="Ask your data — démo", layout="wide")
st.title("Posez vos questions à vos données")

llm = LLMClient()
demo_mode = not llm.enabled

with st.sidebar:
    st.header("Réglages")
    if demo_mode:
        st.caption("Base : boutique e-commerce fictive (2023-2024). "
                   "Mode démo sans clé API : les questions proposées sont "
                   "répondues avec des requêtes vérifiées ; ajoutez "
                   "MISTRAL_API_KEY ou OPENAI_API_KEY dans .env pour poser "
                   "vos propres questions en langage naturel.")
    else:
        st.caption("Base : boutique e-commerce fictive (2023-2024).")
    if st.button("Exemples de questions"):
        st.session_state["examples"] = True

if demo_mode:
    st.info("Pas de clé API : mode démo — choisissez une question "
            "vérifiée ci-dessous pour voir le pipeline complet "
            "(SQL → garde-fous → exécution → graphique).")

if st.session_state.get("examples"):
    st.markdown(
        "- Quel est le chiffre d'affaires total en 2024 ?\n"
        "- Quels sont les 5 produits les plus vendus en quantité ?\n"
        "- Quelle catégorie génère le plus de marge ?\n"
        "- Quel mois de 2024 a enregistré le plus de commandes livrées ?")

if demo_mode:
    labels = [d["question"] for d in DEMO_QUESTIONS]
    choice = st.selectbox("Question de démonstration", labels)
    demo = DEMO_QUESTIONS[labels.index(choice)]
    question = demo["question"]
    run = st.button("Analyser")
else:
    question = st.text_input("Votre question",
                             "Quel est le chiffre d'affaires par mois en 2024 ?")
    run = st.button("Analyser") and question
    demo = None

if run:
    # make sure the DB exists (first run / fresh deploy)
    if not os.path.exists(config.DB_PATH):
        with st.spinner("Création de la base de démonstration…"):
            from data.build_db import build
            build(config.DB_PATH)
    with st.spinner("Analyse en cours…"):
        if demo is not None:
            d = get_demo(demo["id"])
            ans = ask(d["question"], config.DB_PATH, llm,
                      sql_override=d["sql"],
                      insight_override=lambda r, d=d: insight_for(d, r))
        else:
            ans = ask(question, config.DB_PATH, llm)

    if ans.refused:
        st.warning(f"Je ne peux pas répondre : {ans.refusal_reason}")
    else:
        if ans.insight:
            st.subheader("Réponse")
            st.write(ans.insight)
        col1, col2 = st.columns([3, 2])
        with col1:
            fig = charts.render(ans.result, ans.chart)
            if fig is not None:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.dataframe(charts.to_display_rows(ans.result))
        with col2:
            st.subheader("Données")
            st.dataframe(charts.to_display_rows(ans.result), height=380)
        with st.expander("Voir le SQL généré"):
            st.code(ans.sql, language="sql")
        st.caption(f"Latence : {ans.latency_s:.2f}s"
                   + (f" · coût estimé : ${ans.cost_usd:.5f}"
                      if ans.cost_usd else ""))
