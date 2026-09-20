"""Inferencia optimizada de riesgo de quiebre de stock a 7 días.

El histórico y MySQL se relacionan mediante producto_id (P001...P500).
MySQL aporta el stock y parámetros operativos actuales; el histórico aporta
las variables de comportamiento de ventas.
"""

from __future__ import annotations

import json
import re
import unicodedata
from difflib import SequenceMatcher
from functools import lru_cache
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import joblib
import numpy as np
import pandas as pd

from config import MODELO_QUIEBRE_PATH as MODELO_PATH, METRICAS_QUIEBRE_PATH as METRICAS_PATH, FEATURES_ACTUALES_PATH, IMPORTANCIA_VARIABLES_PATH as IMPORTANCIA_PATH
from app.domain.strategies.prediction_strategy import build_prediction_strategy

# Semáforo operativo para presentación y priorización.
# No modifica el umbral binario validado del modelo (guardado en el bundle).
UMBRAL_ALTO_OPERATIVO = 0.75
UMBRAL_MEDIO_OPERATIVO = 0.50

FEATURES_NUMERICAS = [
    "stock_actual", "stock_seguridad", "punto_reorden", "lead_time_dias",
    "ventas_3d", "ventas_7d", "ventas_14d", "ventas_30d",
    "promedio_3d", "promedio_7d", "promedio_14d", "promedio_30d",
    "std_7d", "std_30d", "max_7d", "max_30d",
    "dias_venta_7d", "dias_venta_30d", "promo_7d", "promo_30d",
    "lag_1", "lag_7", "lag_14", "lag_28",
    "tendencia_7_30", "tendencia_ratio_7_30",
    "dias_cobertura_7", "dias_cobertura_30",
    "ratio_stock_reorden", "ratio_stock_seguridad",
    "margen_reorden", "margen_seguridad", "demanda_lead_7",
    "ratio_stock_demanda7", "ratio_stock_demanda_lead",
    "dia_semana", "mes", "dia_mes", "semana_anio", "es_fin_semana",
    "sin_doy", "cos_doy", "promocion",
]


@lru_cache(maxsize=1)
def _cargar_bundle():
    if not MODELO_PATH.exists():
        raise FileNotFoundError(
            "No existe modelo_quiebre_stock.pkl. Ejecuta: python -m scripts.training.train_stock_model"
        )
    return joblib.load(MODELO_PATH)


@lru_cache(maxsize=1)
def cargar_metricas_quiebre() -> Dict:
    if not METRICAS_PATH.exists():
        return {}
    return json.loads(METRICAS_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def cargar_importancia_variables() -> Dict:
    if not IMPORTANCIA_PATH.exists():
        return {}
    return json.loads(IMPORTANCIA_PATH.read_text(encoding="utf-8"))


def _nombre_modelo_amigable(nombre: str) -> str:
    nombres = {
        "RegresionLogistica": "Regresión Logística",
        "RandomForest": "Random Forest",
        "GradientBoosting": "Gradient Boosting",
    }
    return nombres.get(str(nombre or ""), str(nombre or "No disponible"))


@lru_cache(maxsize=1)
def _cargar_features_actuales() -> pd.DataFrame:
    if not FEATURES_ACTUALES_PATH.exists():
        raise FileNotFoundError(
            "No existen features actuales. Ejecuta: python -m scripts.training.train_stock_model"
        )
    return pd.read_csv(FEATURES_ACTUALES_PATH, parse_dates=["fecha"])


def _normalizar_clave_producto(texto: str) -> str:
    texto = str(texto or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _normalizar_producto_id(valor: str) -> str:
    return str(valor or "").strip().upper()


def _matriz_modelo(df: pd.DataFrame, columnas: List[str]) -> pd.DataFrame:
    numericas = df[FEATURES_NUMERICAS].astype("float32")
    categorias = pd.get_dummies(df["categoria"], prefix="cat", dtype="int8")
    X = pd.concat(
        [numericas.reset_index(drop=True), categorias.reset_index(drop=True)],
        axis=1,
    )
    return X.reindex(columns=columnas, fill_value=0)


def _recalcular_variables_stock(df: pd.DataFrame) -> None:
    """Actualiza todas las features que cambian al leer el stock real de MySQL."""
    df["dias_cobertura_7"] = df["stock_actual"] / (df["promedio_7d"] + 0.25)
    df["dias_cobertura_30"] = df["stock_actual"] / (df["promedio_30d"] + 0.25)
    df["ratio_stock_reorden"] = df["stock_actual"] / (df["punto_reorden"] + 1)
    df["ratio_stock_seguridad"] = df["stock_actual"] / (df["stock_seguridad"] + 1)
    df["margen_reorden"] = df["stock_actual"] - df["punto_reorden"]
    df["margen_seguridad"] = df["stock_actual"] - df["stock_seguridad"]
    df["demanda_lead_7"] = df["promedio_7d"] * df["lead_time_dias"]
    df["ratio_stock_demanda7"] = df["stock_actual"] / (df["ventas_7d"] + 1)
    df["ratio_stock_demanda_lead"] = (
        df["stock_actual"] / (df["demanda_lead_7"] + 1)
    )


def _demanda_estimada_7d(df: pd.DataFrame) -> pd.Series:
    # Estimación explicativa para el dashboard; la clasificación final usa ML.
    base = (
        0.55 * df["ventas_7d"]
        + 0.25 * (df["ventas_14d"] / 2.0)
        + 0.20 * (df["ventas_30d"] * 7.0 / 30.0)
    )
    # La tendencia reciente modifica suavemente la proyección sin volverla negativa.
    ajuste = np.clip(1.0 + 0.08 * df["tendencia_7_30"], 0.75, 1.30)
    return np.maximum(0, base * ajuste)


def _aplicar_catalogo_mysql(
    df: pd.DataFrame,
    inventario_mysql: Optional[List[Dict]],
) -> tuple[pd.DataFrame, List[str]]:
    if inventario_mysql is None:
        resultado = df.copy()
        resultado["id_mysql"] = None
        if "stock_minimo" not in resultado.columns:
            resultado["stock_minimo"] = resultado["stock_seguridad"]
        return resultado, []

    if not inventario_mysql:
        vacio = df.iloc[0:0].copy()
        vacio["id_mysql"] = pd.Series(dtype="object")
        vacio["stock_minimo"] = pd.Series(dtype="float64")
        return vacio, []

    catalogo = {}
    for item in inventario_mysql:
        producto_id = _normalizar_producto_id(item.get("producto_id"))
        if producto_id:
            catalogo[producto_id] = item

    trabajo = df.copy()
    trabajo["_producto_id"] = trabajo["producto_id"].map(_normalizar_producto_id)
    trabajo = trabajo[trabajo["_producto_id"].isin(catalogo)].copy()

    if trabajo.empty:
        faltantes = [
            f"{pid} - {info.get('producto', '')}"
            for pid, info in catalogo.items()
        ]
        return trabajo.drop(columns=["_producto_id"], errors="ignore"), faltantes

    trabajo["id_mysql"] = trabajo["_producto_id"].map(
        lambda pid: catalogo[pid].get("id")
    )
    trabajo["producto"] = trabajo["_producto_id"].map(
        lambda pid: catalogo[pid].get("producto") or pid
    )
    trabajo["categoria"] = trabajo["_producto_id"].map(
        lambda pid: catalogo[pid].get("categoria") or "Sin categoría"
    )
    trabajo["stock_actual"] = trabajo["_producto_id"].map(
        lambda pid: max(0.0, float(catalogo[pid].get("stock_actual") or 0))
    )
    trabajo["stock_minimo"] = trabajo["_producto_id"].map(
        lambda pid: max(0.0, float(catalogo[pid].get("stock_minimo") or 0))
    )
    trabajo["stock_seguridad"] = trabajo["_producto_id"].map(
        lambda pid: max(
            0.0,
            float(
                catalogo[pid].get("stock_seguridad")
                if catalogo[pid].get("stock_seguridad") is not None
                else catalogo[pid].get("stock_minimo") or 0
            ),
        )
    )
    trabajo["punto_reorden"] = trabajo["_producto_id"].map(
        lambda pid: max(0.0, float(catalogo[pid].get("punto_reorden") or 0))
    )
    trabajo["lead_time_dias"] = trabajo["_producto_id"].map(
        lambda pid: max(1.0, float(catalogo[pid].get("lead_time_dias") or 1))
    )

    _recalcular_variables_stock(trabajo)

    ids_historicos = set(trabajo["_producto_id"])
    sin_historial = [
        f"{pid} - {info.get('producto', '')}"
        for pid, info in catalogo.items()
        if pid not in ids_historicos
    ]

    return trabajo.drop(columns=["_producto_id"], errors="ignore"), sin_historial


def _factores_observados(fila: pd.Series) -> List[str]:
    """Genera explicaciones operativas a partir de las variables actuales.

    No pretende reemplazar la explicación interna del estimador. Son señales
    observables que ayudan al usuario a interpretar por qué un producto merece
    revisión dentro del contexto de inventario.
    """
    factores: List[str] = []

    stock = float(fila["stock_actual"])
    seguridad = float(fila["stock_seguridad"])
    reorden = float(fila["punto_reorden"])
    lead = max(1.0, float(fila["lead_time_dias"]))
    cobertura = float(fila.get("dias_cobertura_7", 0) or 0)
    proyectado = float(fila.get("stock_proyectado_7d", stock))
    tendencia = float(fila.get("tendencia_7_30", 0) or 0)
    ratio_tendencia = float(fila.get("tendencia_ratio_7_30", 1) or 1)

    if stock <= seguridad:
        factores.append(
            f"Stock actual ({int(round(stock))}) en o por debajo del stock de seguridad ({int(round(seguridad))})."
        )
    elif stock <= reorden:
        factores.append(
            f"Stock actual ({int(round(stock))}) en o por debajo del punto de reorden ({int(round(reorden))})."
        )

    if proyectado < 0:
        factores.append(
            f"La demanda estimada a 7 días supera el stock disponible en aproximadamente {int(np.ceil(abs(proyectado)))} unidades."
        )
    elif proyectado < seguridad:
        factores.append(
            f"El stock proyectado a 7 días ({int(round(proyectado))}) quedaría por debajo del stock de seguridad."
        )

    if cobertura <= lead:
        factores.append(
            f"La cobertura estimada ({cobertura:.1f} días) es igual o menor al lead time de reposición ({int(round(lead))} días)."
        )

    if tendencia >= 0.50 or ratio_tendencia >= 1.20:
        factores.append(
            "Las ventas recientes muestran aceleración respecto al comportamiento de mayor plazo."
        )

    if not factores:
        if stock > reorden and proyectado >= seguridad:
            factores.append(
                "El stock se mantiene sobre los niveles operativos de seguridad y reorden."
            )
        else:
            factores.append(
                "La alerta se obtiene de la combinación completa de variables utilizadas por el modelo."
            )

    return factores[:4]


def _umbrales_operativos(_: float | None = None) -> tuple[float, float]:
    """Devuelve los umbrales del semáforo de priorización.

    El modelo de Machine Learning continúa siendo binario y conserva su
    umbral validado para métricas y evaluación. La interfaz aplica una capa
    operativa independiente: BAJO < 50 %, MEDIO 50–<75 % y ALTO >= 75 %.
    """
    return UMBRAL_MEDIO_OPERATIVO, UMBRAL_ALTO_OPERATIVO


def _nivel_riesgo_operativo(probabilidad: float, _umbral_modelo: float | None = None) -> str:
    umbral_medio, umbral_alto = _umbrales_operativos()
    if probabilidad >= umbral_alto:
        return "ALTO"
    if probabilidad >= umbral_medio:
        return "MEDIO"
    return "BAJO"


def _recomendacion_operativa(fila: pd.Series, nivel_riesgo: str) -> str:
    nivel_riesgo = str(nivel_riesgo or "BAJO").upper()
    stock = float(fila["stock_actual"])
    seguridad = float(fila["stock_seguridad"])
    proyectado = float(fila.get("stock_proyectado_7d", stock))

    if nivel_riesgo == "BAJO":
        return "Mantener monitoreo periódico; no existe una alerta predictiva inmediata."

    if nivel_riesgo == "MEDIO":
        if proyectado < seguridad or stock <= seguridad:
            return "Mantener en vigilancia y revisar reposición si el stock continúa descendiendo."
        return "Mantener en vigilancia: la probabilidad se encuentra en el rango operativo MEDIO (50% a menos de 75%)."

    if proyectado < 0:
        return "Priorizar revisión de reposición: el escenario explicativo proyecta un faltante dentro de 7 días."
    if stock <= seguridad or proyectado < seguridad:
        return "Priorizar revisión de reposición antes del siguiente ciclo de abastecimiento."
    return "Revisar disponibilidad y reposición por la probabilidad elevada detectada por el modelo."


def predecir_riesgo_todos(
    inventario_mysql: Optional[List[Dict]] = None,
    stock_override: Optional[Dict[str, float]] = None,
) -> List[Dict]:
    bundle = _cargar_bundle()
    df = _cargar_features_actuales().copy()
    df, _ = _aplicar_catalogo_mysql(df, inventario_mysql)

    if df.empty:
        return []

    if stock_override:
        mapa = {
            _normalizar_clave_producto(k): v
            for k, v in stock_override.items()
        }
        for idx, nombre in df["producto"].items():
            valor = mapa.get(_normalizar_clave_producto(nombre))
            if valor is not None:
                df.at[idx, "stock_actual"] = max(0, float(valor))
        _recalcular_variables_stock(df)

    X = _matriz_modelo(df, bundle["columnas"])
    strategy = build_prediction_strategy(bundle["modelo"])
    prob = strategy.predict_probability(X)
    umbral_modelo = float(bundle["umbral"])

    umbral_medio, umbral_alto = _umbrales_operativos()
    df["probabilidad_riesgo"] = prob
    # Clasificación binaria original usada para validar el modelo.
    df["riesgo_binario_modelo"] = prob >= umbral_modelo
    # Semáforo operativo usado por dashboard, campana y asistente.
    df["riesgo_alto_operativo"] = prob >= umbral_alto
    df["nivel_riesgo_operativo"] = [
        _nivel_riesgo_operativo(float(p)) for p in prob
    ]
    df["demanda_estimada_7d"] = _demanda_estimada_7d(df)
    df["stock_proyectado_7d"] = df["stock_actual"] - df["demanda_estimada_7d"]
    df["margen_seguridad_proyectado"] = (
        df["stock_proyectado_7d"] - df["stock_seguridad"]
    )
    df["faltante_estimado"] = np.maximum(0, -df["stock_proyectado_7d"])

    resultados = []
    for _, fila in df.sort_values("probabilidad_riesgo", ascending=False).iterrows():
        id_mysql = fila.get("id_mysql")
        resultados.append({
            "fecha_corte": fila["fecha"].strftime("%Y-%m-%d"),
            "producto_id": str(fila["producto_id"]),
            "id_mysql": int(id_mysql) if pd.notna(id_mysql) else None,
            "producto_id_historico": str(fila["producto_id"]),
            "producto": str(fila["producto"]),
            "categoria": str(fila["categoria"]),
            "stock_actual": int(round(float(fila["stock_actual"]))),
            "stock_minimo": int(round(float(fila.get("stock_minimo", fila["stock_seguridad"])))),
            "stock_seguridad": int(round(float(fila["stock_seguridad"]))),
            "punto_reorden": int(round(float(fila["punto_reorden"]))),
            "lead_time_dias": int(round(float(fila["lead_time_dias"]))),
            "ventas_7d": int(round(float(fila["ventas_7d"]))),
            "ventas_14d": int(round(float(fila["ventas_14d"]))),
            "ventas_30d": int(round(float(fila["ventas_30d"]))),
            "promedio_diario_7d": round(float(fila["promedio_7d"]), 2),
            "tendencia_ventas": round(float(fila["tendencia_7_30"]), 2),
            "dias_cobertura": round(float(fila["dias_cobertura_7"]), 1),
            "demanda_estimada_7d": int(round(float(fila["demanda_estimada_7d"]))),
            "stock_proyectado_7d": int(round(float(fila["stock_proyectado_7d"]))),
            "margen_seguridad_proyectado": int(
                round(float(fila["margen_seguridad_proyectado"]))
            ),
            "faltante_estimado": int(math_ceil_nonnegative(fila["faltante_estimado"])),
            "probabilidad_riesgo": round(float(fila["probabilidad_riesgo"]), 4),
            "porcentaje_riesgo": round(float(fila["probabilidad_riesgo"]) * 100, 1),
            "nivel_riesgo": str(fila["nivel_riesgo_operativo"]),
            "clasificacion_binaria_modelo": "RIESGO" if bool(fila["riesgo_binario_modelo"]) else "NO_RIESGO",
            "factores_observados": _factores_observados(fila),
            "recomendacion": _recomendacion_operativa(fila, str(fila["nivel_riesgo_operativo"])),
        })

    return resultados


def math_ceil_nonnegative(valor) -> int:
    return int(np.ceil(max(0.0, float(valor))))


def obtener_resumen_predicciones(
    inventario_mysql: Optional[List[Dict]] = None,
    stock_override: Optional[Dict[str, float]] = None,
) -> Dict:
    df_base = _cargar_features_actuales().copy()
    _, sin_historial = _aplicar_catalogo_mysql(df_base, inventario_mysql)
    datos = predecir_riesgo_todos(
        inventario_mysql=inventario_mysql,
        stock_override=stock_override,
    )
    altos = [d for d in datos if d["nivel_riesgo"] == "ALTO"]
    medios = [d for d in datos if d["nivel_riesgo"] == "MEDIO"]
    bajos = [d for d in datos if d["nivel_riesgo"] == "BAJO"]

    metricas = cargar_metricas_quiebre()
    seleccionado = metricas.get("modelo_seleccionado")
    met_modelo = (
        metricas.get("resultados", {}).get(seleccionado, {})
        if seleccionado else {}
    )

    orden_modelos = ["RegresionLogistica", "RandomForest", "GradientBoosting"]
    comparacion_modelos = []
    for nombre in orden_modelos:
        met = metricas.get("resultados", {}).get(nombre, {})
        if not met:
            continue
        comparacion_modelos.append({
            "nombre_clave": nombre,
            "nombre": _nombre_modelo_amigable(nombre),
            "seleccionado": nombre == seleccionado,
            "accuracy": round(float(met.get("accuracy", 0)) * 100, 2),
            "precision": round(float(met.get("precision", 0)) * 100, 2),
            "recall": round(float(met.get("recall", 0)) * 100, 2),
            "f1": round(float(met.get("f1", 0)) * 100, 2),
            "umbral": round(float(met.get("umbral", 0)) * 100, 2),
            "cumple_recall": float(met.get("recall", 0)) >= float(metricas.get("recall_objetivo", 0.8)),
        })

    importancia = cargar_importancia_variables()
    variables_importantes = []
    top_importancia = importancia.get("top_10", []) if importancia else []
    max_relativa = max(
        [float(item.get("importancia_relativa_pct", 0)) for item in top_importancia] or [0.0]
    )
    for item in top_importancia:
        relativa = float(item.get("importancia_relativa_pct", 0))
        variables_importantes.append({
            "variable": item.get("variable", ""),
            "etiqueta": item.get("etiqueta", item.get("variable", "")),
            "importancia_f1": round(float(item.get("importancia_f1", 0)), 4),
            "desviacion": round(float(item.get("desviacion", 0)), 4),
            "importancia_relativa_pct": round(relativa, 1),
            "barra_pct": round((relativa / max_relativa * 100.0) if max_relativa > 0 else 0.0, 1),
        })

    total_bd = len(inventario_mysql) if inventario_mysql is not None else len(datos)
    total = len(datos)
    porcentaje_alto = (len(altos) / total * 100.0) if total else 0.0
    porcentaje_medio = (len(medios) / total * 100.0) if total else 0.0
    porcentaje_bajo = (len(bajos) / total * 100.0) if total else 0.0
    faltante_proyectado = sum(1 for d in datos if d["stock_proyectado_7d"] < 0)
    prob_promedio = (
        sum(d["porcentaje_riesgo"] for d in datos) / total if total else 0.0
    )
    categorias = sorted({d["categoria"] for d in datos})
    fecha_corte = datos[0]["fecha_corte"] if datos else None
    umbral_modelo_validado = float(met_modelo.get("umbral", 0))
    umbral_medio_operativo, umbral_alto_operativo = _umbrales_operativos()
    fecha_evaluacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "horizonte_dias": 7,
        "fecha_corte": fecha_corte,
        "fecha_evaluacion": fecha_evaluacion,
        "total_productos_bd": total_bd,
        "total_productos": total,
        "alto_riesgo": len(altos),
        "medio_riesgo": len(medios),
        "bajo_riesgo": len(bajos),
        "porcentaje_alto_riesgo": round(porcentaje_alto, 1),
        "porcentaje_medio_riesgo": round(porcentaje_medio, 1),
        "porcentaje_bajo_riesgo": round(porcentaje_bajo, 1),
        "faltante_proyectado": faltante_proyectado,
        "probabilidad_promedio": round(prob_promedio, 1),
        "top_prioritarios": altos[:5],
        "categorias": categorias,
        "productos_sin_historial": sin_historial,
        "cantidad_sin_historial": len(sin_historial),
        "fuente_catalogo": "MySQL" if inventario_mysql is not None else "dataset",
        "modelo": _nombre_modelo_amigable(seleccionado) if seleccionado else "No disponible",
        "estrategia_prediccion": build_prediction_strategy(_cargar_bundle()["modelo"]).name,
        "modelo_clave": seleccionado or "",
        "comparacion_modelos": comparacion_modelos,
        "variables_importantes": variables_importantes,
        "metodo_importancia": importancia.get("metodo", "") if importancia else "",
        "descripcion_importancia": importancia.get("descripcion", "") if importancia else "",
        "f1_base_importancia": round(float(importancia.get("f1_base_muestra", 0)) * 100, 2) if importancia else 0,
        "filas_importancia": int(importancia.get("filas_test_evaluadas", 0)) if importancia else 0,
        "repeticiones_importancia": int(importancia.get("repeticiones", 0)) if importancia else 0,
        "accuracy": round(float(met_modelo.get("accuracy", 0)) * 100, 2),
        "precision": round(float(met_modelo.get("precision", 0)) * 100, 2),
        "recall": round(float(met_modelo.get("recall", 0)) * 100, 2),
        "f1": round(float(met_modelo.get("f1", 0)) * 100, 2),
        "umbral": round(umbral_alto_operativo * 100, 2),
        "umbral_medio": round(umbral_medio_operativo * 100, 2),
        "umbral_modelo_validado": round(umbral_modelo_validado * 100, 2),
        "recall_objetivo": round(float(metricas.get("recall_objetivo", 0.8)) * 100, 0),
        "cumple_recall": float(met_modelo.get("recall", 0)) >= float(metricas.get("recall_objetivo", 0.8)),
        "metodologia_validacion": metricas.get("metodologia_validacion", "Split temporal"),
        "productos": datos,
    }


def buscar_producto_prediccion(
    texto: str,
    inventario_mysql: Optional[List[Dict]] = None,
    stock_override: Optional[Dict[str, float]] = None,
):
    datos = predecir_riesgo_todos(
        inventario_mysql=inventario_mysql,
        stock_override=stock_override,
    )
    nombres = [item["producto"] for item in datos]
    if not nombres:
        return None

    texto_norm = _normalizar_clave_producto(texto)
    mejor_nombre = None
    mejor_score = 0.0

    for nombre in nombres:
        nombre_norm = _normalizar_clave_producto(nombre)
        score = SequenceMatcher(None, texto_norm, nombre_norm).ratio()
        if nombre_norm in texto_norm:
            score = 1.0
        if score > mejor_score:
            mejor_score = score
            mejor_nombre = nombre

    if mejor_nombre is None or mejor_score < 0.62:
        return None

    return next((item for item in datos if item["producto"] == mejor_nombre), None)


class StockPredictionEngine:
    """Adaptador de infraestructura para el motor predictivo de stock.

    Expone una interfaz pequeña a la capa de aplicación y encapsula las
    funciones internas de carga del bundle, preparación de features e inferencia.
    """

    def summary(self, *, inventory=None) -> dict:
        return obtener_resumen_predicciones(inventario_mysql=inventory)

    def predict_all(self, *, inventory=None) -> list[dict]:
        return predecir_riesgo_todos(inventario_mysql=inventory)

    def find_from_text(self, texto: str, *, inventory=None):
        return buscar_producto_prediccion(texto, inventario_mysql=inventory)
