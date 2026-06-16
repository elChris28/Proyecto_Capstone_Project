import mysql.connector
from thefuzz import process
from datetime import datetime, timedelta

from config import DB_CONFIG
from utils import (
    normalizar_texto,
    limpiar_texto,
    calcular_dias_vencimiento
)


conexion = mysql.connector.connect(**DB_CONFIG)
cursor = conexion.cursor(buffered=True)


def detectar_producto(texto):
    texto = normalizar_texto(texto)
    texto_limpio = limpiar_texto(texto)

    query = "SELECT DISTINCT producto FROM productos"
    cursor.execute(query)

    productos = cursor.fetchall()
    lista_productos = [p[0] for p in productos]

    if not lista_productos:
        return None

    mejor_producto = None
    mejor_score = 0

    for producto in lista_productos:
        producto_norm = normalizar_texto(producto)

        score1 = process.extractOne(producto_norm, [texto_limpio])[1]
        score2 = process.extractOne(producto_norm, [texto])[1]

        score = max(score1, score2)

        if score > mejor_score:
            mejor_score = score
            mejor_producto = producto

    if mejor_score >= 80:
        return mejor_producto

    return None


def obtener_stock(producto):
    query = """
    SELECT SUM(stock)
    FROM productos
    WHERE producto = %s
    """
    cursor.execute(query, (producto,))
    resultado = cursor.fetchone()

    if resultado and resultado[0] is not None:
        return resultado[0]

    return None


def obtener_ubicacion(producto):
    query = """
    SELECT DISTINCT ubicacion
    FROM productos
    WHERE producto = %s
      AND ubicacion IS NOT NULL
    """
    cursor.execute(query, (producto,))
    resultados = cursor.fetchall()

    if resultados:
        ubicaciones = [fila[0] for fila in resultados]
        return ", ".join(ubicaciones)

    return None


def obtener_lotes_vencimiento(producto):
    query = """
    SELECT lote, fecha_vencimiento
    FROM productos
    WHERE producto = %s
    ORDER BY fecha_vencimiento ASC
    """
    cursor.execute(query, (producto,))
    return cursor.fetchall()


def obtener_vencimiento(producto):
    query = """
    SELECT fecha_vencimiento
    FROM productos
    WHERE producto = %s
    ORDER BY fecha_vencimiento ASC
    LIMIT 1
    """
    cursor.execute(query, (producto,))
    resultado = cursor.fetchone()

    if resultado:
        return resultado[0]

    return None


def obtener_productos_por_vencer(margen_dias=7):
    hoy = datetime.now().date()
    fecha_limite = hoy + timedelta(days=margen_dias)

    query = """
    SELECT producto, lote, fecha_vencimiento
    FROM productos
    WHERE fecha_vencimiento BETWEEN %s AND %s
    ORDER BY fecha_vencimiento ASC
    """
    cursor.execute(query, (hoy, fecha_limite))
    return cursor.fetchall()


def obtener_stock_critico():
    query = """
    SELECT producto, stock, stock_minimo
    FROM productos
    WHERE stock <= stock_minimo
    ORDER BY stock ASC
    """
    cursor.execute(query)
    return cursor.fetchall()


def guardar_consulta(pregunta, intencion, producto, respuesta):
    try:
        query = """
        INSERT INTO historial_consultas
        (pregunta, intencion, producto, respuesta)
        VALUES (%s, %s, %s, %s)
        """

        cursor.execute(query, (
            pregunta,
            intencion,
            producto,
            respuesta
        ))

        conexion.commit()

    except Exception as error:
        print("Error al guardar la consulta:", error)


def obtener_total_consultas():
    query = "SELECT COUNT(*) FROM historial_consultas"
    cursor.execute(query)
    resultado = cursor.fetchone()
    return resultado[0]


def obtener_consultas_por_intencion():
    query = """
    SELECT intencion, COUNT(*) AS total
    FROM historial_consultas
    GROUP BY intencion
    ORDER BY total DESC
    """
    cursor.execute(query)
    return cursor.fetchall()


def obtener_productos_mas_buscados():
    query = """
    SELECT producto, COUNT(*) AS total
    FROM historial_consultas
    WHERE producto IS NOT NULL
    GROUP BY producto
    ORDER BY total DESC
    LIMIT 5
    """
    cursor.execute(query)
    return cursor.fetchall()