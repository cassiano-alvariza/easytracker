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

# Global stylesheet embedded in every page. Kept as a module constant because
# it is static and shared by all PageRenderer methods.
ESTILOS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
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
        font-family: "Outfit", system-ui, sans-serif;
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
        padding: 2rem 1.25rem 3rem;
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
        margin-top: 1.25rem;
        padding: 1rem;
        text-align: center;
        color: var(--muted);
        background: var(--surface-2);
        border-radius: 10px;
        font-size: 0.9rem;
    }
</style>
"""


class PageRenderer:
    """
    Builds full HTML pages and reusable UI fragments.

    Each public render_* method corresponds to one screen in the app.
    Private helpers (_fmt, _macro_cards, etc.) keep duplication low.
    """

    @staticmethod
    def _fmt(n: float) -> str:
        """Format numbers: integers without decimals, floats with one decimal."""
        return f"{n:.0f}" if n == int(n) else f"{n:.1f}"

    def render_page(self, conteudo: str, mostrar_brand: bool = True) -> str:
        """
        Wrap arbitrary inner HTML in the shared layout (head, brand, card).

        All screens call this so structure and CSS stay consistent.
        """
        brand = """
        <header class="brand">
            <div class="brand-icon">🥗</div>
            <div>
                <h1>EasyTracker <span>nutrição do dia</span></h1>
            </div>
        </header>
        """ if mostrar_brand else ""

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EasyTracker</title>
    {ESTILOS}
</head>
<body>
    <div class="app">
        {brand}
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
                <form action="{url_for('remover_refeicao')}" method="POST">
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
            itens.append(
                f"<li><strong>{escape(ing)}</strong> — {escape(qtd)}</li>"
            )
        return f"<ul class='ingredient-list'>{''.join(itens)}</ul>"

    def _register_suggestion_form(self, sugestao: SugestaoRefeicao) -> str:
        """
        Hidden-field form to add an AI suggestion to the daily log.

        Macros travel as hidden inputs so we do not call Gemini again on submit.
        """
        m = sugestao.macros
        return f"""
        <form action="/sugestao/registrar" method="POST" style="margin-top: 1rem;">
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
        return self.render_page("""
        <h2>Adicionar refeição</h2>
        <p class="subtitle">Descreva o que você comeu — a IA estima os macros.</p>
        <form action="/sobre" method="POST">
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
        """GET form: user asks the AI for a meal idea."""
        return self.render_page("""
        <h2>Sugerir refeição</h2>
        <p class="subtitle">Descreva o que você quer — a IA monta uma sugestão.</p>
        <form action="/sugestao" method="POST">
            <div>
                <label for="pedido">O que você está buscando?</label>
                <textarea id="pedido" name="pedido"
                    placeholder="Ex.: algo leve e rico em proteína para o almoço"
                    required></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Gerar sugestão</button>
        </form>
        <div class="btn-row">
            <a href="/" class="btn btn-secondary">← Voltar ao início</a>
        </div>
        """)

    def render_suggestion_result(self, sugestao: SugestaoRefeicao) -> str:
        """Shows AI suggestion with option to add it to the daily log."""
        return self.render_page(f"""
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
        """)

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
