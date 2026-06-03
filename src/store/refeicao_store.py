"""
Session-backed storage for daily meals.

RefeicaoStore is the only place that reads/writes meal data. Flask routes
should never touch session["refeicoes"] directly — they call methods here.

Today: data lives in Flask's signed cookie session (lost when cookie expires).
Tomorrow: swap this class for SQLiteRefeicaoStore with the same public methods;
           app.py routes stay unchanged.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from models import Macros, Refeicao


class RefeicaoStore:
    """
    CRUD + aggregation for meals stored in a Flask session dict.

    The store receives the session object (usually `flask.session`) in the
    constructor so it remains testable with a plain dict:

        fake_session = {}
        store = RefeicaoStore(fake_session)
        store.add_from_text("salad", Macros(10, 5, 2, 120))
    """

    # Keys used inside Flask session — centralized to avoid typos across the app.
    _KEY_MEALS = "refeicoes"
    _KEY_NEXT_ID = "proximo_id"
    _KEY_PROTEINAS = "proteinas"
    _KEY_CARBOIDRATOS = "carboidratos"
    _KEY_GORDURAS = "gorduras"
    _KEY_CALORIAS = "calorias"

    def __init__(self, session: Any) -> None:
        # We keep a reference to the mutable session mapping Flask provides.
        self._session = session

    def list_all(self) -> list[Refeicao]:
        """Return all meals for today, oldest first."""
        raw = self._session.get(self._KEY_MEALS, [])
        return [Refeicao.from_dict(item) for item in raw]

    def count(self) -> int:
        """Number of meals logged today (for subtitle copy on the summary page)."""
        return len(self.list_all())

    def totals(self) -> Macros:
        """
        Return cached daily totals from session.

        Totals are recalculated on every add/remove so reads stay O(1).
        """
        return Macros(
            proteinas=float(self._session.get(self._KEY_PROTEINAS, 0.0)),
            carboidratos=float(self._session.get(self._KEY_CARBOIDRATOS, 0.0)),
            gorduras=float(self._session.get(self._KEY_GORDURAS, 0.0)),
            calorias=float(self._session.get(self._KEY_CALORIAS, 0.0)),
        )

    def add_from_text(self, texto: str, macros: Macros) -> Refeicao:
        """
        Persist a new meal with the given description and macro breakdown.

        Assigns the next auto-increment id and stamps the current local time.
        """
        refeicoes = list(self._session.get(self._KEY_MEALS, []))
        proximo_id = int(self._session.get(self._KEY_NEXT_ID, 1))

        refeicao = Refeicao(
            id=proximo_id,
            texto=texto.strip() or "Refeição",
            proteinas=macros.proteinas,
            carboidratos=macros.carboidratos,
            gorduras=macros.gorduras,
            calorias=macros.calorias,
            horario=datetime.now().strftime("%H:%M"),
        )

        refeicoes.append(refeicao.to_dict())
        self._session[self._KEY_MEALS] = refeicoes
        self._session[self._KEY_NEXT_ID] = proximo_id + 1
        self._recalculate_totals()
        return refeicao

    def remove(self, refeicao_id: int) -> bool:
        """
        Delete one meal by id. Returns False if id was not found.
        """
        refeicoes = self._session.get(self._KEY_MEALS, [])
        filtradas = [r for r in refeicoes if r["id"] != refeicao_id]
        if len(filtradas) == len(refeicoes):
            return False
        self._session[self._KEY_MEALS] = filtradas
        self._recalculate_totals()
        return True

    def _recalculate_totals(self) -> None:
        """
        Sum macros from all meals and write aggregates back to session.

        Called internally after add/remove so `totals()` always reflects
        the meal list without iterating on every page view.
        """
        proteinas = carboidratos = gorduras = calorias = 0.0
        for refeicao in self.list_all():
            proteinas += refeicao.proteinas
            carboidratos += refeicao.carboidratos
            gorduras += refeicao.gorduras
            calorias += refeicao.calorias

        self._session[self._KEY_PROTEINAS] = proteinas
        self._session[self._KEY_CARBOIDRATOS] = carboidratos
        self._session[self._KEY_GORDURAS] = gorduras
        self._session[self._KEY_CALORIAS] = calorias
