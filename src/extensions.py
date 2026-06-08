"""
Extensões Flask instanciadas aqui para evitar importações circulares.

Cada extensão é criada sem app e inicializada com init_app() em app.py.
"""

from __future__ import annotations

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

login_manager = LoginManager()
login_manager.login_view = "auth.login"  # type: ignore[assignment]
login_manager.login_message = ""

csrf = CSRFProtect()

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
    default_limits=[],
)
