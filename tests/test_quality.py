from datetime import date
from pathlib import Path
import pandas as pd
from app.application.services.data_quality_service import DataQualityService

class InventoryRepo:
    def __init__(self, rows):self.rows=rows
    def get_prediction_inventory(self):return self.rows

def row(pid, stock=10, safety=5, reorder=8, lead=3):
    return dict(producto_id=pid, stock_actual=stock, stock_seguridad=safety,
                punto_reorden=reorder, lead_time_dias=lead)

def baseline(tmp_path):
    f=tmp_path/'base.csv'
    ids=[f'P{i:03d}' for i in range(1,21)]
    pd.DataFrame([dict(fecha='2026-10-17',producto_id=pid,stock_actual=i+1,
                       stock_seguridad=3,punto_reorden=5,lead_time_dias=3)
                  for i,pid in enumerate(ids)]).to_csv(f,index=False)
    return f,ids

def test_good_data(tmp_path):
    f,ids=baseline(tmp_path)
    report=DataQualityService(InventoryRepo([row(pid,stock=i+1) for i,pid in enumerate(ids)]),f).audit(today=date(2026,10,18))
    assert report['estado']=='OK'
    assert report['productos_comparables']==20
    assert report['psi_stock']==0.0
    assert report['productos_sin_historial']==0

def test_stale_reference(tmp_path):
    f,ids=baseline(tmp_path)
    report=DataQualityService(InventoryRepo([row(ids[0])]),f).audit(today=date(2026,11,1))
    assert report['estado']=='REVISAR'
    assert report['dias_desde_corte']==15

def test_missing_duplicate_invalid(tmp_path):
    f,ids=baseline(tmp_path)
    report=DataQualityService(InventoryRepo([row('P001',stock=-1),row('P001'),row('P888')]),f).audit(today=date(2026,10,18))
    assert report['productos_con_campos_invalidos']==1
    assert report['productos_sin_historial']==1
    assert 'P001' in report['ids_duplicados']

def test_psi_high_when_distribution_changes(tmp_path):
    f,ids=baseline(tmp_path)
    report=DataQualityService(InventoryRepo([row(pid,stock=999+i) for i,pid in enumerate(ids)]),f).audit(today=date(2026,10,18))
    assert report['psi_stock'] is not None and report['psi_stock']>=0.25
    assert report['estado']=='REVISAR'

def test_empty_inventory(tmp_path):
    f,ids=baseline(tmp_path)
    report=DataQualityService(InventoryRepo([]),f).audit(today=date(2026,10,18))
    assert report['total_inventario']==0
    assert report['estado']=='REVISAR'
    assert report['psi_stock'] is None
