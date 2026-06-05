"""
EasyTracker Flask application entry point.

Wires HTTP routes to three collaborators:
  - SQLiteRefeicaoStore → lê/escreve refeições no SQLite
  - NutricaoAIService   → chamadas ao Gemini para macros e sugestões
  - PageRenderer        → gera as respostas HTML
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, redirect, request, session, url_for

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from store.sqlite_refeicao_store import SQLiteRefeicaoStore

from models import Macros
from services.nutricao_ai import NutricaoAIService
from store.db import close_db, get_db, init_db
from views.pages import PageRenderer

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-troque-no-env")

# Cria as tabelas na primeira execução (operação idempotente).
init_db()

# Registra o fechamento da conexão ao fim de cada request.
app.teardown_appcontext(close_db)

# Objetos de longa vida: sem estado por usuário, seguros para reutilizar.
nutricao_ai = NutricaoAIService.from_env()
pages = PageRenderer()


def _store() -> SQLiteRefeicaoStore:
    """
    Constrói um store vinculado ao UUID de sessão do usuário atual.

    O UUID é gerado uma vez por browser e gravado no cookie de sessão do Flask.
    Nunca lemos/escrevemos refeicoes diretamente na sessão — só via store.
    """
    if "sessao_id" not in session:
        session["sessao_id"] = str(uuid.uuid4())
    return SQLiteRefeicaoStore(get_db(), session["sessao_id"])


@app.route("/")
def home():
    """Home: exibe o total de calorias do dia e a navegação principal."""
    store = _store()
    return pages.render_home(store.totals())


@app.route("/sobre", methods=["GET", "POST"])
def sobre():
    """
    Registra uma refeição manualmente.

    POST: envia descrição ao Gemini → salva macros via SQLiteRefeicaoStore.
    GET:  exibe o formulário com textarea.
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
    """Remove uma refeição do histórico do dia pelo seu id."""
    store = _store()
    try:
        refeicao_id = int(request.form.get("id", 0))
    except (TypeError, ValueError):
        refeicao_id = 0
    store.remove(refeicao_id)
    return redirect(url_for("contato"))


@app.route("/contato")
def contato():
    """Resumo diário: totais de macros + lista de refeições."""
    store = _store()
    return pages.render_daily_consumption(
        totais=store.totals(),
        refeicoes=store.list_all(),
        meal_count=store.count(),
    )


@app.route("/sugestao/registrar", methods=["POST"])
def registrar_sugestao():
    """
    Adiciona uma sugestão da IA ao diário do dia.

    Os macros chegam via campos ocultos do formulário (sem segunda chamada ao Gemini).
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
    Fluxo de sugestão de refeição via IA.

    POST: pede sugestão ao Gemini e exibe ingredientes + macros.
    GET:  exibe o formulário de pedido.
    """
    if request.method == "POST":
        pedido = request.form.get("pedido", "")
        sugestao = nutricao_ai.generate_suggestion(pedido)
        return pages.render_suggestion_result(sugestao)

    return pages.render_suggestion_form()


if __name__ == "__main__":
    app.run(debug=True)
