from __future__ import annotations

from contextlib import contextmanager
import mysql.connector

from config import DB_CONFIG


class MySQLConnectionFactory:
    """Crea conexiones bajo demanda y evita conexiones globales al importar módulos."""

    def __init__(self, config: dict | None = None):
        self.config = dict(config or DB_CONFIG)

    @contextmanager
    def connection(self):
        connection = mysql.connector.connect(**self.config)
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def cursor(self, *, dictionary: bool = False, buffered: bool = True):
        with self.connection() as connection:
            cursor = connection.cursor(dictionary=dictionary, buffered=buffered)
            try:
                yield connection, cursor
            finally:
                cursor.close()
