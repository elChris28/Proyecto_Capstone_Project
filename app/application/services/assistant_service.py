from __future__ import annotations

import re

from app.shared.utils import evaluar_estado_vencimiento, normalizar_texto


MENSAJE_DESCONOCIDO = """
No entendí la consulta.<br><br>

Puedes preguntar cosas como:<br>
• ¿Cuánto stock hay del producto?<br>
• ¿Dónde está el producto?<br>
• ¿Cuándo vence el producto?<br>
• ¿Cuántos días faltan para vencer?<br>
• ¿Qué productos tienen bajo stock?<br>
• ¿Qué productos están próximos a vencer?<br>
• ¿Qué productos tienen riesgo de quiebre de stock?
"""


def es_seguimiento_valido(texto):
    texto = normalizar_texto(texto)
    patrones = [
        r"\b(stock|cantidad|unidades|existencias|quedan)\b",
        r"\b(donde esta|donde se encuentra|donde queda|ubicacion|ubicad[oa]|estante|zona|almacen|rack)\b",
        r"\b(cuando vence|vence|vencimiento|caduca|caducidad|expira|lote|lotes)\b",
        r"\b(cuantos dias|cuanto falta|dias restantes|tiempo restante)\b",
        r"\bfaltan\b.*\b(vencer|vence|vencimiento|caducar)\b",
    ]
    return any(re.search(patron, texto) for patron in patrones)


def es_consulta_inventario(texto, producto_detectado, session):
    texto = normalizar_texto(texto)
    if producto_detectado:
        return True
    patrones = (
        r"\b(stock|cantidad|unidades|existencias|inventario|producto|productos|"
        r"ubicacion|ubicad[oa]|estante|zona|almacen|rack|"
        r"vencimiento|vence|vencer|caduca|caducidad|expira|lote|lotes|"
        r"critico|criticos|bajo stock|stock bajo|agotad[oa]s?|reponer|reposicion|"
        r"riesgo|quiebre|prediccion|predecir|proximos 7 dias|"
        r"por vencer|proxim[oa]s? a vencer|cuantos dias|dias restantes|cuanto falta)\b"
    )
    if re.search(patrones, texto):
        return True
    return bool(session.get("memoria_producto") and es_seguimiento_valido(texto))


class AssistantService:
    """Servicio de aplicación del asistente conversacional.

    La lógica conversa con repositorios y con PredictionService, sin SQL directo.
    """

    def __init__(
        self,
        product_repository,
        consultation_repository,
        prediction_service,
        intent_engine,
    ):
        self.products = product_repository
        self.consultations = consultation_repository
        self.predictions = prediction_service
        self.intent_engine = intent_engine

    def _save_and_return(self, texto, intencion, producto, respuesta):
        self.consultations.save(texto, intencion, producto, respuesta)
        return respuesta

    def _respond_multiple(self, producto, intenciones):
        respuestas = []
        if "stock" in intenciones:
            respuestas.append(f"📦 Stock total: {self.products.get_stock(producto)}")
        if "ubicacion" in intenciones:
            respuestas.append(f"📍 Ubicación: {self.products.get_location(producto)}")
        if "vencimiento" in intenciones or "dias_vencimiento" in intenciones:
            lotes = self.products.get_lots_expiration(producto)
            if lotes:
                respuestas.append(f"📅 Lotes y vencimientos de {producto}:")
                for lote, fecha in lotes:
                    estado, _ = evaluar_estado_vencimiento(fecha)
                    respuestas.append(f"• Lote {lote}: vence el {fecha} ({estado})")
            else:
                respuestas.append(f"No encontré lotes o vencimientos para {producto}")
        return "<br>".join(respuestas)

    def respond(self, texto, session):
        producto_detectado = self.products.detect_product(texto)
        producto = None
        intencion = "desconocido"

        if not es_consulta_inventario(texto, producto_detectado, session):
            return self._save_and_return(texto, "desconocido", None, MENSAJE_DESCONOCIDO)

        intencion = self.intent_engine.normalize_intent(
            self.intent_engine.predict_intent(texto),
            texto,
        )
        intenciones_detectadas = self.intent_engine.detect_multiple_intents(texto)

        if producto_detectado:
            producto = producto_detectado
            session["memoria_producto"] = producto
        elif es_seguimiento_valido(texto):
            producto = session.get("memoria_producto")

        if len(intenciones_detectadas) > 1:
            if not producto:
                return self._save_and_return(
                    texto, ",".join(intenciones_detectadas), None, "No pude identificar el producto."
                )
            respuesta = self._respond_multiple(producto, intenciones_detectadas)
            return self._save_and_return(
                texto, ",".join(intenciones_detectadas), producto, respuesta
            )

        if len(intenciones_detectadas) == 1:
            intencion = intenciones_detectadas[0]

        if intencion == "desconocido":
            return self._save_and_return(texto, "desconocido", None, MENSAJE_DESCONOCIDO)

        if not producto and intencion not in ["stock_critico", "productos_por_vencer", "riesgo_quiebre"]:
            sugerencias = self.products.suggest_products(texto)
            if sugerencias:
                respuesta = "No pude identificar exactamente el producto.<br><br>¿Quizás te refieres a alguno de estos?<br>"
                respuesta += "".join(f"• {item}<br>" for item in sugerencias)
            else:
                respuesta = "No pude identificar el producto."
            return self._save_and_return(texto, intencion, None, respuesta)

        if intencion == "riesgo_quiebre":
            detalle = self.predictions.find_from_text(texto)
            if detalle:
                respuesta = (
                    f"🔮 Riesgo de quiebre a 7 días para <b>{detalle['producto']}</b>:<br><br>"
                    f"• Nivel de riesgo: <b>{detalle['nivel_riesgo']}</b><br>"
                    f"• Probabilidad estimada: {detalle['porcentaje_riesgo']}%<br>"
                    f"• Stock actual: {detalle['stock_actual']} unidades<br>"
                    f"• Ventas últimos 7 días: {detalle['ventas_7d']} unidades<br>"
                    f"• Demanda estimada próximos 7 días: {detalle['demanda_estimada_7d']} unidades<br>"
                    f"• Stock proyectado: {detalle['stock_proyectado_7d']} unidades<br>"
                )
                if detalle["faltante_estimado"] > 0:
                    respuesta += f"• Faltante estimado: {detalle['faltante_estimado']} unidades<br>"
                respuesta += f"<br>💡 {detalle.get('recomendacion', '')}"
                return self._save_and_return(texto, intencion, detalle["producto"], respuesta)

            resumen = self.predictions.summary()
            if producto:
                return self._save_and_return(
                    texto,
                    intencion,
                    producto,
                    f"⚠️ <b>{producto}</b> existe en MySQL, pero todavía no tiene historial suficiente para calcular su riesgo a 7 días.",
                )

            riesgos = [p for p in resumen["productos"] if p["nivel_riesgo"] == "ALTO"][:10]
            if not riesgos and not resumen["medio_riesgo"]:
                return self._save_and_return(
                    texto,
                    intencion,
                    None,
                    "✅ El sistema no detecta productos en riesgo alto ni en zona de vigilancia para los próximos 7 días.",
                )
            if not riesgos:
                return self._save_and_return(
                    texto,
                    intencion,
                    None,
                    f"🟡 No hay productos en riesgo ALTO, pero {resumen['medio_riesgo']} producto(s) se encuentran en nivel MEDIO de vigilancia.",
                )

            respuesta = (
                f"🔮 <b>Riesgo de quiebre para los próximos 7 días</b><br><br>"
                f"El sistema detectó {resumen['alto_riesgo']} productos en riesgo <b>ALTO</b> y "
                f"{resumen['medio_riesgo']} en nivel <b>MEDIO</b>. Los 10 casos de mayor prioridad son:<br><br>"
            )
            for item in riesgos:
                respuesta += (
                    f"• {item['producto']}: {item['porcentaje_riesgo']}% de riesgo, "
                    f"stock {item['stock_actual']}, demanda estimada {item['demanda_estimada_7d']}<br>"
                )
            respuesta += "<br>📊 Revisa el módulo de Predicción de Stock para el detalle completo."
            return self._save_and_return(texto, intencion, None, respuesta)

        if intencion == "stock":
            stock = self.products.get_stock(producto)
            respuesta = (
                f"📦 El stock de {producto} es {stock} unidades"
                if stock is not None else f"No encontré información de stock para {producto}"
            )
            return self._save_and_return(texto, intencion, producto, respuesta)

        if intencion == "ubicacion":
            ubicacion = self.products.get_location(producto)
            respuesta = (
                f"📍 {producto} está ubicado en {ubicacion}"
                if ubicacion is not None else f"No encontré la ubicación de {producto}"
            )
            return self._save_and_return(texto, intencion, producto, respuesta)

        if intencion in ["vencimiento", "dias_vencimiento"]:
            lotes = self.products.get_lots_expiration(producto)
            if not lotes:
                return self._save_and_return(
                    texto, intencion, producto, f"No encontré lotes o fechas de vencimiento para {producto}"
                )
            if intencion == "vencimiento":
                respuesta = f"📅 Lotes y vencimientos de {producto}:<br><br>"
            else:
                respuesta = f"⏳ Estado de vencimiento por lote para {producto}:<br><br>"
            for lote, vencimiento in lotes:
                estado, _ = evaluar_estado_vencimiento(vencimiento)
                respuesta += f"• Lote {lote}: vence el {vencimiento} ({estado})<br>"
            return self._save_and_return(texto, intencion, producto, respuesta)

        if intencion == "stock_critico":
            productos = self.products.get_critical_stock()
            if not productos:
                return self._save_and_return(texto, intencion, None, "✅ No hay productos con stock crítico.")
            respuesta = "⚠️ Productos con stock crítico:<br><br>"
            for nombre, stock, minimo in productos:
                respuesta += f"• {nombre}: stock actual {stock}, stock mínimo {minimo}<br>"
            return self._save_and_return(texto, intencion, None, respuesta)

        if intencion == "productos_por_vencer":
            productos = self.products.get_expiring_products()
            if not productos:
                return self._save_and_return(texto, intencion, None, "✅ No hay productos próximos a vencer.")
            respuesta = "⚠️ Productos próximos a vencer por lote:<br><br>"
            for nombre, lote, fecha in productos:
                estado, _ = evaluar_estado_vencimiento(fecha)
                respuesta += f"• {nombre} | Lote {lote}: vence el {fecha} ({estado})<br>"
            return self._save_and_return(texto, intencion, None, respuesta)

        return self._save_and_return(texto, intencion, producto, "No pude procesar la consulta.")
