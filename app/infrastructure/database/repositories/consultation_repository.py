from __future__ import annotations

from app.infrastructure.database.mysql_connection import MySQLConnectionFactory


class ConsultationRepository:
    """Repository para historial y métricas de consultas del asistente."""

    def __init__(self, db: MySQLConnectionFactory):
        self.db = db

    def save(self, pregunta, intencion, producto, respuesta) -> bool:
        try:
            with self.db.cursor() as (connection, cursor):
                cursor.execute(
                    """INSERT INTO historial_consultas
                       (pregunta, intencion, producto, respuesta)
                       VALUES (%s, %s, %s, %s)""",
                    (pregunta, intencion, producto, respuesta),
                )
                connection.commit()
            return True
        except Exception as error:
            print("Error al guardar la consulta:", error)
            return False

    def total(self) -> int:
        with self.db.cursor() as (_, cursor):
            cursor.execute("SELECT COUNT(*) FROM historial_consultas")
            return int(cursor.fetchone()[0])

    def by_intention(self):
        with self.db.cursor() as (_, cursor):
            cursor.execute(
                """SELECT intencion, COUNT(*) AS total
                   FROM historial_consultas
                   GROUP BY intencion ORDER BY total DESC"""
            )
            return cursor.fetchall()

    def most_searched_products(self):
        with self.db.cursor() as (_, cursor):
            cursor.execute(
                """SELECT producto, COUNT(*) AS total
                   FROM historial_consultas
                   WHERE producto IS NOT NULL
                   GROUP BY producto ORDER BY total DESC LIMIT 5"""
            )
            return cursor.fetchall()
