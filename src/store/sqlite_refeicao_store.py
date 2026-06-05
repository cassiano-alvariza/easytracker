"""
Store de refeições com persistência em SQLite.

Interface pública idêntica a RefeicaoStore — as rotas em app.py não precisam
de nenhuma alteração.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

from models import Macros, Refeicao


class SQLiteRefeicaoStore:
    """
    CRUD + agregação de refeições em SQLite.

    Recebe uma conexão aberta e o UUID da sessão do usuário.
    O ciclo de vida da conexão é gerenciado por get_db/close_db em db.py.

    Testável sem Flask:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        # rode o DDL de db.py
        store = SQLiteRefeicaoStore(conn, "uuid-qualquer")
    """

    def __init__(self, conn: sqlite3.Connection, sessao_id: str) -> None:
        self._conn = conn
        self._sid = sessao_id
        self._ensure_sessao()

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @staticmethod
    def _today() -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _ensure_sessao(self) -> None:
        """Registra a sessão se for nova; atualiza última atividade se já existir."""
        self._conn.execute(
            """
            INSERT INTO sessoes (id)
            VALUES (?)
            ON CONFLICT(id) DO UPDATE SET
                ultima_atividade = strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')
            """,
            (self._sid,),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Interface pública
    # ------------------------------------------------------------------

    def list_all(self) -> list[Refeicao]:
        """Retorna todas as refeições do dia, mais antigas primeiro."""
        rows = self._conn.execute(
            """
            SELECT id, texto, proteinas, carboidratos, gorduras, calorias, horario
            FROM   refeicoes
            WHERE  sessao_id = ? AND data = ?
            ORDER  BY id
            """,
            (self._sid, self._today()),
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
        """Número de refeições registradas hoje."""
        row = self._conn.execute(
            "SELECT COUNT(*) FROM refeicoes WHERE sessao_id = ? AND data = ?",
            (self._sid, self._today()),
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
            WHERE  sessao_id = ? AND data = ?
            """,
            (self._sid, self._today()),
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
                (sessao_id, data, texto, proteinas, carboidratos, gorduras, calorias, horario)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                self._sid,
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
            "DELETE FROM refeicoes WHERE id = ? AND sessao_id = ?",
            (refeicao_id, self._sid),
        )
        self._conn.commit()
        return cursor.rowcount > 0
