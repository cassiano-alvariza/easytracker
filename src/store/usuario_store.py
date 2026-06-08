"""
CRUD de usuários no banco SQLite.

Responsabilidades: criar conta, buscar por email (login), buscar por id (Flask-Login).
"""

from __future__ import annotations

import sqlite3

from models import Usuario


class UsuarioStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def criar(
        self,
        email: str,
        nome: str,
        senha_hash: str,
        sexo: str = "",
        peso: float | None = None,
        altura: int | None = None,
        idade: int | None = None,
        objetivo: str = "",
        tmb: float | None = None,
    ) -> Usuario | None:
        """
        Insere um novo usuário com dados de perfil opcionais.
        Retorna None se o email já existir.
        """
        try:
            cursor = self._conn.execute(
                """
                INSERT INTO usuarios
                    (email, nome, senha_hash, sexo, peso, altura, idade, objetivo, tmb)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    email.lower().strip(),
                    nome.strip(),
                    senha_hash,
                    sexo or None,
                    peso,
                    altura,
                    idade,
                    objetivo or None,
                    tmb,
                ),
            )
            self._conn.commit()
            return Usuario(
                id=cursor.lastrowid or 0,
                email=email.lower().strip(),
                nome=nome.strip(),
                senha_hash=senha_hash,
                sexo=sexo,
                peso=peso,
                altura=altura,
                idade=idade,
                objetivo=objetivo,
                tmb=tmb,
            )
        except sqlite3.IntegrityError:
            return None  # email duplicado

    def buscar_por_email(self, email: str) -> Usuario | None:
        row = self._conn.execute(
            "SELECT * FROM usuarios WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
        return Usuario.from_row(row) if row else None

    def buscar_por_id(self, usuario_id: int) -> Usuario | None:
        row = self._conn.execute(
            "SELECT * FROM usuarios WHERE id = ?",
            (usuario_id,),
        ).fetchone()
        return Usuario.from_row(row) if row else None
