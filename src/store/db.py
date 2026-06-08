"""
SQLite connection management for EasyTracker.

init_db() cria as tabelas na primeira execução e executa migrações automáticas.
get_db()  retorna a conexão da requisição atual (armazenada em flask.g).
close_db() é registrado como teardown — o Flask chama automaticamente.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from flask import g

DB_PATH = Path(__file__).resolve().parent.parent.parent / "easytracker.db"

_DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS usuarios (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    nome        TEXT    NOT NULL,
    senha_hash  TEXT    NOT NULL,
    sexo        TEXT,
    peso        REAL,
    altura      INTEGER,
    idade       INTEGER,
    objetivo    TEXT,
    tmb         REAL,
    criado_em   TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS refeicoes (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id   INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    data         TEXT    NOT NULL,
    texto        TEXT    NOT NULL,
    proteinas    REAL    NOT NULL DEFAULT 0.0,
    carboidratos REAL    NOT NULL DEFAULT 0.0,
    gorduras     REAL    NOT NULL DEFAULT 0.0,
    calorias     REAL    NOT NULL DEFAULT 0.0,
    horario      TEXT    NOT NULL,
    criado_em    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_refeicoes_usuario_data
    ON refeicoes (usuario_id, data);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """
    Migrações automáticas de schema.

    1. Detecta schema antigo (sessao_id) e recria refeicoes.
    2. Adiciona colunas novas a usuarios se não existirem (ALTER TABLE ADD COLUMN).
    """
    # Migração 1: schema antigo baseado em sessões
    ref_cols = [r[1] for r in conn.execute("PRAGMA table_info(refeicoes)").fetchall()]
    if ref_cols and "sessao_id" in ref_cols:
        conn.executescript("""
            DROP TABLE IF EXISTS refeicoes;
            DROP TABLE IF EXISTS sessoes;
        """)
        conn.commit()

    # Migração 2: novas colunas de perfil em usuarios
    user_cols = [r[1] for r in conn.execute("PRAGMA table_info(usuarios)").fetchall()]
    novas = {
        "sexo": "TEXT",
        "peso": "REAL",
        "altura": "INTEGER",
        "idade": "INTEGER",
        "objetivo": "TEXT",
        "tmb": "REAL",
    }
    for col, tipo in novas.items():
        if col not in user_cols:
            conn.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {tipo}")
    conn.commit()


def init_db(path: Path = DB_PATH) -> None:
    """Cria tabelas e índices se não existirem. Seguro chamar a cada startup."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    _migrate(conn)
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
