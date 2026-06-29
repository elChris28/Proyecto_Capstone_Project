import json
import re
import joblib

from config import (
    MODELO_PATH,
    VECTORIZER_PATH,
    METRICAS_PATH,
    UMBRAL_DESCONOCIDO,
    UMBRAL_MULTIPLE,
    FACTOR_CERCANIA,
    MAX_INTENCIONES
)

from utils import normalizar_texto


modelo = joblib.load(MODELO_PATH)
vectorizer = joblib.load(VECTORIZER_PATH)


def cargar_metricas():
    try:
        with open(METRICAS_PATH, "r", encoding="utf-8") as archivo:
            return json.load(archivo)

    except FileNotFoundError:
        return {
            "accuracy": 0,
            "precision": 0,
            "recall": 0,
            "f1": 0
        }


metricas = cargar_metricas()


def obtener_ranking_intenciones(texto):
    texto_procesado = normalizar_texto(texto)
    texto_vectorizado = vectorizer.transform([texto_procesado])

    probabilidades = modelo.predict_proba(texto_vectorizado)[0]

    ranking = sorted(
        [
            (str(clase), float(probabilidad))
            for clase, probabilidad in zip(modelo.classes_, probabilidades)
        ],
        key=lambda item: item[1],
        reverse=True
    )

    return ranking


def predecir_intencion(texto):
    ranking = obtener_ranking_intenciones(texto)
    prediccion, confianza = ranking[0]

    print(f"Predicción ML: {prediccion} | Confianza: {round(confianza, 3)}")

    if confianza < UMBRAL_DESCONOCIDO:
        return "desconocido"

    return prediccion


def normalizar_intencion_modelo(intencion, texto):
    texto = normalizar_texto(texto)

    if intencion == "productos_criticos":
        return "stock_critico"

    if re.search(r"\blotes?\b", texto):

        if re.search(
            r"(proxim|por vencer|vencen pronto|vencimiento cercano)",
            texto
        ):
            return "productos_por_vencer"

        return "vencimiento"

    if re.search(
        r"(critico|criticos|bajo stock|stock bajo|stock minimo|agot|reponer|reposicion)",
        texto
    ):
        return "stock_critico"

    return intencion


def detectar_intenciones_por_reglas(texto):
    texto = normalizar_texto(texto)
    intenciones = []

    if re.search(
        r"\b(critico|criticos|bajo stock|stock bajo|stock minimo|agotad[oa]s?|agotarse|agotandose|reponer|reposicion|quiebre de stock)\b",
        texto
    ):
        return ["stock_critico"]

    if re.search(
        r"\b(productos?|lotes?)\b.*\b(proxim[oa]s? a vencer|por vencer|vencen pronto|caducan pronto|vencimiento cercano|por caducar)\b",
        texto
    ):
        return ["productos_por_vencer"]

    if re.search(
        r"\b(stock|cantidad|cuantas?|cuantos?|unidades|existencias?|disponible|disponibles|inventario|tengo|quedan?)\b",
        texto
    ):
        intenciones.append("stock")

    if re.search(
        r"\b(donde esta|donde se encuentra|donde queda|ubicacion|ubicad[oa]|estante|zona|almacen|localizar|ubicar|lugar|rack|estanteria|seccion|modulo)\b",
        texto
    ):
        intenciones.append("ubicacion")

    if re.search(
        r"\b(vence|vencer|vencimiento|caduca|caducidad|expira|expiracion|lote|lotes)\b",
        texto
    ):
        intenciones.append("vencimiento")

    if re.search(
        r"\b(cuantos dias|cuanto falta|dias restantes|tiempo restante|cuanto tiempo)\b",
        texto
    ) or re.search(
        r"\bfaltan\b.*\b(vencer|vence|vencimiento|caducar|caduca)\b",
        texto
    ):
        intenciones.append("dias_vencimiento")

    return intenciones


def detectar_intenciones_multiples(texto):
    ranking = obtener_ranking_intenciones(texto)
    intencion_principal, probabilidad_principal = ranking[0]

    intenciones_reglas = detectar_intenciones_por_reglas(texto)

    if "stock_critico" in intenciones_reglas:
        return ["stock_critico"]

    if "productos_por_vencer" in intenciones_reglas:
        return ["productos_por_vencer"]

    intenciones_ml = []

    if probabilidad_principal >= UMBRAL_DESCONOCIDO:

        for intencion, probabilidad in ranking:

            if intencion in ["stock_critico", "productos_por_vencer"]:
                continue

            condicion_probabilidad = probabilidad >= UMBRAL_MULTIPLE
            condicion_cercania = (
                probabilidad >= probabilidad_principal * FACTOR_CERCANIA
            )

            if condicion_probabilidad and condicion_cercania:
                intenciones_ml.append(intencion)

    intenciones_finales = []

    for intencion in intenciones_reglas + intenciones_ml:
        if intencion not in intenciones_finales:
            intenciones_finales.append(intencion)

    if not intenciones_finales and probabilidad_principal >= UMBRAL_DESCONOCIDO:
        intenciones_finales.append(intencion_principal)

    return intenciones_finales[:MAX_INTENCIONES]