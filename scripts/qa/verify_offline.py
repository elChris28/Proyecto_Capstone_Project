"""Verifica en modo offline, sin modificar MySQL ni reentrenar el modelo.

python -m scripts.qa.verify_offline --output evidencias/verificacion_offline.json
"""
import argparse
from datetime import date
import json
from pathlib import Path
import pandas as pd
from config import DATA_DIR, METRICAS_QUIEBRE_PATH
from app.application.services.data_quality_service import DataQualityService
from app.infrastructure.ml.stock_predictor import obtener_resumen_predicciones

class StaticInventory:
    def __init__(self,items):self.items=items
    def get_prediction_inventory(self):return self.items

def run():
    frame=pd.read_csv(DATA_DIR/'inventario_actual.csv',encoding='utf-8-sig')
    columns=['producto_id','producto','categoria','stock_actual','stock_seguridad','punto_reorden','lead_time_dias']
    items=frame[columns].to_dict('records')
    summary=obtener_resumen_predicciones(inventario_mysql=items)
    quality=DataQualityService(StaticInventory(items)).audit()
    metricas=json.loads(METRICAS_QUIEBRE_PATH.read_text(encoding='utf8'))
    return {
        'modalidad':'offline sobre inventario_actual.csv; NO verifica MySQL ni UAT de usuarios',
        'fecha_de_ejecucion':str(date.today()),
        'modelo':summary['modelo'],
        'horizonte_dias':summary['horizonte_dias'],
        'productos_inventario_csv':len(items),
        'productos_evaluados':summary['total_productos'],
        'distribucion_riesgo_csv':{key:summary[key] for key in ['alto_riesgo','medio_riesgo','bajo_riesgo']},
        'recall_modelo_guardado_pct':summary['recall'],
        'f1_modelo_guardado_pct':summary['f1'],
        'umbral_binario_pct':summary['umbral_modelo_validado'],
        'registros_entrenamiento_guardados':metricas['filas_dataset_modelado'],
        'control_calidad':quality,
        'observacion':'Las cifras del CSV NO sustituyen las capturas del informe obtenidas con MySQL. No se reentrenó el modelo.'
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=None)
    args=parser.parse_args()
    data=run()
    raw=json.dumps(data,ensure_ascii=False,indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(raw+'\n',encoding='utf8')
    print(raw)
if __name__=='__main__':main()
