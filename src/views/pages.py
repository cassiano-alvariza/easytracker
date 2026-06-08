"""
HTML page builder for EasyTracker.

PageRenderer turns domain data (Macros, Refeicao, SugestaoRefeicao) into
complete HTML strings. The app still uses server-rendered HTML (no Jinja
templates yet) to keep the refactor focused on structure, not templating.

Rules for this module:
  - No Gemini calls
  - No session reads/writes
  - Only presentation: CSS, escaping user input, layout fragments
"""

from __future__ import annotations

from html import escape

from flask import url_for

from models import Macros, Refeicao, SugestaoRefeicao


def _csrf_token() -> str:
    """Retorna o token CSRF atual (requer contexto de request)."""
    try:
        from flask_wtf.csrf import generate_csrf

        return generate_csrf()
    except Exception:
        return ""


# Global stylesheet embedded in every page. Kept as a module constant because
# it is static and shared by all PageRenderer methods.
ESTILOS = """
<style>
    :root {
        --bg: #0c1118;
        --surface: #151d2b;
        --surface-2: #1c2738;
        --border: rgba(255, 255, 255, 0.08);
        --text: #eef2f7;
        --muted: #8b9bb4;
        --accent: #3dd68c;
        --accent-dim: rgba(61, 214, 140, 0.15);
        --protein: #60a5fa;
        --carbs: #fbbf24;
        --fat: #f472b6;
        --calories: #fb923c;
        --radius: 16px;
        --shadow: 0 24px 48px rgba(0, 0, 0, 0.35);
    }

    * { box-sizing: border-box; margin: 0; padding: 0; }

    body {
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        background: var(--bg);
        color: var(--text);
        min-height: 100vh;
        line-height: 1.5;
    }

    body::before {
        content: "";
        position: fixed;
        inset: 0;
        background:
            radial-gradient(ellipse 80% 50% at 50% -20%, rgba(61, 214, 140, 0.12), transparent),
            radial-gradient(ellipse 60% 40% at 100% 50%, rgba(96, 165, 250, 0.06), transparent);
        pointer-events: none;
        z-index: 0;
    }

    .app {
        position: relative;
        z-index: 1;
        max-width: 520px;
        margin: 0 auto;
        padding: calc(2rem + env(safe-area-inset-top)) 1.25rem calc(3rem + env(safe-area-inset-bottom));
        min-height: 100vh;
        display: flex;
        flex-direction: column;
    }

    .brand {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        margin-bottom: 1.75rem;
    }

    .brand-icon {
        width: 42px;
        height: 42px;
        border-radius: 12px;
        background: linear-gradient(135deg, var(--accent), #22c55e);
        display: grid;
        place-items: center;
        font-size: 1.25rem;
        box-shadow: 0 8px 24px rgba(61, 214, 140, 0.35);
    }

    .brand h1 {
        font-size: 1.35rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    .brand span {
        display: block;
        font-size: 0.8rem;
        font-weight: 400;
        color: var(--muted);
    }

    .card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        padding: 1.75rem;
        box-shadow: var(--shadow);
        flex: 1;
        animation: fadeUp 0.45s ease-out;
    }

    @keyframes fadeUp {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .card h2 {
        font-size: 1.4rem;
        font-weight: 600;
        margin-bottom: 0.35rem;
        letter-spacing: -0.02em;
    }

    .subtitle {
        color: var(--muted);
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }

    .hero-cal {
        text-align: center;
        padding: 1.5rem 0 1.75rem;
        margin-bottom: 1.5rem;
        background: var(--accent-dim);
        border-radius: 12px;
        border: 1px solid rgba(61, 214, 140, 0.2);
    }

    .hero-cal .label {
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--muted);
        margin-bottom: 0.25rem;
    }

    .hero-cal .value {
        font-size: 3rem;
        font-weight: 700;
        color: var(--accent);
        line-height: 1;
        letter-spacing: -0.03em;
    }

    .hero-cal .unit {
        font-size: 1rem;
        color: var(--muted);
        font-weight: 500;
    }

    .actions {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
    }

    .btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 0.9rem 1.25rem;
        border-radius: 12px;
        font-family: inherit;
        font-size: 0.95rem;
        font-weight: 600;
        text-decoration: none;
        border: none;
        cursor: pointer;
        transition: transform 0.15s, box-shadow 0.15s, background 0.15s;
    }

    .btn:active { transform: scale(0.98); }

    .btn-primary {
        background: linear-gradient(135deg, var(--accent), #22c55e);
        color: #052e16;
        box-shadow: 0 8px 24px rgba(61, 214, 140, 0.3);
    }

    .btn-primary:hover {
        box-shadow: 0 12px 32px rgba(61, 214, 140, 0.4);
    }

    .btn-secondary {
        background: var(--surface-2);
        color: var(--text);
        border: 1px solid var(--border);
    }

    .btn-secondary:hover {
        background: #243044;
    }

    .btn-tertiary {
        background: transparent;
        color: var(--muted);
        border: 1px solid var(--border);
    }

    .btn-tertiary:hover {
        color: var(--text);
        border-color: var(--muted);
    }

    .ingredient-list {
        list-style: none;
        margin-bottom: 1rem;
    }

    .ingredient-list li {
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--border);
        color: var(--muted);
    }

    .ingredient-list li strong {
        color: var(--text);
    }

    .btn-row {
        display: flex;
        gap: 0.75rem;
        margin-top: 1.5rem;
        flex-wrap: wrap;
    }

    .btn-row .btn { flex: 1; min-width: 120px; }

    form { display: flex; flex-direction: column; gap: 1rem; }

    label {
        font-size: 0.85rem;
        font-weight: 500;
        color: var(--muted);
    }

    input, textarea {
        width: 100%;
        padding: 0.85rem 1rem;
        border-radius: 12px;
        border: 1px solid var(--border);
        background: var(--surface-2);
        color: var(--text);
        font-family: inherit;
        font-size: 1rem;
        transition: border-color 0.15s, box-shadow 0.15s;
    }

    input:focus, textarea:focus {
        outline: none;
        border-color: rgba(61, 214, 140, 0.5);
        box-shadow: 0 0 0 3px var(--accent-dim);
    }

    textarea {
        min-height: 100px;
        resize: vertical;
    }

    .macros {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.75rem;
        margin-top: 0.5rem;
    }

    .macro {
        background: var(--surface-2);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1rem;
        position: relative;
        overflow: hidden;
    }

    .macro::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
    }

    .macro--protein::before { background: var(--protein); }
    .macro--carbs::before { background: var(--carbs); }
    .macro--fat::before { background: var(--fat); }
    .macro--calories::before { background: var(--calories); }

    .macro .name {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--muted);
        margin-bottom: 0.35rem;
    }

    .macro .amount {
        font-size: 1.5rem;
        font-weight: 700;
        letter-spacing: -0.02em;
    }

    .macro .amount small {
        font-size: 0.85rem;
        font-weight: 500;
        color: var(--muted);
    }

    .success-icon {
        width: 56px;
        height: 56px;
        margin: 0 auto 1rem;
        border-radius: 50%;
        background: var(--accent-dim);
        border: 2px solid rgba(61, 214, 140, 0.4);
        display: grid;
        place-items: center;
        font-size: 1.75rem;
        animation: pop 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
    }

    @keyframes pop {
        from { transform: scale(0.5); opacity: 0; }
        to { transform: scale(1); opacity: 1; }
    }

    .meal-name {
        text-align: center;
        padding: 0.75rem 1rem;
        background: var(--surface-2);
        border-radius: 10px;
        margin: 1rem 0;
        font-style: italic;
        color: var(--muted);
    }

    .meal-name strong { color: var(--text); font-style: normal; }

    .text-center { text-align: center; }

    .meal-history {
        list-style: none;
        margin: 1.5rem 0 0;
    }

    .meal-entry {
        padding: 1rem 0;
        border-bottom: 1px solid var(--border);
    }

    .meal-entry:last-child { border-bottom: none; }

    .meal-entry-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 0.75rem;
        margin-bottom: 0.35rem;
    }

    .meal-entry-header strong {
        font-size: 0.95rem;
        line-height: 1.35;
        flex: 1;
    }

    .meal-entry-time {
        font-size: 0.8rem;
        color: var(--muted);
        white-space: nowrap;
    }

    .meal-entry-macros {
        font-size: 0.85rem;
        color: var(--muted);
        margin-bottom: 0.65rem;
    }

    .meal-entry-macros span { color: var(--calories); font-weight: 600; }

    .btn-remove {
        padding: 0.45rem 0.85rem;
        border-radius: 8px;
        font-family: inherit;
        font-size: 0.8rem;
        font-weight: 600;
        color: #fca5a5;
        background: rgba(248, 113, 113, 0.12);
        border: 1px solid rgba(248, 113, 113, 0.25);
        cursor: pointer;
        transition: background 0.15s;
    }

    .btn-remove:hover { background: rgba(248, 113, 113, 0.2); }

    .empty-history {
        padding: 1rem;
        text-align: center;
        color: var(--muted);
        background: var(--surface-2);
        border-radius: 10px;
        font-size: 0.9rem;
    }

    /* Barra de usuário logado */
    .user-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.5rem 0.75rem;
        margin-bottom: 1rem;
        background: var(--surface-2);
        border: 1px solid var(--border);
        border-radius: 10px;
        font-size: 0.85rem;
        color: var(--muted);
    }
    .user-bar span { font-weight: 500; color: var(--text); }
    .btn-logout {
        background: none;
        border: 1px solid var(--border);
        color: var(--muted);
        border-radius: 8px;
        padding: 0.25rem 0.65rem;
        font-size: 0.8rem;
        cursor: pointer;
        font-family: inherit;
    }
    .btn-logout:hover { border-color: var(--accent); color: var(--accent); }

    /* Mensagem de erro nos formulários de auth */
    .form-error {
        background: rgba(248, 113, 113, 0.12);
        border: 1px solid rgba(248, 113, 113, 0.35);
        color: #f87171;
        border-radius: 10px;
        padding: 0.65rem 0.85rem;
        font-size: 0.9rem;
        margin-bottom: 1rem;
    }
    .auth-footer {
        text-align: center;
        margin-top: 1.25rem;
        font-size: 0.875rem;
        color: var(--muted);
    }
    .auth-footer a { color: var(--accent); text-decoration: none; }

    /* Spinner de carregamento do streaming */
    .stream-spinner { display:flex; justify-content:center; gap:.5rem; padding:1.5rem 0; }
    .stream-spinner span { width:10px; height:10px; border-radius:50%; background:var(--accent); display:inline-block; animation:spbounce 1.1s ease-in-out infinite; }
    .stream-spinner span:nth-child(2) { animation-delay:.18s; }
    .stream-spinner span:nth-child(3) { animation-delay:.36s; }
    @keyframes spbounce { 0%,80%,100%{transform:scale(.2);opacity:.3} 40%{transform:scale(1);opacity:1} }

    /* ── Onboarding imersivo ── */
    .ob-progress-bar { height: 4px; background: var(--border); border-radius: 4px; margin-bottom: 1rem; overflow: hidden; }
    .ob-progress-fill { height: 100%; background: var(--accent); border-radius: 4px; transition: width 0.45s cubic-bezier(.4,0,.2,1); }
    .ob-dots { display: flex; gap: 0.5rem; justify-content: center; margin-bottom: 1.75rem; }
    .ob-dot { width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center; font-size: 0.75rem; font-weight: 700; background: var(--surface-2); border: 2px solid var(--border); color: var(--muted); transition: all 0.3s; }
    .ob-dot.active { background: var(--accent); border-color: var(--accent); color: #0c1118; transform: scale(1.15); }
    .ob-dot.done { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }
    .ob-step { display: none; }
    .ob-step.active { display: block; animation: fadeSlide 0.3s ease; }
    .ob-emoji { font-size: 2.75rem; text-align: center; margin-bottom: 0.5rem; }
    .ob-step h2 { text-align: center; margin-bottom: 0.25rem; }
    .ob-step .subtitle { text-align: center; margin-bottom: 1.25rem; }
    .ob-err { background: rgba(248,113,113,0.12); border: 1px solid rgba(248,113,113,0.35); color: #f87171; border-radius: 10px; padding: 0.6rem 0.85rem; font-size: 0.875rem; margin-bottom: 1rem; text-align: center; }
    .ob-nav { display: flex; gap: 0.75rem; margin-top: 1.25rem; }
    .ob-nav .btn { flex: 1; }
    .choice-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; margin-bottom: 1.1rem; }
    .choice-card { background: var(--surface-2); border: 2px solid var(--border); border-radius: 14px; padding: 1.1rem 0.75rem; text-align: center; cursor: pointer; transition: all 0.2s; font-weight: 500; font-size: 0.9rem; user-select: none; }
    .choice-card .cc-icon { font-size: 1.6rem; margin-bottom: 0.35rem; }
    .choice-card:hover { border-color: rgba(61,214,140,0.45); }
    .choice-card.selected { border-color: var(--accent); background: var(--accent-dim); color: var(--accent); }
    .goal-grid { display: flex; flex-direction: column; gap: 0.65rem; margin-bottom: 1rem; }
    .goal-card { background: var(--surface-2); border: 2px solid var(--border); border-radius: 14px; padding: 0.9rem 1.1rem; display: flex; align-items: center; gap: 0.9rem; cursor: pointer; transition: all 0.2s; user-select: none; }
    .goal-card:hover { border-color: rgba(61,214,140,0.45); }
    .goal-card.selected { border-color: var(--accent); background: var(--accent-dim); }
    .goal-card .gc-icon { font-size: 1.65rem; flex-shrink: 0; }
    .goal-card .gc-title { font-weight: 600; font-size: 0.9rem; }
    .goal-card .gc-desc { font-size: 0.78rem; color: var(--muted); margin-top: 0.1rem; }
    .tmb-box { background: var(--surface-2); border: 1px solid var(--border); border-radius: 20px; padding: 1.75rem; text-align: center; margin: 1.1rem 0; }
    .tmb-number { font-size: 3.25rem; font-weight: 700; color: var(--accent); line-height: 1; letter-spacing: -0.02em; }
    .tmb-unit { font-size: 0.875rem; color: var(--muted); margin-top: 0.3rem; }
    .tmb-tag { display: inline-block; background: var(--accent-dim); color: var(--accent); border-radius: 20px; padding: 0.3rem 0.85rem; font-size: 0.8rem; font-weight: 600; margin-top: 0.85rem; }
    .tmb-info { font-size: 0.85rem; color: var(--muted); text-align: center; margin-top: 0.85rem; line-height: 1.65; }
    @keyframes fadeSlide { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>
"""


class PageRenderer:
    """
    Builds full HTML pages and reusable UI fragments.

    Each public render_* method corresponds to one screen in the app.
    Private helpers (_fmt, _macro_cards, etc.) keep duplication low.
    """

    @staticmethod
    def _csrf_input() -> str:
        """Campo oculto com o token CSRF — inclusão obrigatória em todo POST."""
        return f'<input type="hidden" name="csrf_token" value="{_csrf_token()}">'

    def _user_bar(self) -> str:
        """Barra superior com nome do usuário e botão de logout."""
        try:
            from flask_login import current_user

            if current_user.is_authenticated:
                return f"""
        <div class="user-bar">
            <span>{escape(current_user.nome)}</span>
            <form action="/logout" method="POST" style="margin:0">
                {self._csrf_input()}
                <button type="submit" class="btn-logout">Sair</button>
            </form>
        </div>"""
        except Exception:
            pass
        return ""

    @staticmethod
    def _fmt(n: float) -> str:
        """Format numbers: integers without decimals, floats with one decimal."""
        return f"{n:.0f}" if n == int(n) else f"{n:.1f}"

    def render_page(self, conteudo: str, mostrar_brand: bool = True) -> str:
        """
        Wrap arbitrary inner HTML in the shared layout (head, brand, card).

        All screens call this so structure and CSS stay consistent.
        """
        brand = (
            """
        <header class="brand">
            <div class="brand-icon">🥗</div>
            <div>
                <h1>EasyTracker <span>nutrição do dia</span></h1>
            </div>
        </header>
        """
            if mostrar_brand
            else ""
        )

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EasyTracker</title>
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="EasyTracker">
    <meta name="theme-color" content="#3dd68c">
    <link rel="manifest" href="/static/manifest.json">
    <link rel="apple-touch-icon" href="/static/icon-192.png">
    {ESTILOS}
</head>
<body>
    <div class="app">
        {brand}
        {self._user_bar()}
        <main class="card">{conteudo}</main>
    </div>
</body>
</html>"""

    def _macro_cards(self, macros: Macros) -> str:
        """Four-card grid showing P / C / F / kcal."""
        return f"""
        <div class="macros">
            <div class="macro macro--protein">
                <div class="name">Proteínas</div>
                <div class="amount">{self._fmt(macros.proteinas)} <small>g</small></div>
            </div>
            <div class="macro macro--carbs">
                <div class="name">Carboidratos</div>
                <div class="amount">{self._fmt(macros.carboidratos)} <small>g</small></div>
            </div>
            <div class="macro macro--fat">
                <div class="name">Gorduras</div>
                <div class="amount">{self._fmt(macros.gorduras)} <small>g</small></div>
            </div>
            <div class="macro macro--calories">
                <div class="name">Calorias</div>
                <div class="amount">{self._fmt(macros.calorias)} <small>kcal</small></div>
            </div>
        </div>
        """

    def _meal_history_list(self, refeicoes: list[Refeicao]) -> str:
        """
        Render the daily meal list with remove buttons.

        Must run inside a Flask request context because it calls url_for().
        """
        if not refeicoes:
            return (
                '<p class="empty-history">Nenhuma refeição registrada hoje. '
                "Adicione uma para ver o histórico aqui.</p>"
            )

        itens = []
        # Newest meals first in the UI (reverse chronological).
        for refeicao in reversed(refeicoes):
            texto = escape(refeicao.texto)
            horario = escape(refeicao.horario)
            cal = self._fmt(refeicao.calorias)
            p = self._fmt(refeicao.proteinas)
            c = self._fmt(refeicao.carboidratos)
            g = self._fmt(refeicao.gorduras)
            itens.append(
                f"""
            <li class="meal-entry">
                <div class="meal-entry-header">
                    <strong>{texto}</strong>
                    <span class="meal-entry-time">{horario}</span>
                </div>
                <p class="meal-entry-macros">
                    <span>{cal} kcal</span>
                    · P {p}g · C {c}g · G {g}g
                </p>
                <form action="{url_for("remover_refeicao")}" method="POST">
                    {self._csrf_input()}
                    <input type="hidden" name="id" value="{refeicao.id}">
                    <button type="submit" class="btn-remove">Remover</button>
                </form>
            </li>
            """
            )
        return f'<ul class="meal-history">{"".join(itens)}</ul>'

    def _ingredient_list(
        self,
        ingredientes: list[str],
        quantidades: list[str],
    ) -> str:
        """Bullet list for AI suggestion ingredients and amounts."""
        if not ingredientes:
            return "<p class='subtitle'>—</p>"
        itens = []
        for i, ing in enumerate(ingredientes):
            qtd = quantidades[i] if i < len(quantidades) else "—"
            itens.append(f"<li><strong>{escape(ing)}</strong> — {escape(qtd)}</li>")
        return f"<ul class='ingredient-list'>{''.join(itens)}</ul>"

    def _register_suggestion_form(self, sugestao: SugestaoRefeicao) -> str:
        """
        Hidden-field form to add an AI suggestion to the daily log.

        Macros travel as hidden inputs so we do not call Gemini again on submit.
        """
        m = sugestao.macros
        return f"""
        <form action="/sugestao/registrar" method="POST" style="margin-top: 1rem;">
            {self._csrf_input()}
            <input type="hidden" name="nome" value="{escape(sugestao.nome)}">
            <input type="hidden" name="proteinas" value="{m.proteinas}">
            <input type="hidden" name="carboidratos" value="{m.carboidratos}">
            <input type="hidden" name="gorduras" value="{m.gorduras}">
            <input type="hidden" name="calorias" value="{m.calorias}">
            <button type="submit" class="btn btn-primary" style="width: 100%;">
                ➕ Adicionar ao consumo do dia
            </button>
        </form>
        """

    def render_home(self, totais: Macros) -> str:
        """Landing page: daily calorie hero + navigation buttons."""
        return self.render_page(f"""
        <h2>Bem-vindo</h2>
        <p class="subtitle">Acompanhe o que você comeu hoje em um só lugar.</p>
        <div class="hero-cal">
            <div class="label">Consumo calórico do dia</div>
            <div class="value">{self._fmt(totais.calorias)}</div>
            <div class="unit">kcal</div>
        </div>
        <div class="actions">
            <a href="/sobre" class="btn btn-primary">➕ Adicionar refeição</a>
            <a href="/contato" class="btn btn-secondary">📊 Ver consumo nutricional</a>
            <a href="/sugestao" class="btn btn-tertiary">Sugerir refeição</a>
        </div>
        """)

    def render_add_meal_form(self) -> str:
        """GET form: user describes what they ate in free text."""
        return self.render_page(f"""
        <h2>Adicionar refeição</h2>
        <p class="subtitle">Descreva o que você comeu — a IA estima os macros.</p>
        <form action="/sobre" method="POST">
            {self._csrf_input()}
            <div>
                <label for="refeicao">O que você comeu?</label>
                <textarea id="refeicao" name="ref"
                    placeholder="Ex.: 2 ovos mexidos, pão integral e café com leite"
                    required></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Registrar refeição</button>
        </form>
        <div class="btn-row">
            <a href="/" class="btn btn-secondary">← Voltar ao início</a>
        </div>
        """)

    def render_meal_registered(self, texto: str, macros: Macros) -> str:
        """Success screen after logging a meal manually."""
        texto_safe = escape(texto)
        return self.render_page(f"""
            <div class="text-center">
                <div class="success-icon">✓</div>
                <h2>Refeição registrada</h2>
                <p class="subtitle">Os valores foram somados ao seu dia.</p>
            </div>
            <p class="meal-name"><strong>{texto_safe}</strong></p>
            <p class="subtitle" style="margin-bottom: 0.75rem;">Valores desta refeição:</p>
            {self._macro_cards(macros)}
            <div class="btn-row">
                <a href="/sobre" class="btn btn-primary">Adicionar outra</a>
                <a href="/" class="btn btn-secondary">Início</a>
            </div>
        """)

    def render_daily_consumption(
        self,
        totais: Macros,
        refeicoes: list[Refeicao],
        meal_count: int,
    ) -> str:
        """Summary page: daily totals + scrollable meal history."""
        if meal_count == 1:
            subtitulo = "Totais de 1 refeição registrada hoje."
        elif meal_count:
            subtitulo = f"Totais de {meal_count} refeições registradas hoje."
        else:
            subtitulo = "Totais acumulados de todas as refeições registradas."

        return self.render_page(f"""
        <h2>Consumo do dia</h2>
        <p class="subtitle">{subtitulo}</p>
        {self._macro_cards(totais)}
        <p class="subtitle" style="margin-top: 1.5rem; margin-bottom: 0.5rem;">
            Histórico do dia
        </p>
        {self._meal_history_list(refeicoes)}
        <div class="btn-row">
            <a href="/sobre" class="btn btn-primary">Adicionar refeição</a>
            <a href="/" class="btn btn-secondary">Início</a>
        </div>
        """)

    def render_suggestion_form(self) -> str:
        """
        GET form: user asks the AI for a meal idea.

        Progressive enhancement: with JS enabled the form streams the response
        live via /sugestao/stream; without JS it falls back to a normal POST
        to /sugestao.
        """
        return self.render_page(
            """
        <h2>Sugerir refeição</h2>
        <p class="subtitle">Descreva o que você quer — a IA monta uma sugestão.</p>
        <form id="sugestao-form" action="/sugestao" method="POST">
            __CSRF__""".replace("__CSRF__", self._csrf_input())
            + """
            <div>
                <label for="pedido">O que você está buscando?</label>
                <textarea id="pedido" name="pedido"
                    placeholder="Ex.: algo leve e rico em proteína para o almoço"
                    required></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Gerar sugestão</button>
        </form>
        <div id="sugestao-output" style="display:none; margin-top:1rem;">
            <p class="subtitle" id="sugestao-status">Gerando sugestão…</p>
            <div id="sugestao-live" class="stream-spinner">
                <span></span><span></span><span></span>
            </div>
        </div>
        <div class="btn-row">
            <a href="/" class="btn btn-secondary">← Voltar ao início</a>
        </div>
        <script>
        (function () {
            var form = document.getElementById('sugestao-form');
            var out = document.getElementById('sugestao-output');
            var status = document.getElementById('sugestao-status');
            var live = document.getElementById('sugestao-live');
            var SENTINEL = '<<<RESULT>>>';

            // Sem fetch/streams disponíveis: deixa o POST tradicional acontecer.
            if (!window.fetch || !window.ReadableStream) return;

            form.addEventListener('submit', function (e) {
                e.preventDefault();
                var pedido = form.pedido.value.trim();
                if (!pedido) return;

                var btn = form.querySelector('button');
                btn.disabled = true;
                out.style.display = 'block';
                status.textContent = 'Gerando sugestão…';
                live.textContent = '';

                var csrfInput = form.querySelector('input[name="csrf_token"]');
                var csrfToken = csrfInput ? csrfInput.value : '';
                fetch('/sugestao/stream', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                    body: new URLSearchParams({pedido: pedido, csrf_token: csrfToken})
                }).then(function (resp) {
                    var reader = resp.body.getReader();
                    var decoder = new TextDecoder();
                    var buffer = '';

                    function pump() {
                        return reader.read().then(function (result) {
                            if (result.done) {
                                var done = buffer.indexOf(SENTINEL);
                                if (done !== -1) {
                                    status.textContent = '';
                                    out.innerHTML = buffer.slice(done + SENTINEL.length);
                                } else {
                                    status.textContent =
                                        'Não foi possível gerar a sugestão. Tente novamente.';
                                    btn.disabled = false;
                                }
                                return;
                            }
                            buffer += decoder.decode(result.value, {stream: true});
                                    // chunks são JSON parcial — não exibimos diretamente
                                    return pump();
                        });
                    }
                    return pump();
                }).catch(function () {
                    // Falha de rede no stream: recarrega via POST tradicional.
                    form.submit();
                });
            });
        })();
        </script>
        """
        )

    def suggestion_result_fragment(self, sugestao: SugestaoRefeicao) -> str:
        """
        Inner HTML for an AI suggestion result.

        Reused by the full-page render and by the streaming route, which injects
        this fragment into the page once generation finishes.
        """
        return f"""
            <h2>Sugestão de refeição</h2>
            <p class="subtitle">Sugestão gerada com base no seu pedido.</p>
            <p class="meal-name"><strong>{escape(sugestao.nome)}</strong></p>
            <p class="subtitle" style="margin-bottom: 0.75rem;">Ingredientes:</p>
            {self._ingredient_list(sugestao.ingredientes, sugestao.quantidades)}
            <p class="subtitle" style="margin-bottom: 0.75rem;">Fator nutricional estimado:</p>
            {self._macro_cards(sugestao.macros)}
            {self._register_suggestion_form(sugestao)}
            <div class="btn-row">
                <a href="/sugestao" class="btn btn-secondary">Sugerir outra</a>
                <a href="/" class="btn btn-secondary">Início</a>
            </div>
        """

    def render_suggestion_result(self, sugestao: SugestaoRefeicao) -> str:
        """Shows AI suggestion with option to add it to the daily log."""
        return self.render_page(self.suggestion_result_fragment(sugestao))

    def render_suggestion_registered(self, nome: str, macros: Macros) -> str:
        """Success screen after adding an AI suggestion to the daily log."""
        return self.render_page(f"""
            <div class="text-center">
                <div class="success-icon">✓</div>
                <h2>Adicionado ao consumo do dia</h2>
                <p class="subtitle">Os macros da sugestão foram somados aos seus totais.</p>
            </div>
            <p class="meal-name"><strong>{escape(nome)}</strong></p>
            <p class="subtitle" style="margin-bottom: 0.75rem;">Valores registrados:</p>
            {self._macro_cards(macros)}
            <div class="btn-row">
                <a href="/contato" class="btn btn-primary">Ver consumo do dia</a>
                <a href="/" class="btn btn-secondary">Início</a>
            </div>
        """)

    def render_login_form(self, erro: str | None = None) -> str:
        """Página de login."""
        erro_html = f'<p class="form-error">{escape(erro)}</p>' if erro else ""
        return self.render_page(
            f"""
        <h2>Entrar</h2>
        <p class="subtitle">Acesse sua conta do EasyTracker.</p>
        {erro_html}
        <form action="/login" method="POST">
            {self._csrf_input()}
            <div>
                <label for="email">Email</label>
                <input id="email" name="email" type="email"
                    placeholder="seu@email.com" required autocomplete="email">
            </div>
            <div>
                <label for="senha">Senha</label>
                <input id="senha" name="senha" type="password"
                    placeholder="••••••••" required autocomplete="current-password">
            </div>
            <button type="submit" class="btn btn-primary" style="width:100%">
                Entrar
            </button>
        </form>
        <p class="auth-footer">
            Não tem conta?
            <a href="/cadastro">Criar conta</a>
        </p>
        """,
            mostrar_brand=True,
        )

    def render_register_form(
        self,
        erro: str | None = None,
        nome: str = "",
        email: str = "",
        sexo: str = "",
        peso: str = "",
        altura: str = "",
        idade: str = "",
        objetivo: str = "",
    ) -> str:
        """Onboarding imersivo e gamificado em 4 passos + resultado de TMB."""
        erro_html = f'<div class="ob-err">{escape(erro)}</div>' if erro else ""
        # Usamos .replace() em vez de f-string para não precisar escapar
        # todas as chaves {{ }} do JavaScript embutido.
        html = """
<div>
  <!-- Cabeçalho / logo -->
  <div style="display:flex;align-items:center;gap:0.6rem;margin-bottom:1.5rem;">
    <div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,var(--accent),#22c55e);display:grid;place-items:center;font-size:1.1rem;box-shadow:0 6px 20px rgba(61,214,140,.3);">&#x1F957;</div>
    <span style="font-weight:700;font-size:1.05rem;">EasyTracker</span>
  </div>

  <!-- Barra de progresso -->
  <div class="ob-progress-bar"><div class="ob-progress-fill" id="ob-fill" style="width:25%"></div></div>
  <div class="ob-dots">
    <span class="ob-dot active" id="dot-1">1</span>
    <span class="ob-dot" id="dot-2">2</span>
    <span class="ob-dot" id="dot-3">3</span>
    <span class="ob-dot" id="dot-4">4</span>
  </div>

  <form id="ob-form" action="/cadastro" method="POST" novalidate>
    [[CSRF]]

    <!-- Passo 1: conta -->
    <div class="ob-step active" id="ob-step-1">
      <div class="ob-emoji">&#x1F44B;</div>
      <h2>Vamos começar!</h2>
      <p class="subtitle">Crie sua conta para monitorar sua nutrição.</p>
      [[ERRO]]
      <div><label>Nome</label>
        <input name="nome" type="text" placeholder="Seu nome" id="ob-nome"
          autocomplete="name" value="[[NOME]]">
      </div>
      <div><label>Email</label>
        <input name="email" type="email" placeholder="seu@email.com" id="ob-email"
          autocomplete="email" value="[[EMAIL]]">
      </div>
      <div><label>Senha</label>
        <input name="senha" type="password" placeholder="Mínimo 8 caracteres"
          id="ob-senha" autocomplete="new-password">
      </div>
      <div><label>Confirmar senha</label>
        <input name="confirmacao" type="password" placeholder="Repita a senha"
          id="ob-conf" autocomplete="new-password">
      </div>
      <div id="err-1" class="ob-err" style="display:none"></div>
      <button type="button" class="btn btn-primary" style="width:100%;margin-top:.5rem"
        onclick="nextStep(1)">Próximo &#x2192;</button>
      <p class="auth-footer">Já tem conta? <a href="/login">Entrar</a></p>
    </div>

    <!-- Passo 2: sobre você -->
    <div class="ob-step" id="ob-step-2">
      <div class="ob-emoji">&#x1F9EC;</div>
      <h2>Sobre você</h2>
      <p class="subtitle">Para personalizar seus cálculos nutricionais.</p>
      <label style="display:block;margin-bottom:.5rem;font-size:.85rem;font-weight:500;color:var(--muted)">Sexo biológico</label>
      <div class="choice-grid">
        <div class="choice-card" id="card-M" data-value="M" onclick="selCard(this,'sexo')">
          <div class="cc-icon">&#x2642;&#xFE0F;</div>Masculino
        </div>
        <div class="choice-card" id="card-F" data-value="F" onclick="selCard(this,'sexo')">
          <div class="cc-icon">&#x2640;&#xFE0F;</div>Feminino
        </div>
      </div>
      <input type="hidden" name="sexo" id="input-sexo" value="[[SEXO]]">
      <div><label>Idade</label>
        <input name="idade" type="number" min="10" max="100"
          placeholder="Ex.: 28" id="ob-idade" value="[[IDADE]]">
      </div>
      <div id="err-2" class="ob-err" style="display:none"></div>
      <div class="ob-nav">
        <button type="button" class="btn btn-secondary" onclick="goStep(1)">&#x2190; Voltar</button>
        <button type="button" class="btn btn-primary" onclick="nextStep(2)">Próximo &#x2192;</button>
      </div>
    </div>

    <!-- Passo 3: corpo -->
    <div class="ob-step" id="ob-step-3">
      <div class="ob-emoji">&#x1F4CF;</div>
      <h2>Seu corpo</h2>
      <p class="subtitle">Para calcular seu metabolismo basal.</p>
      <div><label>Peso atual (kg)</label>
        <input name="peso" type="number" min="30" max="300" step="0.1"
          placeholder="Ex.: 75.5" id="ob-peso" value="[[PESO]]">
      </div>
      <div><label>Altura (cm)</label>
        <input name="altura" type="number" min="100" max="250"
          placeholder="Ex.: 175" id="ob-altura" value="[[ALTURA]]">
      </div>
      <div id="err-3" class="ob-err" style="display:none"></div>
      <div class="ob-nav">
        <button type="button" class="btn btn-secondary" onclick="goStep(2)">&#x2190; Voltar</button>
        <button type="button" class="btn btn-primary" onclick="nextStep(3)">Próximo &#x2192;</button>
      </div>
    </div>

    <!-- Passo 4: objetivo -->
    <div class="ob-step" id="ob-step-4">
      <div class="ob-emoji">&#x1F3AF;</div>
      <h2>Qual é seu objetivo?</h2>
      <p class="subtitle">Isso vai guiar suas metas diárias.</p>
      <div class="goal-grid">
        <div class="goal-card" data-value="emagrecer" onclick="selCard(this,'objetivo')">
          <div class="gc-icon">&#x1F525;</div>
          <div><div class="gc-title">Emagrecer</div><div class="gc-desc">Déficit calórico</div></div>
        </div>
        <div class="goal-card" data-value="manter" onclick="selCard(this,'objetivo')">
          <div class="gc-icon">&#x2696;&#xFE0F;</div>
          <div><div class="gc-title">Manter peso</div><div class="gc-desc">Equilíbrio calórico</div></div>
        </div>
        <div class="goal-card" data-value="massa" onclick="selCard(this,'objetivo')">
          <div class="gc-icon">&#x1F4AA;</div>
          <div><div class="gc-title">Ganhar massa</div><div class="gc-desc">Superávit calórico</div></div>
        </div>
      </div>
      <input type="hidden" name="objetivo" id="input-objetivo" value="[[OBJETIVO]]">
      <div id="err-4" class="ob-err" style="display:none"></div>
      <div class="ob-nav">
        <button type="button" class="btn btn-secondary" onclick="goStep(3)">&#x2190; Voltar</button>
        <button type="button" class="btn btn-primary" onclick="nextStep(4)">Ver resultado &#x2192;</button>
      </div>
    </div>

    <!-- Resultado: TMB -->
    <div class="ob-step" id="ob-step-result">
      <div class="ob-emoji">&#x1F389;</div>
      <h2>Seu metabolismo basal</h2>
      <p class="subtitle">Calculado especialmente para você.</p>
      <div class="tmb-box">
        <div class="tmb-number" id="tmb-val">0</div>
        <div class="tmb-unit">kcal / dia</div>
        <div class="tmb-tag" id="tmb-tag"></div>
      </div>
      <p class="tmb-info" id="tmb-info"></p>
      <div class="ob-nav">
        <button type="button" class="btn btn-secondary" onclick="goStep(4)">&#x2190; Voltar</button>
        <button type="submit" class="btn btn-primary">Começar agora &#x1F680;</button>
      </div>
    </div>

  </form>
</div>

<script>
var obCur = 1;
var STEPS = 4;

function goStep(n) {
  var prev = (n === 'result') ? null : document.getElementById('ob-step-' + obCur);
  if (prev) prev.classList.remove('active');
  if (n === 'result') {
    document.getElementById('ob-step-result').classList.add('active');
    setProgress(STEPS, true);
  } else {
    document.getElementById('ob-step-' + n).classList.add('active');
    obCur = n;
    setProgress(n, false);
  }
  window.scrollTo(0,0);
}

function setProgress(step, done) {
  var pct = done ? 100 : Math.round(step / STEPS * 100);
  document.getElementById('ob-fill').style.width = pct + '%';
  for (var i = 1; i <= STEPS; i++) {
    var d = document.getElementById('dot-' + i);
    d.classList.remove('active','done');
    if (done || i < step) d.classList.add('done');
    else if (i === step) d.classList.add('active');
  }
}

function showErr(n, msg) {
  var el = document.getElementById('err-' + n);
  el.textContent = msg; el.style.display = 'block';
}
function clearErr(n) {
  var el = document.getElementById('err-' + n);
  el.textContent = ''; el.style.display = 'none';
}

function selCard(el, name) {
  el.parentElement.querySelectorAll('.choice-card,.goal-card').forEach(function(c) {
    c.classList.remove('selected');
  });
  el.classList.add('selected');
  document.getElementById('input-' + name).value = el.dataset.value;
}

function nextStep(n) {
  clearErr(n);
  if (n === 1) {
    var nome  = document.getElementById('ob-nome').value.trim();
    var email = document.getElementById('ob-email').value.trim();
    var senha = document.getElementById('ob-senha').value;
    var conf  = document.getElementById('ob-conf').value;
    if (nome.length < 2)             return showErr(1,'Nome deve ter pelo menos 2 caracteres.');
    if (email.indexOf('@') < 1)      return showErr(1,'Email inválido.');
    if (senha.length < 8)            return showErr(1,'Senha deve ter pelo menos 8 caracteres.');
    if (senha !== conf)              return showErr(1,'As senhas não coincidem.');
    goStep(2);
  } else if (n === 2) {
    var sexo  = document.getElementById('input-sexo').value;
    var idade = parseInt(document.getElementById('ob-idade').value);
    if (!sexo)                        return showErr(2,'Selecione o sexo biológico.');
    if (!idade||idade<10||idade>100)  return showErr(2,'Informe uma idade válida (10–100 anos).');
    goStep(3);
  } else if (n === 3) {
    var peso   = parseFloat(document.getElementById('ob-peso').value);
    var altura = parseInt(document.getElementById('ob-altura').value);
    if (!peso||peso<30||peso>300)      return showErr(3,'Peso inválido (30–300 kg).');
    if (!altura||altura<100||altura>250) return showErr(3,'Altura inválida (100–250 cm).');
    goStep(4);
  } else if (n === 4) {
    var obj = document.getElementById('input-objetivo').value;
    if (!obj) return showErr(4,'Selecione um objetivo.');
    showResult();
  }
}

function showResult() {
  var sexo   = document.getElementById('input-sexo').value;
  var idade  = parseInt(document.getElementById('ob-idade').value);
  var peso   = parseFloat(document.getElementById('ob-peso').value);
  var altura = parseInt(document.getElementById('ob-altura').value);
  var obj    = document.getElementById('input-objetivo').value;
  var base   = 10*peso + 6.25*altura - 5*idade;
  var tmb    = Math.round(base + (sexo==='M' ? 5 : -161));
  var labels = {emagrecer:'&#x1F525; Emagrecer',manter:'&#x2696;&#xFE0F; Manter peso',massa:'&#x1F4AA; Ganhar massa'};
  var infos  = {
    emagrecer: 'Para emagrecer, consuma menos calorias do que sua TMB, criando um déficit calórico controlado.',
    manter:    'Para manter o peso, equilibre seu consumo com o seu gasto energético diário.',
    massa:     'Para ganhar massa, consuma um pouco mais do que sua TMB, aliado a treinos de resistência.'
  };
  document.getElementById('tmb-tag').innerHTML  = labels[obj] || '';
  document.getElementById('tmb-info').textContent = infos[obj]  || '';
  goStep('result');
  animCount(0, tmb, document.getElementById('tmb-val'), 1100);
}

function animCount(from, to, el, ms) {
  var start = null;
  function tick(ts) {
    if (!start) start = ts;
    var p = Math.min((ts-start)/ms, 1);
    var e = 1 - Math.pow(1-p, 3);
    el.textContent = Math.round(from+(to-from)*e).toLocaleString('pt-BR');
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

// Restaura seleções quando o servidor devolve o formulário com dados pré-preenchidos.
(function() {
  var sv = document.getElementById('input-sexo').value;
  if (sv) { var c = document.getElementById('card-'+sv); if(c) c.classList.add('selected'); }
  var ov = document.getElementById('input-objetivo').value;
  if (ov) { var g = document.querySelector('.goal-card[data-value="'+ov+'"]'); if(g) g.classList.add('selected'); }
})();
</script>
"""
        return self.render_page(
            html.replace("[[CSRF]]", self._csrf_input())
            .replace("[[ERRO]]", erro_html)
            .replace("[[NOME]]", escape(nome))
            .replace("[[EMAIL]]", escape(email))
            .replace("[[SEXO]]", escape(sexo))
            .replace("[[PESO]]", escape(peso))
            .replace("[[ALTURA]]", escape(altura))
            .replace("[[IDADE]]", escape(idade))
            .replace("[[OBJETIVO]]", escape(objetivo)),
            mostrar_brand=False,
        )
