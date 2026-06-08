"""
Rotas de autenticação: /cadastro, /login, /logout.
"""

from __future__ import annotations

from flask import redirect, request, url_for
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from auth import bp
from extensions import limiter
from store.db import get_db
from store.usuario_store import UsuarioStore
from views.pages import PageRenderer

pages = PageRenderer()

# ── helpers ──────────────────────────────────────────────────────────────────


def _calc_tmb(sexo: str, peso: float, altura: int, idade: int) -> float:
    """Mifflin-St Jeor: retorna a Taxa Metabólica Basal em kcal/dia."""
    base = 10 * peso + 6.25 * altura - 5 * idade
    return round(base + (5 if sexo == "M" else -161), 1)


def _form_fisica() -> dict:
    """Lê e retorna os campos físicos do formulário como strings brutas."""
    return {
        "sexo": request.form.get("sexo", "").strip(),
        "peso": request.form.get("peso", "").strip(),
        "altura": request.form.get("altura", "").strip(),
        "idade": request.form.get("idade", "").strip(),
        "objetivo": request.form.get("objetivo", "").strip(),
    }


# ── rotas ─────────────────────────────────────────────────────────────────────


@bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        conf = request.form.get("confirmacao", "")
        fis = _form_fisica()

        def erro(msg: str):
            return pages.render_register_form(erro=msg, nome=nome, email=email, **fis)

        # ── validações básicas ──
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            return erro("Email inválido.")
        if len(nome) < 2:
            return erro("Nome deve ter pelo menos 2 caracteres.")
        if len(senha) < 8:
            return erro("A senha deve ter pelo menos 8 caracteres.")
        if senha != conf:
            return erro("As senhas não coincidem.")

        # ── validações físicas ──
        try:
            peso = float(fis["peso"]) if fis["peso"] else None
            altura = int(fis["altura"]) if fis["altura"] else None
            idade = int(fis["idade"]) if fis["idade"] else None
        except ValueError:
            return erro("Dados físicos inválidos. Verifique peso, altura e idade.")

        if peso is not None and not (30 <= peso <= 300):
            return erro("Peso fora do intervalo (30–300 kg).")
        if altura is not None and not (100 <= altura <= 250):
            return erro("Altura fora do intervalo (100–250 cm).")
        if idade is not None and not (10 <= idade <= 100):
            return erro("Idade fora do intervalo (10–100 anos).")

        # ── TMB ──
        tmb = None
        if fis["sexo"] and peso and altura and idade:
            tmb = _calc_tmb(fis["sexo"], peso, altura, idade)

        # ── persistência ──
        usuario = UsuarioStore(get_db()).criar(
            email=email,
            nome=nome,
            senha_hash=generate_password_hash(senha),
            sexo=fis["sexo"],
            peso=peso,
            altura=altura,
            idade=idade,
            objetivo=fis["objetivo"],
            tmb=tmb,
        )
        if usuario is None:
            return erro("Este email já está cadastrado.")

        login_user(usuario, remember=True)
        return redirect(url_for("home"))

    return pages.render_register_form()


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        usuario = UsuarioStore(get_db()).buscar_por_email(email)
        senha_valida = (
            check_password_hash(usuario.senha_hash, senha)
            if usuario is not None
            else False
        )
        if not senha_valida:
            return pages.render_login_form(erro="Email ou senha incorretos.")

        login_user(usuario, remember=True)
        next_page = request.args.get("next", "")
        if not next_page or not next_page.startswith("/"):
            next_page = url_for("home")
        return redirect(next_page)

    return pages.render_login_form()


@bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
