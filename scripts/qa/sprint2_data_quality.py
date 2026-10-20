"""Verificación reproducible de los entregables PB05-PB07 del Sprint 2.

No modifica CSV, MySQL ni modelos entrenados. El umbral de nulos se toma del
apartado 3.10 del informe (menos de 5 %). No es una medición PRE/POS.

Uso: python -m scripts.qa.sprint2_data_quality --output build/reports/sprint2_datos.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import pandas as pd

from config import DATA_DIR

HISTORICAL_COLUMNS = {'fecha', 'producto_id', 'producto', 'categoria', 'tienda_id', 'ventas', 'promocion'}
INVENTORY_COLUMNS = {'producto_id', 'producto', 'categoria', 'stock_actual', 'stock_seguridad', 'punto_reorden', 'lead_time_dias'}
FEATURE_COLUMNS = {'producto_id', 'ventas_7d', 'ventas_14d', 'ventas_30d', 'dias_cobertura_7',
                   'dias_cobertura_30', 'tendencia_7_30', 'lead_time_dias', 'stock_actual'}


def _load_csv(path: Path, cols: set[str]) -> pd.DataFrame:
    if not path.is_file():
        raise ValueError(f'No existe el archivo obligatorio: {path.name}')
    frame = pd.read_csv(path, encoding='utf-8-sig', low_memory=False)
    missing = sorted(cols - set(frame.columns))
    if missing:
        raise ValueError(f'{path.name}: columnas requeridas ausentes: {missing}')
    if frame.empty:
        raise ValueError(f'{path.name}: archivo sin registros')
    return frame


def audit_files(data_dir: Path) -> dict:
    """Devuelve auditoría objetiva del dataset, inventario y variables Sprint 2."""
    history = _load_csv(data_dir / 'dataset_veterinario.csv', HISTORICAL_COLUMNS)
    inventory = _load_csv(data_dir / 'inventario_actual.csv', INVENTORY_COLUMNS)
    features = _load_csv(data_dir / 'features_actuales_7d.csv', FEATURE_COLUMNS)

    date = pd.to_datetime(history['fecha'], errors='coerce')
    bad_dates = int(date.isna().sum())
    key_duplicates = int(history.duplicated(['fecha', 'producto_id', 'tienda_id']).sum())
    inventory_duplicates = int(inventory.duplicated(['producto_id']).sum())
    features_duplicates = int(features.duplicated(['producto_id']).sum())
    history_missing = int(history[list(HISTORICAL_COLUMNS)].isna().sum().sum())
    inventory_missing = int(inventory[list(INVENTORY_COLUMNS)].isna().sum().sum())
    feature_missing = int(features[list(FEATURE_COLUMNS)].isna().sum().sum())
    required_cells = (len(history) * len(HISTORICAL_COLUMNS) +
                      len(inventory) * len(INVENTORY_COLUMNS) +
                      len(features) * len(FEATURE_COLUMNS))
    missing_rate = 100 * (history_missing + inventory_missing + feature_missing) / required_cells
    negative_sales = int((pd.to_numeric(history['ventas'], errors='coerce') < 0).sum())
    negative_stock = int((pd.to_numeric(inventory['stock_actual'], errors='coerce') < 0).sum())
    invalid_lead = int((pd.to_numeric(inventory['lead_time_dias'], errors='coerce') <= 0).sum())
    historical_products = set(history['producto_id'].dropna().astype(str))
    inventory_products = set(inventory['producto_id'].dropna().astype(str))
    feature_products = set(features['producto_id'].dropna().astype(str))
    missing_inventory_features = sorted(inventory_products - feature_products)
    missing_in_historical = sorted(inventory_products - historical_products)
    issues = []
    if bad_dates: issues.append('Fechas inválidas en histórico')
    if key_duplicates: issues.append('Claves fecha-producto-tienda duplicadas')
    if inventory_duplicates or features_duplicates: issues.append('Productos duplicados en stock o variables')
    if missing_rate >= 5: issues.append('Nulos >= 5 % en columnas obligatorias')
    if negative_sales or negative_stock or invalid_lead: issues.append('Valores operativos fuera de rango')
    if missing_inventory_features or missing_in_historical: issues.append('Productos sin correspondencia histórico/inventario/features')
    return {
        'sprint':'Sprint 2', 'backlog':['PB05','PB06','PB07'],
        'fuentes':['dataset_veterinario.csv','inventario_actual.csv','features_actuales_7d.csv'],
        'historico_filas':int(len(history)),
        'historico_productos':len(historical_products),
        'historico_fecha_inicio':str(date.min().date()) if bad_dates<len(date) else None,
        'historico_fecha_fin':str(date.max().date()) if bad_dates<len(date) else None,
        'historico_claves_duplicadas':key_duplicates,
        'inventario_productos':int(len(inventory)),
        'variables_registros':int(len(features)),
        'campos_variables_verificados':sorted(FEATURE_COLUMNS),
        'fechas_historicas_invalidas':bad_dates,
        'porcentaje_nulos_requeridos':round(float(missing_rate),5),
        'ventas_negativas':negative_sales,
        'stock_negativo':negative_stock,
        'lead_time_no_positivo':invalid_lead,
        'productos_inventario_sin_variables':len(missing_inventory_features),
        'productos_inventario_sin_historico':len(missing_in_historical),
        'incidencias':issues,
        'resultado':'APROBADO' if not issues else 'REVISAR',
        'alcance':'Auditoría de archivos del Sprint 2; no reentrena el modelo ni valida MySQL operativo ni demuestra impacto PRE/POS.'
    }


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,default=DATA_DIR)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        report=audit_files(args.data_dir)
    except (ValueError, OSError, pd.errors.ParserError) as e:
        print(f'ERROR Sprint 2: {e}')
        return 2
    text=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(text+'\n',encoding='utf-8')
    print(text)
    return 0 if report['resultado']=='APROBADO' else 1


if __name__=='__main__':
    raise SystemExit(main())
