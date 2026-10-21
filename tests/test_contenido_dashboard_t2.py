"""Pruebas de estructura del contenido del Dashboard para T2.

No alteran modelos, datos ni rutas y no sustituyen pruebas con MySQL.
"""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

RAIZ = Path(__file__).resolve().parents[1]
PLANTILLA = RAIZ / 'app/presentation/templates/dashboard.html'
CSS = RAIZ / 'app/presentation/static/dashboard.css'


def _html():
    return PLANTILLA.read_text(encoding='utf-8')


def test_CD01_alertas_operativas_antes_de_metricas_tecnicas():
    html = _html()
    assert html.index('Revisión operativa del inventario') < html.index('Información técnica del asistente')
    assert html.index('Productos con Stock Crítico') < html.index('Información técnica del asistente')
    assert html.index('Productos Más Buscados') < html.index('Información técnica del asistente')


def test_CD02_metricas_identificadas_como_intenciones_y_desplegables():
    html = _html()
    assert 'Promedio de métricas del asistente' in html
    assert 'Desempeño del clasificador de intenciones' in html
    assert 'distintos de las métricas de Gradient Boosting' in html
    assert '<details class="dashboard-tech-details">' in html
    assert '</details>' in html


def test_CD03_alertas_logisticas_separadas_de_prediccion():
    html = _html()
    assert 'No son las alertas predictivas a 7 días' in html
    assert 'no equivale al número de productos con riesgo predictivo alto' in html
    assert 'stock_critico|length' in html
    assert 'productos_por_vencer|length' in html


def test_CD04_se_conservan_tablas_graficos_datos_y_rutas():
    html = _html()
    for identidad in ('graficoIntenciones', 'graficoAlertas', 'graficoProductos', 'dashboard-data'):
        assert html.count('id="'+identidad+'"') == 1
    assert 'url_for(\'prediction.predicciones_stock\')' in html
    assert 'url_for(\'assistant.index\')' in html
    assert '{% for item in stock_critico %}' in html
    assert '{% for item in productos_por_vencer %}' in html
    assert '{{ total_consultas }}' in html
    assert 'class="dashboard-tech-details"' in CSS.read_text(encoding='utf-8') or '.dashboard-tech-details' in CSS.read_text(encoding='utf-8')


def test_CD05_plantilla_jinja_renderiza_con_datos_controlados():
    env = Environment(loader=FileSystemLoader(str(PLANTILLA.parent)), autoescape=True)
    env.globals['url_for'] = lambda endpoint, **kwargs: '/' + endpoint.replace('.', '/')
    resultado = env.get_template('dashboard.html').render(
        accuracy=81.25, precision=85.36, recall=81.25, f1=80.0,
        total_consultas=461,
        stock_critico=[('Producto A', 0, 5)],
        productos_por_vencer=[],
        productos_mas_buscados=[('Producto A', 29)],
        labels=['stock_critico'], values=[11],
    )
    assert '461' in resultado
    assert 'Producto A' in resultado
    assert 'Sin productos próximos a vencer' in resultado
    assert 'Información técnica del asistente' in resultado
    assert '0' in resultado
