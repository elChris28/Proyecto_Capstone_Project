"""Comprobaciones T2: presentación de calidad de datos, sin datos inventados."""
from pathlib import Path
from types import SimpleNamespace

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / 'app/presentation/templates/calidad_datos.html'
CSS_PATH = ROOT / 'app/presentation/static/calidad_datos.css'


def _auditoria(estado='REVISAR', observaciones=None):
    if observaciones is None:
        observaciones = ['El histórico requiere actualización.', 'La distribución ha cambiado.']
    return SimpleNamespace(
        estado=estado,
        total_inventario=500,
        productos_comparables=500,
        productos_sin_historial=0,
        productos_con_campos_invalidos=0,
        dias_desde_corte=40,
        psi_stock=0.5991,
        interpretacion_psi='Alto (>=0.25)',
        observaciones=observaciones,
        fecha_corte_variables='2026-09-10',
        aviso='PSI y frescura son indicadores de monitoreo.',
    )


def _render(estado='REVISAR', observaciones=None):
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_PATH.parent)), autoescape=True)
    env.globals['url_for'] = lambda endpoint, **kwargs: (
        '/static/' + kwargs['filename'] if endpoint == 'static' else '/test/' + endpoint
    )
    return env.get_template('calidad_datos.html').render(
        auditoria=_auditoria(estado, observaciones)
    )


def test_EC01_mantiene_todos_los_indicadores_sin_cambiar_valores():
    html = _render()
    for label in ('Productos en inventario', 'Productos comparables', 'Sin historial',
                  'Datos inválidos', 'Antigüedad del dataset', 'PSI del stock'):
        assert label in html
    for value in ('500', '40', '0.5991', '2026-09-10'):
        assert value in html
    assert 'REVISAR' in html


def test_EC02_mantiene_rutas_existentes_y_css_separado():
    source = TEMPLATE_PATH.read_text(encoding='utf-8')
    assert "url_for('prediction.predicciones_stock')" in source
    assert "url_for('prediction.api_calidad_datos')" in source
    assert "url_for('static', filename='calidad_datos.css')" in source
    assert CSS_PATH.is_file()
    assert '<style>' not in source


def test_EC03_observaciones_y_estado_revisar_visibles():
    html = _render()
    assert 'quality-status-card is-review' in html
    assert 'El histórico requiere actualización.' in html
    assert 'La distribución ha cambiado.' in html
    assert 'No se detectaron alertas bajo estas reglas.' not in html


def test_EC04_estado_ok_sin_alertas_correctamente_presentado():
    html = _render(estado='OK', observaciones=[])
    assert 'quality-status-card is-ok' in html
    assert 'No se detectaron alertas bajo estas reglas.' in html
    assert 'quality-metric-caution' not in html


def test_EC05_diseno_responsive_y_preserva_autoria_de_datos():
    css = CSS_PATH.read_text(encoding='utf-8')
    source = TEMPLATE_PATH.read_text(encoding='utf-8')
    assert '@media (max-width: 900px)' in css
    assert '@media (max-width: 560px)' in css
    assert 'auditoria.fecha_corte_variables' in source
    assert 'auditoria.aviso' in source
    assert 'auditoria.interpretacion_psi' in source
    assert 'No modifica las predicciones ni sus métricas.' in source
