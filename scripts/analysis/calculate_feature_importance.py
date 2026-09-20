"""Calcula importancia de variables mediante Permutation Importance agrupada.

La evaluación se realiza sobre una muestra estratificada del conjunto TEST temporal,
utilizando el modelo desplegado y su umbral real. La importancia representa la caída
promedio del F1-Score al desordenar una variable; para la categoría se permutan de
forma conjunta todas sus columnas one-hot.

Uso recomendado:
    python -m scripts.analysis.calculate_feature_importance

Salida:
    models/stock/importancia_variables.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score

from scripts.training.train_stock_model import (
    RANDOM_STATE,
    _crear_matriz,
    _muestra_estratificada,
    preparar_dataset,
)

STOCK_MODEL_DIR = PROJECT_ROOT / "models" / "stock"
MODELO_PATH = STOCK_MODEL_DIR / "modelo_quiebre_stock.pkl"
SALIDA_PATH = STOCK_MODEL_DIR / "importancia_variables.json"
STOCK_MODEL_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILAS_TEST = 6000
REPETICIONES = 5

ETIQUETAS = {
    "stock_actual": "Stock actual",
    "stock_seguridad": "Stock de seguridad",
    "punto_reorden": "Punto de reorden",
    "lead_time_dias": "Tiempo de reposición (lead time)",
    "ventas_3d": "Ventas últimos 3 días",
    "ventas_7d": "Ventas últimos 7 días",
    "ventas_14d": "Ventas últimos 14 días",
    "ventas_30d": "Ventas últimos 30 días",
    "promedio_3d": "Promedio diario últimos 3 días",
    "promedio_7d": "Promedio diario últimos 7 días",
    "promedio_14d": "Promedio diario últimos 14 días",
    "promedio_30d": "Promedio diario últimos 30 días",
    "std_7d": "Variabilidad de ventas 7 días",
    "std_30d": "Variabilidad de ventas 30 días",
    "max_7d": "Venta máxima diaria 7 días",
    "max_30d": "Venta máxima diaria 30 días",
    "dias_venta_7d": "Días con venta en últimos 7 días",
    "dias_venta_30d": "Días con venta en últimos 30 días",
    "promo_7d": "Promociones últimos 7 días",
    "promo_30d": "Promociones últimos 30 días",
    "lag_1": "Venta del día anterior",
    "lag_7": "Venta de hace 7 días",
    "lag_14": "Venta de hace 14 días",
    "lag_28": "Venta de hace 28 días",
    "tendencia_7_30": "Tendencia de ventas 7 vs. 30 días",
    "tendencia_ratio_7_30": "Ratio de tendencia 7 vs. 30 días",
    "dias_cobertura_7": "Días de cobertura según demanda de 7 días",
    "dias_cobertura_30": "Días de cobertura según demanda de 30 días",
    "ratio_stock_reorden": "Relación stock / punto de reorden",
    "ratio_stock_seguridad": "Relación stock / stock de seguridad",
    "margen_reorden": "Margen sobre punto de reorden",
    "margen_seguridad": "Margen sobre stock de seguridad",
    "demanda_lead_7": "Demanda estimada durante lead time",
    "ratio_stock_demanda7": "Relación stock / demanda 7 días",
    "ratio_stock_demanda_lead": "Relación stock / demanda durante lead time",
    "dia_semana": "Día de la semana",
    "mes": "Mes",
    "dia_mes": "Día del mes",
    "semana_anio": "Semana del año",
    "es_fin_semana": "Indicador de fin de semana",
    "sin_doy": "Componente estacional anual (seno)",
    "cos_doy": "Componente estacional anual (coseno)",
    "promocion": "Promoción del día",
    "categoria": "Categoría del producto",
}


def _score(modelo, X: pd.DataFrame, y: pd.Series, umbral: float) -> float:
    prob = modelo.predict_proba(X)[:, 1]
    pred = (prob >= umbral).astype("int8")
    return float(f1_score(y, pred, zero_division=0))


def _grupos(columnas: List[str]) -> Dict[str, List[str]]:
    grupos: Dict[str, List[str]] = {}
    categorias = [c for c in columnas if c.startswith("cat_")]
    for col in columnas:
        if col.startswith("cat_"):
            continue
        grupos[col] = [col]
    if categorias:
        grupos["categoria"] = categorias
    return grupos


def calcular() -> Dict:
    print("[1/5] Cargando modelo desplegado...")
    bundle = joblib.load(MODELO_PATH)
    modelo = bundle["modelo"]
    columnas = list(bundle["columnas"])
    umbral = float(bundle["umbral"])

    print("[2/5] Reconstruyendo dataset modelado...")
    dataset, _ = preparar_dataset()
    X = _crear_matriz(dataset, columnas_finales=columnas)
    y = dataset["riesgo_quiebre_7d"].astype("int8").reset_index(drop=True)
    fechas = dataset["fecha"].reset_index(drop=True)

    fechas_unicas = np.sort(fechas.unique())
    corte_val = pd.Timestamp(fechas_unicas[int(len(fechas_unicas) * 0.85)])
    mascara_test = fechas > corte_val
    X_test = X.loc[mascara_test].reset_index(drop=True)
    y_test = y.loc[mascara_test].reset_index(drop=True)

    print(f"[3/5] Muestreando TEST: {len(X_test):,} filas -> máximo {MAX_FILAS_TEST:,}...")
    X_eval, y_eval = _muestra_estratificada(
        X_test,
        y_test,
        MAX_FILAS_TEST,
        RANDOM_STATE + 77,
    )
    X_eval = X_eval.reset_index(drop=True).copy()
    y_eval = y_eval.reset_index(drop=True)

    baseline = _score(modelo, X_eval, y_eval, umbral)
    print(f"      F1 base con umbral desplegado: {baseline:.4f}")

    grupos = _grupos(columnas)
    rng = np.random.default_rng(RANDOM_STATE + 991)
    resultados = []

    print(f"[4/5] Calculando importancia agrupada ({len(grupos)} variables, {REPETICIONES} repeticiones)...")
    for i, (variable, cols) in enumerate(grupos.items(), start=1):
        caidas = []
        for _ in range(REPETICIONES):
            perm = rng.permutation(len(X_eval))
            X_perm = X_eval.copy()
            # Permutar el bloque como unidad conserva una categoría one-hot válida.
            X_perm.loc[:, cols] = X_eval.loc[perm, cols].to_numpy()
            score_perm = _score(modelo, X_perm, y_eval, umbral)
            caidas.append(baseline - score_perm)

        media = float(np.mean(caidas))
        std = float(np.std(caidas))
        resultados.append({
            "variable": variable,
            "etiqueta": ETIQUETAS.get(variable, variable),
            "importancia_f1": media,
            "desviacion": std,
        })
        if i % 10 == 0 or i == len(grupos):
            print(f"      {i}/{len(grupos)} variables evaluadas")

    resultados.sort(key=lambda r: r["importancia_f1"], reverse=True)
    total_positivo = sum(max(0.0, r["importancia_f1"]) for r in resultados)
    for r in resultados:
        positivo = max(0.0, r["importancia_f1"])
        r["importancia_relativa_pct"] = round(
            (positivo / total_positivo * 100.0) if total_positivo > 0 else 0.0,
            2,
        )
        r["importancia_f1"] = round(r["importancia_f1"], 6)
        r["desviacion"] = round(r["desviacion"], 6)

    reporte = {
        "metodo": "Permutation Importance agrupada sobre TEST temporal",
        "descripcion": (
            "Caída promedio del F1-Score al permutar cada variable en el conjunto TEST. "
            "La categoría se permuta como un bloque one-hot. La evaluación usa el umbral "
            "real del modelo desplegado."
        ),
        "modelo": str(bundle.get("nombre_modelo", "")),
        "umbral": umbral,
        "f1_base_muestra": round(baseline, 6),
        "filas_test_evaluadas": int(len(X_eval)),
        "repeticiones": REPETICIONES,
        "fecha_corte_test_desde": str((corte_val + pd.Timedelta(days=1)).date()),
        "variables": resultados,
        "top_10": resultados[:10],
    }

    SALIDA_PATH.write_text(
        json.dumps(reporte, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[5/5] Guardado: {SALIDA_PATH.name}")
    return reporte


if __name__ == "__main__":
    rep = calcular()
    print("\nTop 10 variables:")
    for i, item in enumerate(rep["top_10"], start=1):
        print(
            f"{i:>2}. {item['etiqueta']:<48} "
            f"caída F1={item['importancia_f1']:.4f} "
            f"relativa={item['importancia_relativa_pct']:.1f}%"
        )
