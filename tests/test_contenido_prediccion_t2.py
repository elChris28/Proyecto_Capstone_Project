"""T2: contenido y orden de lectura de la página de predicción.

Estas pruebas verifican únicamente la plantilla y sus controles visibles;
no validan MySQL, el modelo predictivo ni las mediciones PRE/POS.
"""
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = ROOT / "app" / "presentation" / "templates"
TEMPLATE_PATH = TEMPLATE_DIR / "predicciones_stock.html"
CSS_PATH = ROOT / "app" / "presentation" / "static" / "predicciones_stock.css"


def _renderizar_prueba(completo=False):
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR),
                      autoescape=select_autoescape(["html"]))
    env.globals["url_for"] = lambda endpoint, **kwargs: "/" + endpoint.replace(".", "/")
    producto = dict(
        producto_id="P060", producto="Pipeta Antipulgas Canino VetNova Mini",
        categoria="Antiparasitario", porcentaje_riesgo=100, stock_actual=0,
        nivel_riesgo="ALTO", stock_minimo=11, stock_seguridad=11,
        punto_reorden=16, ventas_7d=29, ventas_14d=38,
        ventas_30d=80, demanda_estimada_7d=27, stock_proyectado_7d=-27,
        faltante_estimado=28, margen_seguridad_proyectado=-38,
        dias_cobertura=0.0, lead_time_dias=2, promedio_diario_7d=4.14,
        tendencia_ventas=1.48, factores_observados=["Stock actual insuficiente"],
        recomendacion="Priorizar revisión de reposición",
    )
    resumen = dict(
        total_productos=500, alto_riesgo=95, medio_riesgo=44, bajo_riesgo=361,
        porcentaje_alto_riesgo=19.0, porcentaje_medio_riesgo=8.8,
        porcentaje_bajo_riesgo=72.2, horizonte_dias=7,
        fecha_corte="2026-09-10", fecha_evaluacion="2026-10-20",
        fuente_catalogo="MySQL", faltante_proyectado=39,
        modelo="Gradient Boosting", metodologia_validacion="Partición temporal",
        recall_objetivo=80, cumple_recall=True, accuracy=87.41,
        precision=77.01, recall=81.48, f1=79.18,
        umbral=75, umbral_medio=50, umbral_modelo_validado=60.55,
        comparacion_modelos=[], variables_importantes=[],
        top_prioritarios=[producto], categorias=["Antiparasitario"],
        cantidad_sin_historial=0,
    )
    if completo:
        resumen["comparacion_modelos"] = [dict(
            nombre="Gradient Boosting", seleccionado=True, cumple_recall=True,
            accuracy=87.41, precision=77.01, recall=81.48, f1=79.18,
            umbral=60.55,
        )]
        resumen["variables_importantes"] = [dict(
            etiqueta="Relación stock / stock de seguridad",
            importancia_relativa_pct=53.6, barra_pct=53.6,
            importancia_f1=0.2172,
        )]
        resumen.update(filas_importancia=6000, repeticiones_importancia=5,
                       f1_base_importancia=78.84)
    return env.get_template(TEMPLATE_PATH.name).render(
        resumen=resumen, productos=[producto], historial_evaluaciones=[],
        csrf_token="valor-de-prueba", evaluacion_guardada=None,
        error_guardado=None,
    )


def test_CT01_primero_acciones_y_despues_informacion_tecnica():
    s = TEMPLATE_PATH.read_text(encoding="utf-8")
    selectores = (
        'class="executive-summary"', 'class="kpi-grid"',
        'class="priority-section"', 'class="table-card"',
        'class="history-section"', 'id="informacion-tecnica"',
    )
    assert [s.index(x) for x in selectores] == sorted(s.index(x) for x in selectores)


def test_CT02_modelos_y_metricas_conservados_en_desplegable():
    html = _renderizar_prueba(completo=True)
    i = html.index('<details class="technical-details"')
    j = html.index('</details>', i)
    panel = html[i:j]
    assert "<summary>Información técnica del modelo" in panel
    assert '<section class="model-card">' in panel
    for etiqueta in ("Accuracy", "Precision", "Recall", "F1-Score",
                     "Umbral binario ML", "Comparación de modelos evaluados",
                     "Variables con mayor relevancia", "PRE/POS"):
        assert etiqueta in panel


def test_CT03_se_mantienen_filtros_detalle_y_registro():
    html = _renderizar_prueba(completo=True)
    for campo in ('id="searchProduct"', 'id="categoryFilter"',
                  'id="riskFilter"', 'id="predictionTable"',
                  'data-target="detail-1"', 'class="register-form"'):
        assert campo in html
    assert "Calidad de datos" in html
    assert "Pipeta Antipulgas Canino VetNova Mini" in html
    assert "Registrar evaluación" in html


def test_CT04_advertencias_sin_modificar_valores_del_modelo():
    html = _renderizar_prueba(completo=True)
    assert "No son mediciones PRE/POS" in html
    assert "no representa" in html.lower() or "no representan" in html.lower()
    assert "stock proyectado negativo" in html
    assert "no genera compras automáticamente" in html
    assert "2026-09-10" in html
    assert "Calidad de datos" in html
    assert ".technical-details > summary" in CSS_PATH.read_text(encoding="utf-8")
