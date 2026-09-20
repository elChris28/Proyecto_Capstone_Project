from __future__ import annotations

from datetime import datetime, timedelta
from thefuzz import process

from app.domain.entities.product import Product
from app.infrastructure.database.mysql_connection import MySQLConnectionFactory
from app.shared.utils import normalizar_texto, limpiar_texto


class ProductRepository:
    """Repository: concentra todas las consultas de productos e inventario."""

    def __init__(self, db: MySQLConnectionFactory):
        self.db = db

    def _product_names(self) -> list[str]:
        with self.db.cursor() as (_, cursor):
            cursor.execute("SELECT DISTINCT producto FROM productos")
            return [row[0] for row in cursor.fetchall()]

    def detect_product(self, texto: str):
        texto = normalizar_texto(texto)
        texto_limpio = limpiar_texto(texto)
        productos = self._product_names()
        if not productos:
            return None

        mejor_producto = None
        mejor_score = 0
        for producto in productos:
            producto_norm = normalizar_texto(producto)
            score1 = process.extractOne(producto_norm, [texto_limpio])[1]
            score2 = process.extractOne(producto_norm, [texto])[1]
            score = max(score1, score2)
            if score > mejor_score:
                mejor_score = score
                mejor_producto = producto
        return mejor_producto if mejor_score >= 80 else None

    def suggest_products(self, texto: str, limite: int = 3) -> list[str]:
        texto_limpio = limpiar_texto(normalizar_texto(texto))
        productos = self._product_names()
        if not productos:
            return []
        return [
            producto for producto, score in process.extract(texto_limpio, productos, limit=limite)
            if score >= 50
        ]

    def get_stock(self, producto: str):
        with self.db.cursor() as (_, cursor):
            cursor.execute("SELECT SUM(stock) FROM productos WHERE producto = %s", (producto,))
            row = cursor.fetchone()
            return row[0] if row and row[0] is not None else None

    def get_location(self, producto: str):
        with self.db.cursor() as (_, cursor):
            cursor.execute(
                """SELECT DISTINCT ubicacion FROM productos
                   WHERE producto = %s AND ubicacion IS NOT NULL""",
                (producto,),
            )
            rows = cursor.fetchall()
            return ", ".join(row[0] for row in rows) if rows else None

    def get_lots_expiration(self, producto: str):
        with self.db.cursor() as (_, cursor):
            cursor.execute(
                """SELECT lote, fecha_vencimiento FROM productos
                   WHERE producto = %s ORDER BY fecha_vencimiento ASC""",
                (producto,),
            )
            return cursor.fetchall()

    def get_expiration(self, producto: str):
        with self.db.cursor() as (_, cursor):
            cursor.execute(
                """SELECT fecha_vencimiento FROM productos
                   WHERE producto = %s ORDER BY fecha_vencimiento ASC LIMIT 1""",
                (producto,),
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def get_expiring_products(self, margen_dias: int = 7):
        hoy = datetime.now().date()
        fecha_limite = hoy + timedelta(days=margen_dias)
        with self.db.cursor() as (_, cursor):
            cursor.execute(
                """SELECT producto, lote, fecha_vencimiento FROM productos
                   WHERE fecha_vencimiento BETWEEN %s AND %s
                   ORDER BY fecha_vencimiento ASC""",
                (hoy, fecha_limite),
            )
            return cursor.fetchall()

    def get_critical_stock(self):
        with self.db.cursor() as (_, cursor):
            cursor.execute(
                """SELECT producto, stock, stock_minimo FROM productos
                   WHERE stock <= stock_minimo ORDER BY stock ASC"""
            )
            return cursor.fetchall()

    def get_stock_map(self) -> dict[str, float]:
        try:
            with self.db.cursor() as (_, cursor):
                cursor.execute(
                    "SELECT producto, SUM(stock) AS stock_actual FROM productos GROUP BY producto"
                )
                return {row[0]: float(row[1] or 0) for row in cursor.fetchall()}
        except Exception as error:
            print("No se pudo obtener stock de MySQL para predicción:", error)
            return {}

    def get_prediction_inventory(self) -> list[dict]:
        try:
            with self.db.cursor() as (_, cursor):
                cursor.execute(
                    """SELECT id, producto_id, producto, categoria,
                              stock AS stock_actual, stock_minimo, stock_seguridad,
                              punto_reorden, lead_time_dias
                       FROM productos
                       WHERE activo = 1
                         AND producto_id IS NOT NULL
                         AND TRIM(producto_id) <> ''
                       ORDER BY producto_id"""
                )
                rows = cursor.fetchall()

            products = [
                Product(
                    id=row[0],
                    producto_id=row[1],
                    producto=row[2],
                    categoria=row[3],
                    stock_actual=float(row[4] or 0),
                    stock_minimo=float(row[5] or 0),
                    stock_seguridad=float(row[6] or 0),
                    punto_reorden=float(row[7] or 0),
                    lead_time_dias=float(row[8] or 1),
                )
                for row in rows
            ]
            return [product.to_prediction_dict() for product in products]
        except Exception as error:
            print("No se pudo obtener el catálogo MySQL para predicción:", error)
            return []
