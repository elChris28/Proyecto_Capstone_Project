from __future__ import annotations

from datetime import datetime

from app.infrastructure.database.mysql_connection import MySQLConnectionFactory


class PredictionHistoryRepository:
    """Repository de trazabilidad de evaluaciones del modelo."""

    def __init__(self, db: MySQLConnectionFactory):
        self.db = db

    def ensure_tables(self) -> None:
        query_evaluaciones = """
        CREATE TABLE IF NOT EXISTS evaluaciones_riesgo_stock (
            id INT NOT NULL AUTO_INCREMENT,
            fecha_evaluacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            fecha_corte DATE NULL,
            horizonte_dias INT NOT NULL DEFAULT 7,
            modelo VARCHAR(100) NULL,
            umbral_alto DECIMAL(6,4) NULL,
            umbral_medio DECIMAL(6,4) NULL,
            total_productos INT NOT NULL DEFAULT 0,
            alto_riesgo INT NOT NULL DEFAULT 0,
            medio_riesgo INT NOT NULL DEFAULT 0,
            bajo_riesgo INT NOT NULL DEFAULT 0,
            probabilidad_promedio DECIMAL(6,2) NULL,
            PRIMARY KEY (id),
            KEY idx_eval_fecha (fecha_evaluacion)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        query_detalle = """
        CREATE TABLE IF NOT EXISTS historial_predicciones_stock (
            id BIGINT NOT NULL AUTO_INCREMENT,
            evaluacion_id INT NOT NULL,
            fecha_evaluacion DATETIME NOT NULL,
            producto_id VARCHAR(10) NOT NULL,
            producto VARCHAR(150) NOT NULL,
            categoria VARCHAR(80) NULL,
            stock_actual INT NOT NULL DEFAULT 0,
            demanda_estimada_7d INT NOT NULL DEFAULT 0,
            stock_proyectado_7d INT NOT NULL DEFAULT 0,
            probabilidad_riesgo DECIMAL(7,6) NOT NULL DEFAULT 0,
            nivel_riesgo VARCHAR(10) NOT NULL,
            PRIMARY KEY (id),
            KEY idx_hist_eval (evaluacion_id),
            KEY idx_hist_producto (producto_id),
            KEY idx_hist_fecha (fecha_evaluacion),
            CONSTRAINT fk_hist_eval FOREIGN KEY (evaluacion_id)
              REFERENCES evaluaciones_riesgo_stock(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """
        with self.db.cursor() as (connection, cursor):
            cursor.execute(query_evaluaciones)
            cursor.execute(query_detalle)
            connection.commit()

    def save_evaluation(self, resumen: dict):
        try:
            self.ensure_tables()
            fecha_eval = datetime.now()
            with self.db.cursor() as (connection, cursor):
                cursor.execute(
                    """INSERT INTO evaluaciones_riesgo_stock
                       (fecha_evaluacion, fecha_corte, horizonte_dias, modelo,
                        umbral_alto, umbral_medio, total_productos,
                        alto_riesgo, medio_riesgo, bajo_riesgo, probabilidad_promedio)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        fecha_eval,
                        resumen.get("fecha_corte"),
                        int(resumen.get("horizonte_dias", 7)),
                        resumen.get("modelo"),
                        float(resumen.get("umbral", 0)) / 100.0,
                        float(resumen.get("umbral_medio", 0)) / 100.0,
                        int(resumen.get("total_productos", 0)),
                        int(resumen.get("alto_riesgo", 0)),
                        int(resumen.get("medio_riesgo", 0)),
                        int(resumen.get("bajo_riesgo", 0)),
                        float(resumen.get("probabilidad_promedio", 0)),
                    ),
                )
                evaluacion_id = cursor.lastrowid
                rows = [
                    (
                        evaluacion_id,
                        fecha_eval,
                        item.get("producto_id"),
                        item.get("producto"),
                        item.get("categoria"),
                        int(item.get("stock_actual", 0)),
                        int(item.get("demanda_estimada_7d", 0)),
                        int(item.get("stock_proyectado_7d", 0)),
                        float(item.get("probabilidad_riesgo", 0)),
                        item.get("nivel_riesgo", "BAJO"),
                    )
                    for item in resumen.get("productos", [])
                ]
                if rows:
                    cursor.executemany(
                        """INSERT INTO historial_predicciones_stock
                           (evaluacion_id, fecha_evaluacion, producto_id, producto, categoria,
                            stock_actual, demanda_estimada_7d, stock_proyectado_7d,
                            probabilidad_riesgo, nivel_riesgo)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        rows,
                    )
                connection.commit()
            return evaluacion_id
        except Exception as error:
            print("No se pudo guardar la evaluación de riesgo:", error)
            return None

    def latest_evaluations(self, limite: int = 6) -> list[dict]:
        try:
            self.ensure_tables()
            limite = max(1, min(int(limite), 20))
            with self.db.cursor() as (_, cursor):
                cursor.execute(
                    f"""SELECT id, fecha_evaluacion, fecha_corte, horizonte_dias, modelo,
                               umbral_alto, umbral_medio, total_productos,
                               alto_riesgo, medio_riesgo, bajo_riesgo, probabilidad_promedio
                        FROM evaluaciones_riesgo_stock
                        ORDER BY fecha_evaluacion DESC, id DESC LIMIT {limite}"""
                )
                rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "fecha_evaluacion": row[1].strftime("%Y-%m-%d %H:%M:%S") if row[1] else None,
                    "fecha_corte": row[2].strftime("%Y-%m-%d") if row[2] else None,
                    "horizonte_dias": row[3],
                    "modelo": row[4],
                    "umbral_alto": round(float(row[5] or 0) * 100, 2),
                    "umbral_medio": round(float(row[6] or 0) * 100, 2),
                    "total_productos": row[7],
                    "alto_riesgo": row[8],
                    "medio_riesgo": row[9],
                    "bajo_riesgo": row[10],
                    "probabilidad_promedio": float(row[11] or 0),
                }
                for row in rows
            ]
        except Exception as error:
            print("No se pudo leer el historial de evaluaciones:", error)
            return []

    def product_history(self, producto_id: str, limite: int = 10) -> list[dict]:
        try:
            self.ensure_tables()
            limite = max(1, min(int(limite), 50))
            with self.db.cursor() as (_, cursor):
                cursor.execute(
                    f"""SELECT evaluacion_id, fecha_evaluacion, stock_actual,
                               demanda_estimada_7d, stock_proyectado_7d,
                               probabilidad_riesgo, nivel_riesgo
                        FROM historial_predicciones_stock
                        WHERE producto_id = %s
                        ORDER BY fecha_evaluacion DESC, id DESC LIMIT {limite}""",
                    (producto_id,),
                )
                rows = cursor.fetchall()
            return [
                {
                    "evaluacion_id": row[0],
                    "fecha_evaluacion": row[1].strftime("%Y-%m-%d %H:%M:%S") if row[1] else None,
                    "stock_actual": row[2],
                    "demanda_estimada_7d": row[3],
                    "stock_proyectado_7d": row[4],
                    "probabilidad_riesgo": round(float(row[5] or 0), 4),
                    "porcentaje_riesgo": round(float(row[5] or 0) * 100, 1),
                    "nivel_riesgo": row[6],
                }
                for row in rows
            ]
        except Exception as error:
            print("No se pudo leer el historial del producto:", error)
            return []
