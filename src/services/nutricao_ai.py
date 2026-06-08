"""
Google Gemini integration for EasyTracker — structured output edition.

Usa response_schema para que o Gemini devolva JSON garantido em vez de texto
livre. Resultado: sem parsing frágil, sem fallbacks, prompts mais simples.

Fluxo anterior:
    Gemini → "30,45,8,350"  → parse_nutricional()  → pode quebrar
    Gemini → "nome|ing|qty|P,C,F,kcal" → sugestao_parse() → tem fallback

Fluxo atual:
    Gemini → {"proteinas":30, "carboidratos":45, ...}  → json.loads()  → direto
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TypedDict

from dotenv import load_dotenv
from google import genai
from google.genai import types

from models import Macros, SugestaoRefeicao

ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")


# ── Schemas JSON ──────────────────────────────────────────────────────────────


class MacrosJSON(TypedDict):
    """Schema de resposta para estimativa nutricional."""

    proteinas: float
    carboidratos: float
    gorduras: float
    calorias: float


class SugestaoJSON(TypedDict):
    """Schema de resposta para sugestão de refeição."""

    nome: str
    ingredientes: list[str]
    quantidades: list[str]
    proteinas: float
    carboidratos: float
    gorduras: float
    calorias: float


# ── Service ───────────────────────────────────────────────────────────────────


class NutricaoAIService:
    """
    Wrapper de todas as chamadas ao Gemini usando structured output.

    Cada método define um TypedDict como response_schema. O Gemini garante
    que a resposta é JSON válido com exatamente esses campos e tipos —
    zero parsing de texto, zero fallbacks.
    """

    DEFAULT_MODEL = "gemini-2.5-flash"

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL) -> None:
        if not api_key:
            raise RuntimeError("Set GOOGLE_API_KEY in .env (copy from .env.example).")
        self._client = genai.Client(api_key=api_key)
        self._model = model

    @classmethod
    def from_env(cls, model: str = DEFAULT_MODEL) -> NutricaoAIService:
        """Factory: lê configuração das variáveis de ambiente."""
        return cls(api_key=os.environ.get("GOOGLE_API_KEY", ""), model=model)

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def _config(self, schema: type) -> types.GenerateContentConfig:
        """
        Config compartilhada: JSON mode + schema + sem thinking + determinístico.

        thinking_budget=0 desliga o raciocínio interno — para extração
        estruturada simples isso reduz bastante a latência.
        """
        return types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
            temperature=0.0,
        )

    @staticmethod
    def _suggestion_prompt(user_request: str) -> str:
        """Prompt para sugestão — sem instruções de formato (o schema cuida disso)."""
        return (
            f"Gere uma sugestão de refeição conforme o pedido: {user_request}. "
            "Inclua o nome da refeição, a lista de ingredientes, as quantidades de "
            "cada ingrediente e os valores nutricionais estimados para a refeição "
            "completa (proteínas em g, carboidratos em g, gorduras em g e calorias em kcal)."
        )

    @staticmethod
    def _macros_from(data: dict) -> Macros:
        """Constrói Macros a partir de um dict JSON já validado pelo schema."""
        return Macros(
            proteinas=float(data.get("proteinas", 0)),
            carboidratos=float(data.get("carboidratos", 0)),
            gorduras=float(data.get("gorduras", 0)),
            calorias=float(data.get("calorias", 0)),
        )

    @staticmethod
    def _sugestao_from(data: dict) -> SugestaoRefeicao:
        """Constrói SugestaoRefeicao a partir de um dict JSON já validado."""
        return SugestaoRefeicao(
            nome=str(data.get("nome", "")),
            ingredientes=[str(i) for i in data.get("ingredientes", [])],
            quantidades=[str(q) for q in data.get("quantidades", [])],
            macros=NutricaoAIService._macros_from(data),
        )

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def estimate_macros(self, meal_description: str) -> Macros:
        """
        Pede ao Gemini a estimativa de P/C/G/kcal para uma descrição livre.

        O prompt não precisa mais instruir o formato da resposta — o schema
        garante que os campos chegam como números com os nomes corretos.
        """
        prompt = (
            f"Estime os valores nutricionais da seguinte refeição: {meal_description}. "
            "Retorne as gramas de proteínas, carboidratos, gorduras e o total de calorias."
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=self._config(MacrosJSON),
        )
        return self._macros_from(json.loads(response.text or "{}"))

    def generate_suggestion(self, user_request: str) -> SugestaoRefeicao:
        """
        Gera uma sugestão completa de refeição (nome, ingredientes, macros).

        Sem fallback: se o schema não for respeitado, json.loads levanta
        ValueError — mas isso não deve acontecer com response_schema ativo.
        """
        response = self._client.models.generate_content(
            model=self._model,
            contents=self._suggestion_prompt(user_request),
            config=self._config(SugestaoJSON),
        )
        return self._sugestao_from(json.loads(response.text or "{}"))

    def parse_suggestion(self, texto: str) -> SugestaoRefeicao:
        """
        Converte o JSON acumulado de stream_suggestion_text() em SugestaoRefeicao.

        Chamado pela rota /sugestao/stream após acumular todos os chunks.
        """
        return self._sugestao_from(json.loads(texto or "{}"))

    def stream_suggestion_text(self, user_request: str):
        """
        Gera uma sugestão em streaming, cedendo chunks de JSON conforme chegam.

        O chamador (rota /sugestao/stream) acumula os chunks e chama
        parse_suggestion() ao final. Os chunks são JSON parcial e não são
        exibidos diretamente — a UI mostra uma animação de carregamento.
        """
        for chunk in self._client.models.generate_content_stream(
            model=self._model,
            contents=self._suggestion_prompt(user_request),
            config=self._config(SugestaoJSON),
        ):
            if chunk.text:
                yield chunk.text
