from types import SimpleNamespace

def sample_summary():
    return dict(total_productos=2,productos=[dict(producto_id='P001',producto='Demo A',nivel_riesgo='ALTO'),dict(producto_id='P002',producto='Demo B',nivel_riesgo='BAJO')],alto_riesgo=1,medio_riesgo=0,bajo_riesgo=1)

class FakePrediction:
    def summary(self):return sample_summary()
    def product_detail(self,ident):
        return dict(producto={'producto_id':ident}) if ident=='P001' else None

class FakeQuality:
    def audit(self):return dict(estado='REVISAR',total_inventario=2,total_referencia=2,
        productos_comparables=2,productos_sin_historial=0,productos_con_campos_invalidos=0,
        dias_desde_corte=12,fecha_corte_variables='2026-10-06',psi_stock=0.0,
        interpretacion_psi='Bajo',observaciones=['Variables desactualizadas'],aviso='Prueba',ids_duplicados=[])

class FakeAlert:
    def bell_summary(self):return dict(alto_riesgo=1,prioritarios=[{'producto_id':'P001'}])

def setup_fakes(app):
    services=app.extensions['services']
    services.prediction_service=FakePrediction()
    services.data_quality_service=FakeQuality()
    services.alert_service=FakeAlert()

def test_health_and_headers(client):
    result=client.get('/health')
    assert result.status_code==200
    assert result.json['estado']=='activo'
    assert result.headers.get('X-Content-Type-Options')=='nosniff'
    assert result.headers.get('X-Frame-Options')=='DENY'

def test_horizon_rejects_other_than_seven(client,app):
    setup_fakes(app)
    resp=client.get('/api/predicciones-stock?dias=14')
    assert resp.status_code==400
    assert '7 días' in resp.json['error']

def test_prediction_summary_and_product_not_found(client,app):
    setup_fakes(app)
    resp=client.get('/api/predicciones-stock?dias=7')
    assert resp.status_code==200 and resp.json['total_productos']==2
    assert client.get('/api/predicciones-stock/P001').status_code==200
    assert client.get('/api/predicciones-stock/P999').status_code==404

def test_alert_api(client,app):
    setup_fakes(app)
    response=client.get('/api/alertas-riesgo')
    assert response.status_code==200
    assert response.json['alto_riesgo']==1

def test_quality_json_and_html(client,app):
    setup_fakes(app)
    r=client.get('/api/calidad-datos')
    assert r.status_code==200 and r.json['estado']=='REVISAR'
    r2=client.get('/calidad-datos')
    assert r2.status_code==200
    assert b'Control de calidad' in r2.data

def test_register_failure_redirect(client,app):
    setup_fakes(app)
    app.extensions['services'].evaluation_service=SimpleNamespace(register_current=lambda:None)
    r=client.post('/predicciones-stock/registrar-evaluacion')
    assert r.status_code==302 and 'error=1' in r.location

def test_register_success_redirect(client,app):
    setup_fakes(app)
    app.extensions['services'].evaluation_service=SimpleNamespace(register_current=lambda:45)
    r=client.post('/predicciones-stock/registrar-evaluacion')
    assert r.status_code==302 and 'evaluacion=45' in r.location
