"""
Google Gemini integration for nutrition estimation and meal suggestions.

Responsibilities of this module:
  - Talk to the Gemini API (prompts + parsing responses)
  - Return typed domain objects (Macros, SugestaoRefeicao)

It does NOT know about Flask sessions or HTML. Routes call NutricaoAIService
methods and pass results to RefeicaoStore / PageRenderer.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

from models import Macros, SugestaoRefeicao

# Project root is one level above src/ (where .env lives).
ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")


def parse_nutricional(texto: str) -> tuple[float, float, float, float]:
    """
    Parse AI text "P,C,F,kcal" into four floats.

    Pure function: no side effects, easy to unit test without calling Gemini.
    Raises ValueError when the model returns an unexpected format.
    """
    valores = [float(v.strip()) for v in texto.strip().split(",")]
    if len(valores) != 4:
        raise ValueError(
            f"Expected 4 comma-separated numbers, got {len(valores)}: {texto!r}"
        )
    return valores[0], valores[1], valores[2], valores[3]


def _montar_descricao_refeicao(
    nome: str,
    ingredientes: list[str],
    quantidades: list[str],
) -> str:
    """
    Build a single meal description string from suggestion parts.

    Used as fallback when Gemini returns ingredients but omits macro numbers.
    """
    itens = []
    for i, ing in enumerate(ingredientes):
        qtd = quantidades[i] if i < len(quantidades) else ""
        itens.append(f"{qtd} {ing}".strip() if qtd else ing)
    corpo = ", ".join(itens) if itens else nome
    return f"{nome}: {corpo}"


def sugestao_parse(texto: str) -> SugestaoRefeicao:
    """
    Parse the pipe-delimited suggestion format from Gemini.

    Expected shape:
      name | ing1; ing2 | qty1; qty2 | P,C,F,kcal
    """
    partes = [p.strip() for p in texto.strip().split("|")]
    if len(partes) != 4:
        raise ValueError(
            f"Expected 4 pipe-separated parts, got {len(partes)}: {texto!r}"
        )
    nome = partes[0]
    ingredientes = [i.strip() for i in partes[1].split(";") if i.strip()]
    quantidades = [q.strip() for q in partes[2].split(";") if q.strip()]
    macros = Macros.from_tuple(parse_nutricional(partes[3]))
    return SugestaoRefeicao(
        nome=nome,
        ingredientes=ingredientes,
        quantidades=quantidades,
        macros=macros,
    )


class NutricaoAIService:
    """
    Service class that wraps all Gemini calls for EasyTracker.

    Why a class instead of loose functions?
      - Keeps API key, model name, and client in one place
      - Creates a fresh chat per request (avoids context leaking between users)
      - Easy to mock in tests by substituting this class

    Usage from app.py:
        ai = NutricaoAIService.from_env()
        macros = ai.estimate_macros("2 eggs and toast")
        suggestion = ai.generate_suggestion("light high-protein lunch")
    """

    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        if not api_key:
            raise RuntimeError("Set GOOGLE_API_KEY in .env (copy from .env.example).")
        # Long-lived client; individual chats are created per request below.
        self._client = genai.Client(api_key=api_key)
        self._model = model

    @classmethod
    def from_env(cls, model: str = DEFAULT_MODEL) -> NutricaoAIService:
        """Factory: read configuration from environment variables."""
        api_key = os.environ.get("GOOGLE_API_KEY", "")
        return cls(api_key=api_key, model=model)

    def _new_chat(self):
        """
        Start an isolated Gemini chat session.

        A new chat per call prevents earlier meal descriptions from influencing
        later estimates (which happened with a single global chat object).
        """
        return self._client.chats.create(model=self._model)

    def estimate_macros(self, meal_description: str) -> Macros:
        """
        Ask Gemini to estimate P/C/F/kcal for a free-text meal description.

        Returns a Macros instance ready for RefeicaoStore.add_from_text().
        """
        prompt = (
            f"gere o fator nutricional e apenas ele da seguinte refeição: "
            f"{meal_description}. "
            "quero a resposta formatada de forma simples e prática. "
            "quero que a resposta seja estruturada em número de proteínas, "
            "numero de carboidratos, numero de gorduras, e numero de calorias. "
            "APENAS o número de cada, sem nem o sinalizador de quantidade "
            "(ex: 220g), quero apenas o número de cada uma nessa ordem, "
            "separados por vírgula."
        )
        resposta = self._new_chat().send_message(prompt)
        return Macros.from_tuple(parse_nutricional(resposta.text or ""))

    def generate_suggestion(self, user_request: str) -> SugestaoRefeicao:
        """
        Generate a full meal suggestion (name, ingredients, macros).

        If Gemini returns a malformed macro section, we fall back to
        estimate_macros() on the assembled ingredient list.
        """
        prompt = (
            f"gere uma sugestao de refeicao conforme o pedido do usuario: "
            f"{user_request}. "
            "Responda SOMENTE com 4 partes separadas por |, nesta ordem: "
            "nome da refeicao | ingrediente1; ingrediente2 | "
            "quantidade1; quantidade2 | "
            "proteinas,carboidratos,gorduras,calorias (apenas numeros "
            "separados por virgula, sem unidades, estimativa total da "
            "refeicao sugerida)."
        )
        resposta = self._new_chat().send_message(prompt)
        try:
            return sugestao_parse(resposta.text or "")
        except ValueError:
            # Partial parse: keep name + ingredients, recompute macros via AI.
            partes = [p.strip() for p in (resposta.text or "").strip().split("|")]
            if len(partes) < 3:
                raise
            nome = partes[0]
            ingredientes = [i.strip() for i in partes[1].split(";") if i.strip()]
            quantidades = [q.strip() for q in partes[2].split(";") if q.strip()]
            descricao = _montar_descricao_refeicao(nome, ingredientes, quantidades)
            macros = self.estimate_macros(descricao)
            return SugestaoRefeicao(
                nome=nome,
                ingredientes=ingredientes,
                quantidades=quantidades,
                macros=macros,
            )
