"""
SQLite connection management for EasyTracker.

init_db() cria as tabelas na primeira execução.
get_db()  retorna a conexão da requisição atual (armazenada em flask.g).
close_db() é registrado como teardown — o Flask chama automaticamente.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import g

# O arquivo .db fica na raiz do projeto (ao lado do .env).
DB_PATH = Path(__file__).resolve().parent.parent.parent / "easytracker.db"

_DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sessoes (
    id                TEXT PRIMARY KEY,
    criada_em         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')),
    ultima_atividade  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS refeicoes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sessao_id     TEXT    NOT NULL REFERENCES sessoes(id) ON DELETE CASCADE,
    data          TEXT    NOT NULL,
    texto         TEXT    NOT NULL,
    proteinas     REAL    NOT NULL DEFAULT 0.0,
    carboidratos  REAL    NOT NULL DEFAULT 0.0,
    gorduras      REAL    NOT NULL DEFAULT 0.0,
    calorias      REAL    NOT NULL DEFAULT 0.0,
    horario       TEXT    NOT NULL,
    criado_em     TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_refeicoes_sessao_data
    ON refeicoes (sessao_id, data);
"""


def init_db(path: Path = DB_PATH) -> None:
    """Cria tabelas e índices se não existirem. Seguro chamar a cada startup."""
    conn = sqlite3.connect(path)
    conn.executescript(_DDL)
    conn.commit()
    conn.close()


def get_db() -> sqlite3.Connection:
    """
    Retorna a conexão SQLite da requisição atual (Flask g).

    Abre uma nova conexão na primeira chamada do request e reutiliza
    nas chamadas seguintes. O teardown close_db() a fecha ao fim do request.
    """
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exception: BaseException | None = None) -> None:
    """Fecha a conexão ao fim de cada request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()
