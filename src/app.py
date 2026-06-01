import os
from html import escape
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, request, session

from ai_processing import nutri

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-only-troque-no-env")

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
</style>
"""


def _totais():
    return {
        "proteinas": session.get("proteinas", 0.0),
        "carboidratos": session.get("carboidratos", 0.0),
        "gorduras": session.get("gorduras", 0.0),
        "calorias": session.get("calorias", 0.0),
    }


def _fmt(n: float) -> str:
    return f"{n:.0f}" if n == int(n) else f"{n:.1f}"


def pagina(conteudo: str, mostrar_brand: bool = True) -> str:
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


def _macro_cards(proteinas, carboidratos, gorduras, calorias):
    return f"""
        <div class="macros">
            <div class="macro macro--protein">
                <div class="name">Proteínas</div>
                <div class="amount">{_fmt(proteinas)} <small>g</small></div>
            </div>
            <div class="macro macro--carbs">
                <div class="name">Carboidratos</div>
                <div class="amount">{_fmt(carboidratos)} <small>g</small></div>
            </div>
            <div class="macro macro--fat">
                <div class="name">Gorduras</div>
                <div class="amount">{_fmt(gorduras)} <small>g</small></div>
            </div>
            <div class="macro macro--calories">
                <div class="name">Calorias</div>
                <div class="amount">{_fmt(calorias)} <small>kcal</small></div>
            </div>
        </div>
    """

@app.route("/zerar")
def zerar():
    session.clear()
    return pagina(f"""
        <h2>Consumo zerado</h2>
        <p class="subtitle">O consumo foi zerado com sucesso.</p>
        <div class="btn-row">
            <a href="/" class="btn btn-primary">Voltar ao início</a>
        </div>
    """)
    return pagina(f"""
        <h2>Consumo zerado</h2>
        <p class="subtitle">O consumo foi zerado com sucesso.</p>
        <div class="btn-row">
            <a href="/" class="btn btn-primary">Voltar ao início</a>
        </div>
    """)

@app.route("/")
def home():
    calorias = _totais()["calorias"]
    return pagina(f"""
        <h2>Bem-vindo</h2>
        <p class="subtitle">Acompanhe o que você comeu hoje em um só lugar.</p>
        <div class="hero-cal">
            <div class="label">Consumo calórico do dia</div>
            <div class="value">{_fmt(calorias)}</div>
            <div class="unit">kcal</div>
        </div>
        <div class="actions">
            <a href="/sobre" class="btn btn-primary">➕ Adicionar refeição</a>
            <a href="/contato" class="btn btn-secondary">📊 Ver consumo nutricional</a>
            <a href="/zerar"class="btn btn-tertiary">Zerar consumo</a>
        </div>
    """)


@app.route("/sobre", methods=["GET", "POST"])
def sobre():
    if request.method == "POST":
        refe = request.form.get("ref", "")

        proteinas, carboidratos, gorduras, calorias = nutri(refe)
        print(f"Refeição adicionada: {refe}")
        print(proteinas, carboidratos, gorduras, calorias)

        totais = _totais()
        session["proteinas"] = totais["proteinas"] + proteinas
        session["carboidratos"] = totais["carboidratos"] + carboidratos
        session["gorduras"] = totais["gorduras"] + gorduras
        session["calorias"] = totais["calorias"] + calorias

        refe_safe = escape(refe)
        return pagina(f"""
            <div class="text-center">
                <div class="success-icon">✓</div>
                <h2>Refeição registrada</h2>
                <p class="subtitle">Os valores foram somados ao seu dia.</p>
            </div>
            <p class="meal-name"><strong>{refe_safe}</strong></p>
            <p class="subtitle" style="margin-bottom: 0.75rem;">Valores desta refeição:</p>
            {_macro_cards(proteinas, carboidratos, gorduras, calorias)}
            <div class="btn-row">
                <a href="/sobre" class="btn btn-primary">Adicionar outra</a>
                <a href="/" class="btn btn-secondary">Início</a>
            </div>
        """)

    return pagina(f"""
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


@app.route("/contato")
def contato():
    totais = _totais()
    return pagina(f"""
        <h2>Consumo do dia</h2>
        <p class="subtitle">Totais acumulados de todas as refeições registradas.</p>
        {_macro_cards(
            totais["proteinas"],
            totais["carboidratos"],
            totais["gorduras"],
            totais["calorias"],
        )}
        <div class="btn-row">
            <a href="/sobre" class="btn btn-primary">Adicionar refeição</a>
            <a href="/" class="btn btn-secondary">Início</a>
        </div>
    """)


if __name__ == "__main__":
    app.run(debug=True)
