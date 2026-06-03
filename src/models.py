"""
Domain models for EasyTracker.

These dataclasses represent the core concepts of the app (macros, meals, AI
suggestions). They are plain data containers with no Flask or Gemini dependencies,
so they can be reused in tests, future SQLite storage, or API responses.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Macros:
    """
    Nutritional totals for a single meal or for the whole day.

    All macro values are stored as floats (grams for P/C/F, kcal for calories).
    Using a dedicated type instead of raw tuples makes route and store code
    easier to read and refactor.
    """

    proteinas: float
    carboidratos: float
    gorduras: float
    calorias: float

    @classmethod
    def zero(cls) -> Macros:
        """Empty totals used when the session has no meals yet."""
        return cls(0.0, 0.0, 0.0, 0.0)

    @classmethod
    def from_tuple(
        cls,
        values: tuple[float, float, float, float],
    ) -> Macros:
        """Build Macros from the (P, C, F, kcal) tuple returned by the AI layer."""
        return cls(*values)

    def as_tuple(self) -> tuple[float, float, float, float]:
        """Unpack macros for places that still expect a plain tuple."""
        return (
            self.proteinas,
            self.carboidratos,
            self.gorduras,
            self.calorias,
        )


@dataclass
class Refeicao:
    """
    One logged meal for the current day.

    Each meal gets a unique `id` so the user can remove a specific entry from
    the daily history without affecting others.
    """

    id: int
    texto: str
    proteinas: float
    carboidratos: float
    gorduras: float
    calorias: float
    horario: str

    @property
    def macros(self) -> Macros:
        """Shortcut to access this meal's macros as a Macros object."""
        return Macros(
            self.proteinas,
            self.carboidratos,
            self.gorduras,
            self.calorias,
        )

    @classmethod
    def from_dict(cls, data: dict) -> Refeicao:
        """Rebuild a Refeicao from the dict shape stored in Flask session."""
        return cls(
            id=int(data["id"]),
            texto=str(data["texto"]),
            proteinas=float(data["proteinas"]),
            carboidratos=float(data["carboidratos"]),
            gorduras=float(data["gorduras"]),
            calorias=float(data["calorias"]),
            horario=str(data.get("horario", "")),
        )

    def to_dict(self) -> dict:
        """Serialize to a JSON-friendly dict for Flask session storage."""
        return {
            "id": self.id,
            "texto": self.texto,
            "proteinas": self.proteinas,
            "carboidratos": self.carboidratos,
            "gorduras": self.gorduras,
            "calorias": self.calorias,
            "horario": self.horario,
        }


@dataclass(frozen=True)
class SugestaoRefeicao:
    """
    A meal suggestion produced by the AI.

    Unlike Refeicao, this is not persisted until the user clicks
    "Add to daily consumption". It includes ingredient lists for display.
    """

    nome: str
    ingredientes: list[str]
    quantidades: list[str]
    macros: Macros
