from contextlib import contextmanager
from app.infrastructure.database.repositories.product_repository import ProductRepository

class Cursor:
    def __init__(self):self.sql=''
    def execute(self,sql,params=None):self.sql=sql
    def fetchall(self):return [(1,'P001','Producto A','Alimento',25,5,7,12,3)]
class DB:
    def __init__(self):self.cursor_obj=Cursor()
    @contextmanager
    def cursor(self,*args,**kwargs):yield None,self.cursor_obj

def test_inventory_one_row_per_product_with_sum():
    db=DB()
    products=ProductRepository(db).get_prediction_inventory()
    assert 'GROUP BY producto_id' in db.cursor_obj.sql
    assert 'SUM(stock)' in db.cursor_obj.sql
    assert len(products)==1
    assert products[0]['stock_actual']==25
