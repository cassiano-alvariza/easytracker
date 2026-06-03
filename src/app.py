"""
EasyTracker Flask application entry point.

This file is intentionally thin: it wires HTTP routes to three collaborators:
  - RefeicaoStore  → read/write meals in the user's session
  - NutricaoAIService → Gemini calls for macros and suggestions
  - PageRenderer   → build HTML responses

Run from the src/ directory:
    python app.py
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, redirect, request, session, url_for

# Load .env from project root (one level above src/).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from models import Macros
from services.nutricao_ai import NutricaoAIService
from store.refeicao_store import RefeicaoStore
from views.pages import PageRenderer

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-troque-no-env")

# Long-lived service objects: safe to reuse across requests (no per-user state).
nutricao_ai = NutricaoAIService.from_env()
pages = PageRenderer()


def _store() -> RefeicaoStore:
    """
    Build a store bound to the current user's Flask session.

    Called at the start of each route that needs meal data. Keeping this as a
    small factory makes it obvious where session access happens.
    """
    return RefeicaoStore(session)


@app.route("/")
def home():
    """Home: show today's calorie total and main navigation."""
    store = _store()
    return pages.render_home(store.totals())


@app.route("/sobre", methods=["GET", "POST"])
def sobre():
    """
    Add a meal manually.

    POST: send description to Gemini → save macros via RefeicaoStore.
    GET:  show the textarea form.
    """
    store = _store()

    if request.method == "POST":
        refe = request.form.get("ref", "")
        macros = nutricao_ai.estimate_macros(refe)
        store.add_from_text(refe, macros)
        return pages.render_meal_registered(refe, macros)

    return pages.render_add_meal_form()


@app.route("/contato/remover", methods=["POST"])
def remover_refeicao():
    """Remove one meal from today's history by its id."""
    store = _store()
    try:
        refeicao_id = int(request.form.get("id", 0))
    except (TypeError, ValueError):
        refeicao_id = 0
    store.remove(refeicao_id)
    return redirect(url_for("contato"))


@app.route("/contato")
def contato():
    """Daily summary: macro totals + meal list."""
    store = _store()
    return pages.render_daily_consumption(
        totais=store.totals(),
        refeicoes=store.list_all(),
        meal_count=store.count(),
    )


@app.route("/sugestao/registrar", methods=["POST"])
def registrar_sugestao():
    """
    Add a previously generated AI suggestion to the daily log.

    Macros arrive from hidden form fields (no second Gemini call).
    """
    store = _store()
    nome = request.form.get("nome", "Refeição sugerida")
    macros = Macros(
        proteinas=float(request.form["proteinas"]),
        carboidratos=float(request.form["carboidratos"]),
        gorduras=float(request.form["gorduras"]),
        calorias=float(request.form["calorias"]),
    )
    store.add_from_text(nome, macros)
    return pages.render_suggestion_registered(nome, macros)


@app.route("/sugestao", methods=["GET", "POST"])
def sugestao_page():
    """
    AI meal suggestion flow.

    POST: ask Gemini for a suggestion and show ingredients + macros.
    GET:  show the request form.
    """
    if request.method == "POST":
        pedido = request.form.get("pedido", "")
        sugestao = nutricao_ai.generate_suggestion(pedido)
        return pages.render_suggestion_result(sugestao)

    return pages.render_suggestion_form()


if __name__ == "__main__":
    app.run(debug=True)
