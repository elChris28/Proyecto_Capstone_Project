"""Pruebas del verificador PB05-PB07. Son controles técnicos, no PRE/POS."""
from pathlib import Path
import pandas as pd
import pytest
from scripts.qa.sprint2_data_quality import audit_files


def sample_data(folder: Path):
    pd.DataFrame([
        {'fecha':'2026-10-01','producto_id':'P1','producto':'Producto 1','categoria':'C','tienda_id':'T1','ventas':2,'promocion':0},
        {'fecha':'2026-10-02','producto_id':'P1','producto':'Producto 1','categoria':'C','tienda_id':'T1','ventas':1,'promocion':1}
    ]).to_csv(folder/'dataset_veterinario.csv',index=False)
    pd.DataFrame([{'producto_id':'P1','producto':'Producto 1','categoria':'C','stock_actual':11,
                   'stock_seguridad':4,'punto_reorden':7,'lead_time_dias':2}]).to_csv(folder/'inventario_actual.csv',index=False)
    pd.DataFrame([{'producto_id':'P1','stock_actual':11,'ventas_7d':3,'ventas_14d':3,
                   'ventas_30d':3,'dias_cobertura_7':10,'dias_cobertura_30':10,
                   'tendencia_7_30':1,'lead_time_dias':2}]).to_csv(folder/'features_actuales_7d.csv',index=False)


def test_sprint2_archivos_consistentes_aprobados(tmp_path):
    sample_data(tmp_path)
    actual=audit_files(tmp_path)
    assert actual['resultado']=='APROBADO'
    assert actual['historico_filas']==2
    assert actual['inventario_productos']==actual['variables_registros']==1


def test_sprint2_rechaza_duplicados_en_clave(tmp_path):
    sample_data(tmp_path)
    path=tmp_path/'dataset_veterinario.csv'
    df=pd.read_csv(path)
    pd.concat([df,df.iloc[[0]]],ignore_index=True).to_csv(path,index=False)
    actual=audit_files(tmp_path)
    assert actual['resultado']=='REVISAR'
    assert actual['historico_claves_duplicadas']==1


def test_sprint2_detecta_falta_de_variables(tmp_path):
    sample_data(tmp_path)
    path=tmp_path/'features_actuales_7d.csv'
    frame=pd.read_csv(path).drop(columns=['ventas_14d'])
    frame.to_csv(path,index=False)
    with pytest.raises(ValueError,match='columnas requeridas ausentes'):
        audit_files(tmp_path)


def test_sprint2_detecta_valor_operativo_invalido(tmp_path):
    sample_data(tmp_path)
    path=tmp_path/'inventario_actual.csv'
    frame=pd.read_csv(path)
    frame.loc[0,'stock_actual']=-2
    frame.to_csv(path,index=False)
    actual=audit_files(tmp_path)
    assert actual['stock_negativo']==1
    assert actual['resultado']=='REVISAR'
