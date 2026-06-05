"""Persistence layer: SQLite via SQLiteRefeicaoStore."""

from store.db import close_db, get_db, init_db
from store.refeicao_store import RefeicaoStore
from store.sqlite_refeicao_store import SQLiteRefeicaoStore

__all__ = [
    "RefeicaoStore",
    "SQLiteRefeicaoStore",
    "init_db",
    "get_db",
    "close_db",
]
