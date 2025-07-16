import logging
import secrets
from typing import Optional, Dict

import sqlite3
from flask import current_app

from ..config.settings import Settings


class UserService:
    """Service for managing API users."""

    def __init__(self, settings: Settings, app=None):
        self.logger = logging.getLogger(__name__)
        self.settings = settings
        if app is None:
            try:
                app = current_app
                self.db_path = app.config.get("DATABASE_PATH")
            except RuntimeError:
                self.db_path = settings.database_path
        else:
            self.db_path = app.config.get("DATABASE_PATH")
        self._ensure_table()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _ensure_table(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    api_key TEXT NOT NULL UNIQUE
                )
                """
            )
            conn.commit()

    def get_user(self, username: str) -> Optional[Dict]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT id, username, api_key FROM users WHERE username = ?",
                (username,),
            )
            row = cur.fetchone()
            if row:
                return {"id": row[0], "username": row[1], "api_key": row[2]}
        return None

    def get_user_by_api_key(self, api_key: str) -> Optional[Dict]:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT id, username, api_key FROM users WHERE api_key = ?",
                (api_key,),
            )
            row = cur.fetchone()
            if row:
                return {"id": row[0], "username": row[1], "api_key": row[2]}
        return None

    def set_api_key(self, username: str, api_key: str) -> str:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            )
            if cur.fetchone():
                conn.execute(
                    "UPDATE users SET api_key = ? WHERE username = ?",
                    (api_key, username),
                )
            else:
                conn.execute(
                    "INSERT INTO users (username, api_key) VALUES (?, ?)",
                    (username, api_key),
                )
            conn.commit()
        return api_key

    def generate_api_key(self, username: str) -> str:
        key = secrets.token_hex(16)
        return self.set_api_key(username, key)
