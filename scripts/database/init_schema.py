"""Comprobación/aplicación explícita del esquema MySQL y carga de stock CSV.

Uso: python -m scripts.database.init_schema --check
     python -m scripts.database.init_schema --apply
     python -m scripts.database.init_schema --seed-stock  # solo si tabla vacía

No sobrescribe filas de productos ni simula ubicaciones o vencimientos.
"""
from __future__ import annotations
import argparse
import csv
from pathlib import Path
from config import DB_CONFIG, DATA_DIR

SCHEMA = Path(__file__).with_name('schema.sql')
REQUIRED = {
    'productos': {'id','producto_id','producto','categoria','stock','stock_minimo',
                  'stock_seguridad','punto_reorden','lead_time_dias','ubicacion','lote',
                  'fecha_vencimiento','activo'},
    'historial_consultas': {'id','pregunta','intencion','producto','respuesta'},
    'evaluaciones_riesgo_stock': {'id','fecha_evaluacion','fecha_corte','horizonte_dias',
        'modelo','umbral_alto','umbral_medio','total_productos','alto_riesgo','medio_riesgo',
        'bajo_riesgo','probabilidad_promedio'},
    'historial_predicciones_stock': {'id','evaluacion_id','fecha_evaluacion','producto_id',
        'producto','categoria','stock_actual','demanda_estimada_7d','stock_proyectado_7d',
        'probabilidad_riesgo','nivel_riesgo'},
}

def verify_columns(cursor, database: str) -> dict:
    """Inspecciona estructura real: no depende de datos ficticios."""
    cursor.execute('''SELECT TABLE_NAME, COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                      WHERE TABLE_SCHEMA=%s''', (database,))
    actual = {}
    for table, column in cursor.fetchall():
        actual.setdefault(table, set()).add(column)
    missing = {table: sorted(columns - actual.get(table, set()))
               for table, columns in REQUIRED.items()}
    return {table: cols for table, cols in missing.items() if cols}

def apply_schema(cursor):
    content = SCHEMA.read_text(encoding='utf8')
    # SQL estático controlado por el proyecto; sin interpolación de inputs.
    statements = [s.strip() for s in content.split(';') if 'CREATE TABLE' in s.upper()]
    for statement in statements:
        # Retirar encabezados -- comentados para mejorar compatibilidad.
        statement = '\n'.join(line for line in statement.splitlines()
                              if not line.lstrip().startswith('--')).strip()
        if statement:
            cursor.execute(statement)
    return len(statements)

def seed_stock(cursor, csv_path: Path):
    cursor.execute('SELECT COUNT(*) FROM productos')
    if int(cursor.fetchone()[0]):
        raise ValueError('La tabla productos no está vacía: se cancela la carga para evitar sobrescrituras.')
    rows=[]
    with csv_path.open(newline='', encoding='utf-8-sig') as stream:
        reader=csv.DictReader(stream)
        for row in reader:
            rows.append((row['producto_id'],row['producto'],row['categoria'],
                        int(row['stock_actual']),int(row['stock_seguridad']),
                        int(row['stock_seguridad']),int(row['punto_reorden']),
                        max(1,int(row['lead_time_dias']))))
    ids=[row[0] for row in rows]
    if len(ids)!=len(set(ids)):
        raise ValueError('CSV contiene identificadores producto_id duplicados.')
    cursor.executemany('''INSERT INTO productos
        (producto_id,producto,categoria,stock,stock_minimo,stock_seguridad,
         punto_reorden,lead_time_dias) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',rows)
    return len(rows)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    opts=ap.add_mutually_exclusive_group(required=True)
    opts.add_argument('--check',action='store_true')
    opts.add_argument('--apply',action='store_true')
    opts.add_argument('--seed-stock',action='store_true')
    args=ap.parse_args()
    import mysql.connector
    conn=mysql.connector.connect(**DB_CONFIG)
    try:
        cursor=conn.cursor()
        if args.apply:
            amount=apply_schema(cursor);conn.commit()
            print(f'Se verificó/aplicó DDL de {amount} tablas (CREATE TABLE IF NOT EXISTS).')
        elif args.seed_stock:
            amount=seed_stock(cursor,DATA_DIR/'inventario_actual.csv');conn.commit()
            print(f'Productos cargados: {amount}; lotes, ubicación y vencimientos no simulados.')
        errors=verify_columns(cursor,DB_CONFIG['database'])
        if errors:
            print('Columnas faltantes:', errors)
            return 1
        print('OK: estructura requerida por los repositorios disponible.')
        return 0
    except Exception:
        conn.rollback();raise
    finally:
        conn.close()

if __name__=='__main__':
    raise SystemExit(main())
