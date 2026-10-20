from pathlib import Path
import json
import pandas as pd
from config import DATA_DIR, METRICAS_QUIEBRE_PATH
from app.infrastructure.ml.stock_predictor import obtener_resumen_predicciones

def test_reference_model_outputs_500_with_consistent_distribution():
    csv=DATA_DIR/'inventario_actual.csv'
    frame=pd.read_csv(csv,encoding='utf-8-sig')
    inventory=frame[['producto_id','producto','categoria','stock_actual','stock_seguridad',
                     'punto_reorden','lead_time_dias']].to_dict('records')
    result=obtener_resumen_predicciones(inventario_mysql=inventory)
    assert result['horizonte_dias']==7
    assert result['total_productos']==len(frame)==500
    assert result['alto_riesgo']+result['medio_riesgo']+result['bajo_riesgo']==500
    assert 0<=result['recall']<=100
    assert abs(result['recall']-81.48)<0.02
    assert all(p['clasificacion_binaria_modelo'] in ('RIESGO','NO_RIESGO') for p in result['productos'])
    assert all(0<=p['probabilidad_riesgo']<=1 for p in result['productos'])
    assert all(p['nivel_riesgo'] in ('BAJO','MEDIO','ALTO') for p in result['productos'])

def test_csv_and_model_baseline_are_distinct_sources():
    metrics=json.loads(METRICAS_QUIEBRE_PATH.read_text(encoding='utf8'))
    data=pd.read_csv(DATA_DIR/'dataset_veterinario.csv',usecols=['producto_id'])
    assert metrics['filas_dataset_modelado']==1021500
    assert len(data)==1039500
    # El proyecto documenta la diferencia; no se reentrenó ni alteró el modelo.
    assert len(data)-metrics['filas_dataset_modelado']==18000
