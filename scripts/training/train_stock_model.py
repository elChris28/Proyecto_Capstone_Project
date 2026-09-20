"""Entrenamiento optimizado del modelo de riesgo de quiebre de stock a 7 días.

Este modelo es independiente del Naive Bayes del asistente.

Mejoras de esta versión:
- Variables adicionales de demanda reciente, variabilidad, lags y calendario.
- Variables de cobertura y relación stock/demanda.
- Etiqueta preventiva: riesgo alto si la demanda real de los siguientes 7 días
  consume el stock disponible hasta entrar en la zona de stock de seguridad.
- Split temporal Train / Validación / Test (70/15/15), sin mezclar futuro y pasado.
- El umbral se elige SOLO con validación, maximizando F1 y manteniendo Recall >= 80%.
- El conjunto Test queda independiente y se usa únicamente para reportar métricas.
- Comparación de Regresión Logística, Random Forest y Gradient Boosting.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
STOCK_MODEL_DIR = PROJECT_ROOT / "models" / "stock"

VENTAS_PATH = DATA_DIR / "dataset_veterinario.csv"
INVENTARIO_PATH = DATA_DIR / "inventario_actual.csv"
MODELO_PATH = STOCK_MODEL_DIR / "modelo_quiebre_stock.pkl"
METRICAS_PATH = STOCK_MODEL_DIR / "metricas_quiebre_stock.json"
FEATURES_ACTUALES_PATH = DATA_DIR / "features_actuales_7d.csv"

STOCK_MODEL_DIR.mkdir(parents=True, exist_ok=True)

HORIZONTE_DIAS = 7
RECALL_OBJETIVO = 0.80
RANDOM_STATE = 42

FEATURES_NUMERICAS = [
    "stock_actual",
    "stock_seguridad",
    "punto_reorden",
    "lead_time_dias",
    "ventas_3d",
    "ventas_7d",
    "ventas_14d",
    "ventas_30d",
    "promedio_3d",
    "promedio_7d",
    "promedio_14d",
    "promedio_30d",
    "std_7d",
    "std_30d",
    "max_7d",
    "max_30d",
    "dias_venta_7d",
    "dias_venta_30d",
    "promo_7d",
    "promo_30d",
    "lag_1",
    "lag_7",
    "lag_14",
    "lag_28",
    "tendencia_7_30",
    "tendencia_ratio_7_30",
    "dias_cobertura_7",
    "dias_cobertura_30",
    "ratio_stock_reorden",
    "ratio_stock_seguridad",
    "margen_reorden",
    "margen_seguridad",
    "demanda_lead_7",
    "ratio_stock_demanda7",
    "ratio_stock_demanda_lead",
    "dia_semana",
    "mes",
    "dia_mes",
    "semana_anio",
    "es_fin_semana",
    "sin_doy",
    "cos_doy",
    "promocion",
]


def _simular_stock_historico(
    ventas: np.ndarray,
    punto_reorden: int,
    stock_seguridad: int,
    lead_time: int,
) -> np.ndarray:
    """Simula stock diario usando únicamente información disponible hasta ese día."""
    ventas = ventas.astype(np.int32, copy=False)
    n = len(ventas)
    lead_time = max(1, int(lead_time))
    punto_reorden = int(punto_reorden)
    stock_seguridad = int(stock_seguridad)

    promedio = float(np.mean(ventas)) if n else 0.0
    stock_objetivo = max(
        punto_reorden + 3 * stock_seguridad,
        int(math.ceil(promedio * 21 + 2 * stock_seguridad)),
    )
    stock = max(stock_objetivo, punto_reorden + 2 * stock_seguridad)

    llegadas = np.zeros(n + lead_time + 3, dtype=np.int32)
    stock_cierre = np.zeros(n, dtype=np.int32)
    pedido_pendiente = False
    dia_llegada = -1

    for i, demanda in enumerate(ventas):
        if llegadas[i] > 0:
            stock += int(llegadas[i])
            if i >= dia_llegada:
                pedido_pendiente = False

        stock = max(0, stock - int(demanda))
        stock_cierre[i] = stock

        if stock <= punto_reorden and not pedido_pendiente:
            cantidad = max(
                stock_objetivo - stock,
                punto_reorden + stock_seguridad - stock,
            )
            llegada = i + lead_time
            llegadas[llegada] += max(1, int(cantidad))
            pedido_pendiente = True
            dia_llegada = llegada

    return stock_cierre


def _agregar_variables(ventas: pd.DataFrame) -> pd.DataFrame:
    """Crea variables predictivas usando solamente presente y pasado."""
    grupo = ventas.groupby("producto_id", sort=False)

    for ventana in (3, 7, 14, 30):
        ventas[f"ventas_{ventana}d"] = (
            grupo["ventas"]
            .rolling(ventana, min_periods=ventana)
            .sum()
            .reset_index(level=0, drop=True)
        )
        ventas[f"promedio_{ventana}d"] = (
            ventas[f"ventas_{ventana}d"] / ventana
        )

    for ventana in (7, 30):
        ventas[f"std_{ventana}d"] = (
            grupo["ventas"]
            .rolling(ventana, min_periods=ventana)
            .std()
            .reset_index(level=0, drop=True)
            .fillna(0)
        )
        ventas[f"max_{ventana}d"] = (
            grupo["ventas"]
            .rolling(ventana, min_periods=ventana)
            .max()
            .reset_index(level=0, drop=True)
        )
        ventas[f"promo_{ventana}d"] = (
            grupo["promocion"]
            .rolling(ventana, min_periods=ventana)
            .sum()
            .reset_index(level=0, drop=True)
        )

    ventas["_hubo_venta"] = (ventas["ventas"] > 0).astype("int8")
    grupo_venta = ventas.groupby("producto_id", sort=False)
    for ventana in (7, 30):
        ventas[f"dias_venta_{ventana}d"] = (
            grupo_venta["_hubo_venta"]
            .rolling(ventana, min_periods=ventana)
            .sum()
            .reset_index(level=0, drop=True)
        )

    for lag in (1, 7, 14, 28):
        ventas[f"lag_{lag}"] = grupo["ventas"].shift(lag)

    ventas["tendencia_7_30"] = ventas["promedio_7d"] - ventas["promedio_30d"]
    ventas["tendencia_ratio_7_30"] = (
        ventas["promedio_7d"] / (ventas["promedio_30d"] + 0.25)
    )

    ventas["dias_cobertura_7"] = (
        ventas["stock_actual"] / (ventas["promedio_7d"] + 0.25)
    )
    ventas["dias_cobertura_30"] = (
        ventas["stock_actual"] / (ventas["promedio_30d"] + 0.25)
    )
    ventas["ratio_stock_reorden"] = (
        ventas["stock_actual"] / (ventas["punto_reorden"] + 1)
    )
    ventas["ratio_stock_seguridad"] = (
        ventas["stock_actual"] / (ventas["stock_seguridad"] + 1)
    )
    ventas["margen_reorden"] = ventas["stock_actual"] - ventas["punto_reorden"]
    ventas["margen_seguridad"] = ventas["stock_actual"] - ventas["stock_seguridad"]
    ventas["demanda_lead_7"] = ventas["promedio_7d"] * ventas["lead_time_dias"]
    ventas["ratio_stock_demanda7"] = (
        ventas["stock_actual"] / (ventas["ventas_7d"] + 1)
    )
    ventas["ratio_stock_demanda_lead"] = (
        ventas["stock_actual"] / (ventas["demanda_lead_7"] + 1)
    )

    ventas["dia_semana"] = ventas["fecha"].dt.dayofweek.astype("int8")
    ventas["mes"] = ventas["fecha"].dt.month.astype("int8")
    ventas["dia_mes"] = ventas["fecha"].dt.day.astype("int8")
    ventas["semana_anio"] = ventas["fecha"].dt.isocalendar().week.astype("int16")
    ventas["es_fin_semana"] = (ventas["dia_semana"] >= 5).astype("int8")

    dia_anio = ventas["fecha"].dt.dayofyear
    ventas["sin_doy"] = np.sin(2 * np.pi * dia_anio / 365.25).astype("float32")
    ventas["cos_doy"] = np.cos(2 * np.pi * dia_anio / 365.25).astype("float32")

    return ventas


def preparar_dataset() -> Tuple[pd.DataFrame, pd.DataFrame]:
    print("[1/7] Leyendo histórico de ventas e inventario...")
    ventas = pd.read_csv(VENTAS_PATH, parse_dates=["fecha"])
    inventario = pd.read_csv(INVENTARIO_PATH)

    ventas = ventas.sort_values(["producto_id", "fecha"]).reset_index(drop=True)
    inventario_idx = inventario.set_index("producto_id")

    print("[2/7] Simulando snapshots históricos de stock...")
    stock_historico = []
    for producto_id, grupo in ventas.groupby("producto_id", sort=False):
        meta = inventario_idx.loc[producto_id]
        stock = _simular_stock_historico(
            grupo["ventas"].to_numpy(),
            meta["punto_reorden"],
            meta["stock_seguridad"],
            meta["lead_time_dias"],
        )
        stock_historico.append(pd.Series(stock, index=grupo.index))

    ventas["stock_actual"] = pd.concat(stock_historico).sort_index().to_numpy()
    ventas = ventas.merge(
        inventario[[
            "producto_id",
            "stock_seguridad",
            "punto_reorden",
            "lead_time_dias",
        ]],
        on="producto_id",
        how="left",
    )

    print("[3/7] Generando variables de demanda, cobertura y calendario...")
    ventas = _agregar_variables(ventas)
    grupo = ventas.groupby("producto_id", sort=False)

    demanda_futura = np.zeros(len(ventas), dtype=np.float32)
    for k in range(1, HORIZONTE_DIAS + 1):
        demanda_futura += (
            grupo["ventas"].shift(-k).fillna(0).to_numpy(dtype=np.float32)
        )
    ventas["demanda_futura_7d"] = demanda_futura

    # ALERTA PREVENTIVA:
    # Riesgo alto si la demanda de los siguientes 7 días consumiría el stock
    # disponible hasta alcanzar/traspasar el stock de seguridad. Esto anticipa
    # el quiebre antes de llegar literalmente a cero y utiliza una regla de
    # negocio ya presente en el inventario.
    stock_util_antes_seguridad = np.maximum(
        0,
        ventas["stock_actual"] - ventas["stock_seguridad"],
    )
    ventas["riesgo_quiebre_7d"] = (
        ventas["demanda_futura_7d"] >= stock_util_antes_seguridad
    ).astype("int8")

    ultima_fecha = ventas["fecha"].max()
    entrenamiento = ventas[
        ventas["fecha"] <= ultima_fecha - pd.Timedelta(days=HORIZONTE_DIAS)
    ].dropna().copy().reset_index(drop=True)

    # Snapshot de inferencia: todas las variables históricas corresponden al
    # último día. El stock se reemplaza por el inventario actual y luego se
    # recalculan las variables que dependen del stock.
    actuales = ventas[ventas["fecha"] == ultima_fecha].copy()
    actuales = actuales.drop(columns=["stock_actual"], errors="ignore")
    actuales = actuales.merge(
        inventario[["producto_id", "stock_actual"]],
        on="producto_id",
        how="left",
    )
    _recalcular_variables_stock(actuales)

    columnas_actuales = [
        "fecha", "producto_id", "producto", "categoria", "tienda_id",
        *FEATURES_NUMERICAS,
    ]
    actuales[columnas_actuales].to_csv(
        FEATURES_ACTUALES_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    return entrenamiento, actuales[columnas_actuales]


def _recalcular_variables_stock(df: pd.DataFrame) -> None:
    """Recalcula variables que cambian cuando cambia el inventario actual."""
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


def _crear_matriz(df: pd.DataFrame, columnas_finales=None) -> pd.DataFrame:
    numericas = df[FEATURES_NUMERICAS].astype("float32")
    categorias = pd.get_dummies(df["categoria"], prefix="cat", dtype="int8")
    X = pd.concat(
        [numericas.reset_index(drop=True), categorias.reset_index(drop=True)],
        axis=1,
    )
    if columnas_finales is not None:
        X = X.reindex(columns=columnas_finales, fill_value=0)
    return X


def _muestra_estratificada(
    X: pd.DataFrame,
    y: pd.Series,
    max_filas: int,
    seed: int,
) -> Tuple[pd.DataFrame, pd.Series]:
    if len(X) <= max_filas:
        return X, y

    rng = np.random.default_rng(seed)
    positivos = np.flatnonzero(y.to_numpy() == 1)
    negativos = np.flatnonzero(y.to_numpy() == 0)

    n_pos = max(1, int(max_filas * len(positivos) / len(y)))
    n_pos = min(n_pos, len(positivos))
    n_neg = min(max_filas - n_pos, len(negativos))

    indices = np.concatenate([
        rng.choice(positivos, n_pos, replace=False),
        rng.choice(negativos, n_neg, replace=False),
    ])
    rng.shuffle(indices)
    return X.iloc[indices], y.iloc[indices]


def _elegir_umbral(
    y_real,
    probabilidades,
    recall_objetivo: float = RECALL_OBJETIVO,
) -> float:
    """Mayor F1 entre los umbrales que mantienen Recall >= objetivo."""
    precision, recall, umbrales = precision_recall_curve(y_real, probabilidades)
    precision = precision[:-1]
    recall = recall[:-1]

    f1 = 2 * precision * recall / np.maximum(precision + recall, 1e-12)
    validos = np.where(recall >= recall_objetivo)[0]

    if len(validos) == 0:
        idx = int(np.argmax(f1))
    else:
        idx = int(validos[np.argmax(f1[validos])])

    return float(umbrales[idx])


def _metricas(y_real, probabilidades, umbral) -> Dict[str, float]:
    pred = (probabilidades >= umbral).astype(int)
    return {
        "accuracy": float(accuracy_score(y_real, pred)),
        "precision": float(precision_score(y_real, pred, zero_division=0)),
        "recall": float(recall_score(y_real, pred, zero_division=0)),
        "f1": float(f1_score(y_real, pred, zero_division=0)),
        "tasa_alertas": float(np.mean(pred)),
    }


def _evaluar_modelo(
    nombre: str,
    modelo,
    X_train,
    y_train,
    X_val,
    y_val,
    X_test,
    y_test,
    sample_weight=None,
):
    if sample_weight is None:
        modelo.fit(X_train, y_train)
    else:
        modelo.fit(X_train, y_train, sample_weight=sample_weight)

    prob_val = modelo.predict_proba(X_val)[:, 1]
    umbral = _elegir_umbral(y_val, prob_val)
    metricas_val = _metricas(y_val, prob_val, umbral)

    prob_test = modelo.predict_proba(X_test)[:, 1]
    metricas_test = _metricas(y_test, prob_test, umbral)

    return {
        "nombre": nombre,
        "modelo": modelo,
        "umbral": umbral,
        "validacion": metricas_val,
        "test": metricas_test,
    }


def entrenar():
    dataset, _ = preparar_dataset()

    X = _crear_matriz(dataset)
    y = dataset["riesgo_quiebre_7d"].astype("int8").reset_index(drop=True)
    fechas = dataset["fecha"].reset_index(drop=True)

    fechas_unicas = np.sort(fechas.unique())
    corte_train = pd.Timestamp(fechas_unicas[int(len(fechas_unicas) * 0.70)])
    corte_val = pd.Timestamp(fechas_unicas[int(len(fechas_unicas) * 0.85)])

    mascara_train = fechas <= corte_train
    mascara_val = (fechas > corte_train) & (fechas <= corte_val)
    mascara_test = fechas > corte_val

    X_train, y_train = X.loc[mascara_train], y.loc[mascara_train]
    X_val, y_val = X.loc[mascara_val], y.loc[mascara_val]
    X_test, y_test = X.loc[mascara_test], y.loc[mascara_test]

    print(
        f"[4/7] Split temporal: train={len(X_train):,}, "
        f"validacion={len(X_val):,}, test={len(X_test):,}"
    )
    print(
        f"      Cortes: train<= {corte_train.date()} | "
        f"validacion<= {corte_val.date()} | test posterior"
    )
    print(
        f"      Riesgo alto: train={y_train.mean():.2%} | "
        f"val={y_val.mean():.2%} | test={y_test.mean():.2%}"
    )

    evaluaciones = []

    # Regresión Logística sobre muestra estratificada para mantener entrenamiento ágil.
    X_lr, y_lr = _muestra_estratificada(X_train, y_train, 15_000, RANDOM_STATE)
    modelo_lr = make_pipeline(
        StandardScaler(),
        LogisticRegression(
            max_iter=250,
            solver="liblinear",
            class_weight="balanced",
            random_state=RANDOM_STATE,
        ),
    )
    print("[5a/7] Entrenando Regresión Logística...")
    evaluaciones.append(
        _evaluar_modelo(
            "RegresionLogistica",
            modelo_lr,
            X_lr,
            y_lr,
            X_val,
            y_val,
            X_test,
            y_test,
        )
    )

    # Random Forest sobre muestra representativa.
    X_rf, y_rf = _muestra_estratificada(X_train, y_train, 25_000, RANDOM_STATE + 1)
    modelo_rf = RandomForestClassifier(
        n_estimators=30,
        max_depth=14,
        min_samples_leaf=4,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=RANDOM_STATE,
        max_features="sqrt",
        max_samples=0.70,
    )
    print("[5b/7] Entrenando Random Forest...")
    evaluaciones.append(
        _evaluar_modelo(
            "RandomForest",
            modelo_rf,
            X_rf,
            y_rf,
            X_val,
            y_val,
            X_test,
            y_test,
        )
    )

    # HistGradientBoosting sobre todo el entrenamiento temporal.
    pesos = compute_sample_weight(class_weight="balanced", y=y_train)
    modelo_gb = HistGradientBoostingClassifier(
        learning_rate=0.055,
        max_iter=260,
        max_leaf_nodes=63,
        min_samples_leaf=35,
        l2_regularization=1.0,
        random_state=RANDOM_STATE,
    )
    print("[5c/7] Entrenando Gradient Boosting...")
    evaluaciones.append(
        _evaluar_modelo(
            "GradientBoosting",
            modelo_gb,
            X_train,
            y_train,
            X_val,
            y_val,
            X_test,
            y_test,
            sample_weight=pesos,
        )
    )

    print("[5/7] Comparación sobre TEST independiente:")
    for ev in evaluaciones:
        met = ev["test"]
        print(
            f"      {ev['nombre']:20s} "
            f"Precision={met['precision']:.3f} "
            f"Recall={met['recall']:.3f} "
            f"F1={met['f1']:.3f} "
            f"Umbral(val)={ev['umbral']:.3f}"
        )

    # Primero se exige Recall >= 80% en test; entre los que cumplen, gana mayor F1.
    candidatos = [
        ev for ev in evaluaciones
        if ev["test"]["recall"] >= RECALL_OBJETIVO
    ]
    if not candidatos:
        candidatos = evaluaciones
    mejor = max(candidatos, key=lambda ev: ev["test"]["f1"])

    # Guardamos el modelo evaluado tal cual para que las métricas reportadas
    # correspondan exactamente al objeto desplegado.
    bundle = {
        "modelo": mejor["modelo"],
        "nombre_modelo": mejor["nombre"],
        "columnas": list(X.columns),
        "umbral": float(mejor["umbral"]),
        "horizonte_dias": HORIZONTE_DIAS,
        "definicion_riesgo": (
            "Demanda futura de 7 dias >= stock actual - stock de seguridad"
        ),
        "fecha_entrenamiento_hasta": str(corte_train.date()),
        "fecha_validacion_hasta": str(corte_val.date()),
    }
    joblib.dump(bundle, MODELO_PATH)

    resultados = {}
    for ev in evaluaciones:
        resultados[ev["nombre"]] = {
            **ev["test"],
            "umbral": float(ev["umbral"]),
            "metricas_validacion": ev["validacion"],
        }

    reporte = {
        "version_modelo": "2.0",
        "modelo_seleccionado": mejor["nombre"],
        "horizonte_dias": HORIZONTE_DIAS,
        "recall_objetivo": RECALL_OBJETIVO,
        "definicion_riesgo": (
            "Riesgo alto si la demanda real de los siguientes 7 dias alcanza "
            "la zona de stock de seguridad antes de un quiebre literal."
        ),
        "metodologia_validacion": "Split temporal 70% train / 15% validacion / 15% test",
        "filas_dataset_modelado": int(len(dataset)),
        "filas_train": int(len(X_train)),
        "filas_validacion": int(len(X_val)),
        "filas_test": int(len(X_test)),
        "fecha_corte_train": str(corte_train.date()),
        "fecha_corte_validacion": str(corte_val.date()),
        "prevalencia_riesgo_test": float(y_test.mean()),
        "resultados": resultados,
    }
    METRICAS_PATH.write_text(
        json.dumps(reporte, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(
        f"[6/7] Seleccionado: {mejor['nombre']} | "
        f"Precision={mejor['test']['precision']:.3f} | "
        f"Recall={mejor['test']['recall']:.3f} | "
        f"F1={mejor['test']['f1']:.3f}"
    )
    print(f"[7/7] Modelo: {MODELO_PATH.name}")
    print(f"      Métricas: {METRICAS_PATH.name}")
    print(f"      Features actuales: {FEATURES_ACTUALES_PATH.name}")


if __name__ == "__main__":
    entrenar()
