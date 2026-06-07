import logging
import os
import sqlite3

logger = logging.getLogger("dex.memory.encryptor")

SENSITIVE_PATTERNS = [
    "пароль", "password", "pin", "secret", "token", "key",
    "credit", "card", "bank", "account", "passport", "snils",
    "финансы", "finance", "login", "credentials"
]


class SecureMemory:
    def __init__(self, db_path: str, key: str | None = None) -> None:
        self._db_path = db_path
        self._key = key or os.environ.get("DEX_SQLCIPHER_KEY", "default-dev-key-change-me")
        self._conn: sqlite3.Connection | None = None

    def initialize(self):
        try:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.execute(f"PRAGMA key = '{self._key}'")
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS secrets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    key_name TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self._conn.commit()
            logger.info(f"Secure memory initialized at {self._db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize SQLCipher: {e}")
            if self._conn:
                self._conn.close()
                self._conn = None

    @property
    def ready(self) -> bool:
        return self._conn is not None

    def store(self, category: str, key_name: str, value: str):
        if not self.ready:
            logger.warning("Secure memory not ready")
            return
        try:
            self._conn.execute(
                "INSERT OR REPLACE INTO secrets (category, key_name, value) VALUES (?, ?, ?)",
                (category, key_name, value)
            )
            self._conn.commit()
            logger.info(f"Stored secret: {category}/{key_name}")
        except Exception as e:
            logger.error(f"Failed to store secret: {e}")

    def retrieve(self, key_name: str) -> str | None:
        if not self.ready:
            return None
        try:
            cur = self._conn.execute(
                "SELECT value FROM secrets WHERE key_name = ?", (key_name,)
            )
            row = cur.fetchone()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Failed to retrieve secret: {e}")
            return None

    def delete(self, key_name: str):
        if self.ready:
            self._conn.execute("DELETE FROM secrets WHERE key_name = ?", (key_name,))
            self._conn.commit()

    def list_categories(self) -> list[str]:
        if not self.ready:
            return []
        cur = self._conn.execute("SELECT DISTINCT category FROM secrets")
        return [row[0] for row in cur.fetchall()]

    @staticmethod
    def is_sensitive(text: str) -> bool:
        lower = text.lower()
        return any(p in lower for p in SENSITIVE_PATTERNS)

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
