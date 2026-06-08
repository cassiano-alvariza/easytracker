"""
SQLite-backed meal store for EasyTracker.

Interface pública idêntica à original — as rotas em app.py não precisam
de nenhuma alteração além de passar usuario_id em vez de sessao_id.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from models import Macros, Refeicao


class SQLiteRefeicaoStore:
    """
    CRUD + agregação de refeições em SQLite, vinculadas a um usuario_id.

    Testável sem Flask:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        # rode o DDL de db.py
        store = SQLiteRefeicaoStore(conn, usuario_id=1)
    """

    def __init__(self, conn: sqlite3.Connection, usuario_id: int) -> None:
        self._conn = conn
        self._uid = usuario_id

    @staticmethod
    def _today() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def list_all(self) -> list[Refeicao]:
        """Retorna todas as refeições do dia, mais antigas primeiro."""
        rows = self._conn.execute(
            """
            SELECT id, texto, proteinas, carboidratos, gorduras, calorias, horario
            FROM   refeicoes
            WHERE  usuario_id = ? AND data = ?
            ORDER  BY id
            """,
            (self._uid, self._today()),
        ).fetchall()
        return [
            Refeicao(
                id=row["id"],
                texto=row["texto"],
                proteinas=row["proteinas"],
                carboidratos=row["carboidratos"],
                gorduras=row["gorduras"],
                calorias=row["calorias"],
                horario=row["horario"],
            )
            for row in rows
        ]

    def count(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM refeicoes WHERE usuario_id = ? AND data = ?",
            (self._uid, self._today()),
        ).fetchone()
        return row[0]

    def totals(self) -> Macros:
        """Soma dos macros de todas as refeições do dia."""
        row = self._conn.execute(
            """
            SELECT
                COALESCE(SUM(proteinas),    0.0) AS proteinas,
                COALESCE(SUM(carboidratos), 0.0) AS carboidratos,
                COALESCE(SUM(gorduras),     0.0) AS gorduras,
                COALESCE(SUM(calorias),     0.0) AS calorias
            FROM   refeicoes
            WHERE  usuario_id = ? AND data = ?
            """,
            (self._uid, self._today()),
        ).fetchone()
        return Macros(
            proteinas=row["proteinas"],
            carboidratos=row["carboidratos"],
            gorduras=row["gorduras"],
            calorias=row["calorias"],
        )

    def add_from_text(self, texto: str, macros: Macros) -> Refeicao:
        """Persiste uma nova refeição e retorna o objeto com id atribuído pelo banco."""
        horario = datetime.now().strftime("%H:%M")
        texto = texto.strip() or "Refeição"
        cursor = self._conn.execute(
            """
            INSERT INTO refeicoes
                (usuario_id, data, texto, proteinas, carboidratos, gorduras, calorias, horario)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._uid,
                self._today(),
                texto,
                macros.proteinas,
                macros.carboidratos,
                macros.gorduras,
                macros.calorias,
                horario,
            ),
        )
        self._conn.commit()
        return Refeicao(
            id=cursor.lastrowid or 0,
            texto=texto,
            proteinas=macros.proteinas,
            carboidratos=macros.carboidratos,
            gorduras=macros.gorduras,
            calorias=macros.calorias,
            horario=horario,
        )

    def remove(self, refeicao_id: int) -> bool:
        """Remove uma refeição pelo id. Retorna False se não encontrada."""
        cursor = self._conn.execute(
            "DELETE FROM refeicoes WHERE id = ? AND usuario_id = ?",
            (refeicao_id, self._uid),
        )
        self._conn.commit()
        return cursor.rowcount > 0
