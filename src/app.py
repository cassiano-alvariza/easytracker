"""
EasyTracker Flask application entry point.

Wires HTTP routes to three collaborators:
  - SQLiteRefeicaoStore → lê/escreve refeições no SQLite
  - NutricaoAIService   → chamadas ao Gemini para macros e sugestões
  - PageRenderer        → gera as respostas HTML

Segurança:
  - Flask-Login  → sessões de usuário e @login_required
  - Flask-WTF    → proteção CSRF em todos os formulários POST
  - Flask-Limiter → rate limiting no /login (5 tentativas/minuto)
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    redirect,
    request,
    stream_with_context,
    url_for,
)
from flask_login import current_user, login_required

from extensions import csrf, limiter, login_manager
from models import Macros
from services.nutricao_ai import NutricaoAIService
from store.db import close_db, get_db, init_db
from store.sqlite_refeicao_store import SQLiteRefeicaoStore
from store.usuario_store import UsuarioStore
from views.pages import PageRenderer

# Carrega o .env da raiz do projeto (um nível acima de src/).
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-troque-no-env")

# Segurança dos cookies de sessão.
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"

# Inicializa extensões.
csrf.init_app(app)
login_manager.init_app(app)
limiter.init_app(app)

# Cria as tabelas na primeira execução (operação idempotente + migração automática).
init_db()

# Fecha a conexão ao fim de cada request.
app.teardown_appcontext(close_db)

# Registra o blueprint de autenticação.
from auth import bp as auth_bp  # noqa: E402

app.register_blueprint(auth_bp)

# Objetos de longa vida: sem estado por usuário, seguros para reutilizar.
nutricao_ai = NutricaoAIService.from_env()
pages = PageRenderer()


@login_manager.user_loader
def load_user(user_id: str):
    """Flask-Login chama isso a cada request para recarregar o usuário da sessão."""
    return UsuarioStore(get_db()).buscar_por_id(int(user_id))


def _store() -> SQLiteRefeicaoStore:
    """Constrói um store vinculado ao usuário logado."""
    return SQLiteRefeicaoStore(get_db(), current_user.id)


# ---------------------------------------------------------------------------
# Rotas principais (todas protegidas por @login_required)
# ---------------------------------------------------------------------------


@app.route("/")
@login_required
def home():
    """Home: exibe o total de calorias do dia e a navegação principal."""
    return pages.render_home(_store().totals())


@app.route("/sobre", methods=["GET", "POST"])
@login_required
def sobre():
    """
    Registra uma refeição manualmente.

    POST: envia descrição ao Gemini → salva macros.
    GET:  exibe o formulário.
    """
    store = _store()
    if request.method == "POST":
        refe = request.form.get("ref", "")
        macros = nutricao_ai.estimate_macros(refe)
        store.add_from_text(refe, macros)
        return pages.render_meal_registered(refe, macros)
    return pages.render_add_meal_form()


@app.route("/contato/remover", methods=["POST"])
@login_required
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
@login_required
def contato():
    """Resumo diário: totais de macros + lista de refeições."""
    store = _store()
    return pages.render_daily_consumption(
        totais=store.totals(),
        refeicoes=store.list_all(),
        meal_count=store.count(),
    )


@app.route("/sugestao/registrar", methods=["POST"])
@login_required
def registrar_sugestao():
    """
    Adiciona uma sugestão da IA ao diário do dia.

    Os macros chegam via campos ocultos (sem segunda chamada ao Gemini).
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
@login_required
def sugestao_page():
    """
    Fluxo de sugestão de refeição via IA.

    POST: pede sugestão ao Gemini e exibe ingredientes + macros.
    GET:  exibe o formulário.
    """
    if request.method == "POST":
        pedido = request.form.get("pedido", "")
        sugestao = nutricao_ai.generate_suggestion(pedido)
        return pages.render_suggestion_result(sugestao)
    return pages.render_suggestion_form()


@app.route("/sugestao/stream", methods=["POST"])
@login_required
def sugestao_stream():
    """
    Stream da sugestão da IA em tempo real (consumido por JS no formulário).

    Envia o texto bruto do Gemini em chunks conforme chega; ao final, anexa
    <<<RESULT>>> + HTML renderizado para o front-end substituir o preview.
    """
    pedido = request.form.get("pedido", "")

    def gerar():
        partes = []
        for trecho in nutricao_ai.stream_suggestion_text(pedido):
            partes.append(trecho)
            yield trecho
        sugestao = nutricao_ai.parse_suggestion("".join(partes))
        yield "<<<RESULT>>>" + pages.suggestion_result_fragment(sugestao)

    return Response(
        stream_with_context(gerar()),
        mimetype="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


if __name__ == "__main__":
    app.run(debug=True)
