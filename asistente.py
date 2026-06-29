import re

from utils import (evaluar_estado_vencimiento,normalizar_texto)
from predictor import (predecir_intencion,normalizar_intencion_modelo,detectar_intenciones_multiples)
from database import (detectar_producto,obtener_stock,obtener_ubicacion,obtener_lotes_vencimiento,obtener_stock_critico,obtener_productos_por_vencer,guardar_consulta, sugerir_productos)
from utils import (evaluar_estado_vencimiento)

MENSAJE_DESCONOCIDO = """
No entendí la consulta.<br><br>

Puedes preguntar cosas como:<br>
• ¿Cuánto stock hay del producto?<br>
• ¿Dónde está el producto?<br>
• ¿Cuándo vence el producto?<br>
• ¿Cuántos días faltan para vencer?<br>
• ¿Qué productos tienen bajo stock?<br>
• ¿Qué productos están próximos a vencer?
"""

def es_seguimiento_valido(texto):
    texto = normalizar_texto(texto)

    patrones = [
        r"\b(stock|cantidad|unidades|existencias|quedan)\b",
        r"\b(donde esta|donde se encuentra|donde queda|ubicacion|ubicad[oa]|estante|zona|almacen|rack)\b",
        r"\b(cuando vence|vence|vencimiento|caduca|caducidad|expira|lote|lotes)\b",
        r"\b(cuantos dias|cuanto falta|dias restantes|tiempo restante)\b",
        r"\bfaltan\b.*\b(vencer|vence|vencimiento|caducar)\b"
    ]

    return any(re.search(patron, texto) for patron in patrones)


def es_consulta_inventario(texto, producto_detectado, session):
    texto = normalizar_texto(texto)

    if producto_detectado:
        return True

    patrones_inventario = (
        r"\b(stock|cantidad|unidades|existencias|inventario|producto|productos|"
        r"ubicacion|ubicad[oa]|estante|zona|almacen|rack|"
        r"vencimiento|vence|vencer|caduca|caducidad|expira|lote|lotes|"
        r"critico|criticos|bajo stock|stock bajo|agotad[oa]s?|reponer|reposicion|"
        r"por vencer|proxim[oa]s? a vencer|cuantos dias|dias restantes|cuanto falta)\b"
    )

    if re.search(patrones_inventario, texto):
        return True

    if session.get("memoria_producto") and es_seguimiento_valido(texto):
        return True

    return False



def responder_multiples_intenciones(producto, intenciones):
    respuestas = []

    if "stock" in intenciones:
        stock = obtener_stock(producto)
        respuestas.append(f"📦 Stock total: {stock}")

    if "ubicacion" in intenciones:
        ubicacion = obtener_ubicacion(producto)
        respuestas.append(f"📍 Ubicación: {ubicacion}")

    if "vencimiento" in intenciones or "dias_vencimiento" in intenciones:
        lotes = obtener_lotes_vencimiento(producto)

        if lotes:
            respuestas.append(f"📅 Lotes y vencimientos de {producto}:")

            for lote, fecha in lotes:
                estado, dias = evaluar_estado_vencimiento(fecha)
                respuestas.append(
                    f"• Lote {lote}: vence el {fecha} ({estado})"
                )

        else:
            respuestas.append(
                f"No encontré lotes o vencimientos para {producto}"
            )

    return "<br>".join(respuestas)


def asistente(texto, session):
    producto_detectado = detectar_producto(texto)

    producto = None
    intencion = "desconocido"

    def finalizar_respuesta(respuesta, intencion_final=None, producto_final=None):
        guardar_consulta(
            texto,
            intencion_final if intencion_final else intencion,
            producto_final if producto_final else producto,
            respuesta
        )
        return respuesta

    # Si no es una consulta relacionada al inventario, responder como desconocido
    if not es_consulta_inventario(texto, producto_detectado, session):
        return finalizar_respuesta(
            MENSAJE_DESCONOCIDO,
            "desconocido",
            None
        )

    intencion = predecir_intencion(texto)
    intencion = normalizar_intencion_modelo(intencion, texto)

    intenciones_detectadas = detectar_intenciones_multiples(texto)
    print("Intenciones detectadas:", intenciones_detectadas)

    # Usar memoria solo si la pregunta parece continuación válida
    if producto_detectado:
        producto = producto_detectado
        session["memoria_producto"] = producto
    elif es_seguimiento_valido(texto):
        producto = session.get("memoria_producto")
    else:
        producto = None

    def finalizar_respuesta(respuesta, intencion_final=None, producto_final=None):
        guardar_consulta(
            texto,
            intencion_final if intencion_final else intencion,
            producto_final if producto_final else producto,
            respuesta
        )
        return respuesta

    if len(intenciones_detectadas) > 1:

        if not producto:
            return finalizar_respuesta(
                "No pude identificar el producto.",
                ",".join(intenciones_detectadas),
                None
            )

        respuesta = responder_multiples_intenciones(
            producto,
            intenciones_detectadas
        )

        return finalizar_respuesta(
            respuesta,
            ",".join(intenciones_detectadas),
            producto
        )

    if len(intenciones_detectadas) == 1:
        intencion = intenciones_detectadas[0]

    if intencion == "desconocido":
        return finalizar_respuesta(
            MENSAJE_DESCONOCIDO,
            "desconocido",
            None
        )

    if not producto and intencion not in [
        "stock_critico",
        "productos_por_vencer"
    ]:
        sugerencias = sugerir_productos(texto)

        if sugerencias:
            respuesta = "No pude identificar exactamente el producto.<br><br>"
            respuesta += "¿Quizás te refieres a alguno de estos?<br>"
            for item in sugerencias:
                respuesta += f"• {item}<br>"
        else:
            respuesta = "No pude identificar el producto."

        return finalizar_respuesta(
            respuesta,
            intencion,
            None
        )

    if intencion == "stock":
        stock = obtener_stock(producto)

        if stock is None:
            return finalizar_respuesta(
                f"No encontré información de stock para {producto}",
                intencion,
                producto
            )

        return finalizar_respuesta(
            f"📦 El stock de {producto} es {stock} unidades",
            intencion,
            producto
        )

    elif intencion == "ubicacion":
        ubicacion = obtener_ubicacion(producto)

        if ubicacion is None:
            return finalizar_respuesta(
                f"No encontré la ubicación de {producto}",
                intencion,
                producto
            )

        return finalizar_respuesta(
            f"📍 {producto} está ubicado en {ubicacion}",
            intencion,
            producto
        )

    elif intencion == "vencimiento":
        lotes = obtener_lotes_vencimiento(producto)

        if not lotes:
            return finalizar_respuesta(
                f"No encontré lotes o fechas de vencimiento para {producto}",
                intencion,
                producto
            )

        respuesta = f"📅 Lotes y vencimientos de {producto}:<br><br>"

        for lote, vencimiento in lotes:
            estado, dias = evaluar_estado_vencimiento(vencimiento)
            respuesta += (
                f"• Lote {lote}: vence el {vencimiento} "
                f"({estado})<br>"
            )

        return finalizar_respuesta(respuesta, intencion, producto)

    elif intencion == "dias_vencimiento":
        lotes = obtener_lotes_vencimiento(producto)

        if not lotes:
            return finalizar_respuesta(
                f"No encontré lotes o fechas de vencimiento para {producto}",
                intencion,
                producto
            )

        respuesta = f"⏳ Estado de vencimiento por lote para {producto}:<br><br>"

        for lote, vencimiento in lotes:
            estado, dias = evaluar_estado_vencimiento(vencimiento)
            respuesta += (
                f"• Lote {lote}: {estado}. "
                f"Fecha de vencimiento: {vencimiento}<br>"
            )

        return finalizar_respuesta(respuesta, intencion, producto)

    elif intencion == "stock_critico":
        productos = obtener_stock_critico()

        if not productos:
            return finalizar_respuesta(
                "✅ No hay productos con stock crítico.",
                intencion,
                None
            )

        respuesta = "⚠️ Productos con stock crítico:<br><br>"

        for item in productos:
            nombre = item[0]
            stock = item[1]
            stock_minimo = item[2]

            respuesta += (
                f"• {nombre}: stock actual {stock}, "
                f"stock mínimo {stock_minimo}<br>"
            )

        return finalizar_respuesta(respuesta, intencion, None)

    elif intencion == "productos_por_vencer":
        productos = obtener_productos_por_vencer()

        if not productos:
            return finalizar_respuesta(
                "✅ No hay productos próximos a vencer.",
                intencion,
                None
            )

        respuesta = "⚠️ Productos próximos a vencer por lote:<br><br>"

        for producto_item in productos:
            nombre = producto_item[0]
            lote = producto_item[1]
            fecha = producto_item[2]

            estado, dias = evaluar_estado_vencimiento(fecha)

            respuesta += (
                f"• {nombre} | Lote {lote}: vence el {fecha} "
                f"({estado})<br>"
            )

        return finalizar_respuesta(respuesta, intencion, None)

    return finalizar_respuesta(
        "No pude procesar la consulta.",
        intencion,
        producto
    )