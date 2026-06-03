import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    raise RuntimeError(
        "Defina GOOGLE_API_KEY no arquivo .env (copie de .env.example)."
    )

client = genai.Client(api_key=api_key)
chat = client.chats.create(model="gemini-2.5-flash")


def parse_nutricional(texto: str) -> tuple[float, float, float, float]:
    valores = [float(v.strip()) for v in texto.strip().split(",")]
    if len(valores) != 4:
        raise ValueError(
            f"Esperados 4 valores separados por vírgula, obtidos {len(valores)}: {texto!r}"
        )
    return valores[0], valores[1], valores[2], valores[3]

def _montar_descricao_refeicao(
    nome: str, ingredientes: list[str], quantidades: list[str]
) -> str:
    itens = []
    for i, ing in enumerate(ingredientes):
        qtd = quantidades[i] if i < len(quantidades) else ""
        itens.append(f"{qtd} {ing}".strip() if qtd else ing)
    corpo = ", ".join(itens) if itens else nome
    return f"{nome}: {corpo}"


def sugestao_parse(
    texto: str,
) -> tuple[str, list[str], list[str], float, float, float, float]:
    partes = [p.strip() for p in texto.strip().split("|")]
    if len(partes) != 4:
        raise ValueError(
            f"Esperadas 4 partes separadas por |, obtidas {len(partes)}: {texto!r}"
        )
    nome = partes[0]
    ingredientes = [i.strip() for i in partes[1].split(";") if i.strip()]
    quantidades = [q.strip() for q in partes[2].split(";") if q.strip()]
    proteinas, carboidratos, gorduras, calorias = parse_nutricional(partes[3])
    return (
        nome,
        ingredientes,
        quantidades,
        proteinas,
        carboidratos,
        gorduras,
        calorias,
    )

def nutri(refe: str) -> tuple[float, float, float, float]:
    prompt = (
        f"gere o fator nutricional e apenas ele da seguinte refeição: {refe}. "
        "quero a resposta formatada de forma simples e prática. "
        "quero que a resposta seja estruturada em número de proteínas, numero de carboidratos, "
        "numero de gorduras, e numero de calorias. "
        "APENAS o número de cada, sem nem o sinalizador de quantidade (ex: 220g), "
        "quero apenas o número de cada uma nessa ordem, separados por vírgula."
    )
    resposta = chat.send_message(prompt)
    return parse_nutricional(resposta.text)

def gerar_sugestao(
    pedido: str,
) -> tuple[str, list[str], list[str], float, float, float, float]:
    prompt = (
        f"gere uma sugestao de refeicao conforme o pedido do usuario: {pedido}. "
        "Responda SOMENTE com 4 partes separadas por |, nesta ordem: "
        "nome da refeicao | ingrediente1; ingrediente2 | quantidade1; quantidade2 | "
        "proteinas,carboidratos,gorduras,calorias (apenas numeros separados por virgula, "
        "sem unidades, estimativa total da refeicao sugerida)."
    )
    resposta = chat.send_message(prompt)
    try:
        return sugestao_parse(resposta.text)
    except ValueError:
        partes = [p.strip() for p in resposta.text.strip().split("|")]
        if len(partes) < 3:
            raise
        nome = partes[0]
        ingredientes = [i.strip() for i in partes[1].split(";") if i.strip()]
        quantidades = [q.strip() for q in partes[2].split(";") if q.strip()]
        macros = nutri(_montar_descricao_refeicao(nome, ingredientes, quantidades))
        return nome, ingredientes, quantidades, *macros