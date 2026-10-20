import csv
from pathlib import Path
import pytest
from scripts.database.init_schema import REQUIRED, apply_schema, seed_stock, verify_columns

class Cursor:
    def __init__(self,rows=None,count=0): self.rows=rows or [];self.count=count;self.queries=[];self.params=[]
    def execute(self,query,params=None):self.queries.append(query);self.params.append(params)
    def executemany(self,query,rows):self.queries.append(query);self.params.append(rows)
    def fetchall(self):return self.rows
    def fetchone(self):return (self.count,)

def test_schema_has_four_tables():
    cursor=Cursor()
    assert apply_schema(cursor)==4
    assert len(cursor.queries)==4
    assert all('CREATE TABLE IF NOT EXISTS' in s for s in cursor.queries)

def test_schema_check_rejects_missing_columns():
    cursor=Cursor([('productos','id')]);missing=verify_columns(cursor,'test_db')
    assert set(missing)==set(REQUIRED)
    assert 'producto_id' in missing['productos']

def test_schema_check_accepts_full_schema():
    cursor=Cursor([(t,k) for t,columns in REQUIRED.items() for k in columns])
    assert verify_columns(cursor,'test_db')=={}

def test_seed_requires_empty_products(tmp_path):
    cursor=Cursor(count=1)
    with pytest.raises(ValueError,match='no está vacía'):
        seed_stock(cursor,tmp_path/'any.csv')

def test_seed_import_without_invented_expiration(tmp_path):
    p=tmp_path/'stock.csv'
    with p.open('w',encoding='utf8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['producto_id','producto','categoria','stock_actual','stock_seguridad','punto_reorden','lead_time_dias'])
        writer.writeheader();writer.writerow(dict(producto_id='P001',producto='Demo',categoria='Medicamento',stock_actual='10',stock_seguridad='4',punto_reorden='8',lead_time_dias='2'))
    cursor=Cursor()
    assert seed_stock(cursor,p)==1
    assert len(cursor.params[-1][0])==8
    assert cursor.params[-1][0][0]=='P001'

def test_duplicate_seed_rows_not_allowed(tmp_path):
    p=tmp_path/'stock.csv'
    p.write_text('producto_id,producto,categoria,stock_actual,stock_seguridad,punto_reorden,lead_time_dias\nP001,Demo,C,10,1,2,3\nP001,Demo,C,10,1,2,3\n')
    with pytest.raises(ValueError,match='duplicados'):
        seed_stock(Cursor(),p)
