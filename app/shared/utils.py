import unicodedata
import spacy
from datetime import datetime, date

_nlp = None


def obtener_nlp():
    global _nlp

    if _nlp is None:
        _nlp = spacy.load("es_core_news_sm")

    return _nlp


def normalizar_texto(texto):
    texto = str(texto).lower()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(
        caracter for caracter in texto
        if unicodedata.category(caracter) != "Mn"
    )
    return texto.strip()


def limpiar_texto(texto):
    nlp = obtener_nlp()
    doc = nlp(texto.lower())

    palabras = []

    for token in doc:
        if not token.is_stop and not token.is_punct:
            palabras.append(token.lemma_)

    return " ".join(palabras)


def convertir_a_fecha(fecha_vencimiento):
    if isinstance(fecha_vencimiento, datetime):
        return fecha_vencimiento.date()

    if isinstance(fecha_vencimiento, date):
        return fecha_vencimiento

    return datetime.strptime(str(fecha_vencimiento), "%Y-%m-%d").date()


def calcular_dias_vencimiento(fecha_vencimiento):
    hoy = datetime.now().date()
    fecha = convertir_a_fecha(fecha_vencimiento)
    diferencia = fecha - hoy
    return diferencia.days


def evaluar_estado_vencimiento(fecha_vencimiento, margen_dias=7):
    dias = calcular_dias_vencimiento(fecha_vencimiento)

    if dias < 0:
        estado = f"vencido hace {abs(dias)} días"
    elif dias == 0:
        estado = "vence hoy"
    elif dias <= margen_dias:
        estado = f"próximo a vencer en {dias} días"
    else:
        estado = f"vigente, faltan {dias} días"

    return estado, dias