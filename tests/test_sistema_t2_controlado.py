"""T2: verificaciones HTTP de flujos principales con servicios de prueba.

Los casos ejercitan rutas, sesión, plantillas y respuestas HTTP de VetAssistant IA
usando el cliente de prueba de Flask. Las dependencias externas se sustituyen
por dobles controlados: NO demuestran MySQL real, navegador ni aceptación UAT.

Ejecutar: python -m pytest -v tests/test_sistema_t2_controlado.py
"""
from types import SimpleNamespace
import pytest

pytest.importorskip("flask")


def producto():
    return dict(
        producto_id="P001", producto="Antipulgas Bravecto Perro", categoria="Antiparasitario",
        nivel_riesgo="ALTO", porcentaje_riesgo=80.0, stock_actual=5,
        stock_minimo=7, stock_seguridad=8, punto_reorden=10,
        ventas_7d=12, ventas_14d=25, ventas_30d=50,
        demanda_estimada_7d=13, stock_proyectado_7d=-8,
        faltante_estimado=8, margen_seguridad_proyectado=-16,
        dias_cobertura=2.7, lead_time_dias=5,
        promedio_diario_7d=1.71, tendencia_ventas="CRECIENTE",
        factores_observados=["Stock por debajo de seguridad"],
        recomendacion="Revisar reposición del producto",
    )


def resumen():
    p = producto()
    return dict(
        total_productos=1, alto_riesgo=1, medio_riesgo=0, bajo_riesgo=0,
        porcentaje_alto_riesgo=100.0, porcentaje_medio_riesgo=0.0,
        porcentaje_bajo_riesgo=0.0, horizonte_dias=7,
        fecha_corte="2026-09-10", fecha_evaluacion="2026-10-20",
        fuente_catalogo="Inventario de prueba", faltante_proyectado=1,
        modelo="HistGradientBoostingClassifier", metodologia_validacion="División temporal",
        recall_objetivo=80, cumple_recall=True, accuracy=87.41,
        precision=77.01, recall=81.48, f1=79.18,
        umbral=75, umbral_medio=50, umbral_modelo_validado=60.55,
        comparacion_modelos=[], variables_importantes=[],
        top_prioritarios=[p], productos=[p], categorias=["Antiparasitario"],
        cantidad_sin_historial=0,
    )


class AsistentePrueba:
    def __init__(self):
        self.preguntas = []

    def respond(self, pregunta, sesion):
        self.preguntas.append(pregunta)
        if "stock" in pregunta.lower():
            sesion["memoria_producto"] = "Antipulgas Bravecto Perro"
            return "Stock total: 5 unidades"
        return "Consulta no reconocida"


class PrediccionPrueba:
    def __init__(self):
        self.lecturas = 0

    def summary(self):
        self.lecturas += 1
        return resumen()

    def product_detail(self, codigo):
        if codigo != "P001":
            return None
        return dict(producto=producto(), horizonte_dias=7, historial_registrado=[])


class RegistroPrueba:
    def __init__(self, resultado):
        self.resultado = resultado
        self.registros = 0

    def latest(self, limite=6):
        return []

    def register_current(self):
        self.registros += 1
        return self.resultado


class PanelPrueba:
    def data(self):
        return dict(
            accuracy=95, precision=94, recall=93, f1=92,
            total_consultas=2,
            consultas_por_intencion=[("stock", 2)],
            productos_mas_buscados=[],
            stock_critico=[("Antipulgas Bravecto Perro", 5, 7)],
            productos_por_vencer=[], labels=["stock"], values=[2],
        )


class CalidadPrueba:
    def audit(self):
        return dict(
            estado="REVISAR", total_inventario=1, total_referencia=1,
            productos_comparables=1, productos_sin_historial=0,
            productos_con_campos_invalidos=0,
            dias_desde_corte=40, fecha_corte_variables="2026-09-10",
            psi_stock=0.1, interpretacion_psi="Bajo",
            observaciones=["Revisar la fecha de corte"],
            aviso="Escenario de prueba", ids_duplicados=[],
        )


@pytest.fixture
def escenario(app):
    """Mantiene Flask real; sustituye solo infraestructura y casos de uso externos."""
    app.config.update(TESTING=True)
    services = app.extensions["services"]
    services.assistant_service = AsistentePrueba()
    services.prediction_service = PrediccionPrueba()
    services.evaluation_service = RegistroPrueba(17)
    services.dashboard_service = PanelPrueba()
    services.alert_service = SimpleNamespace(bell_summary=lambda: dict(
        alto_riesgo=1, medio_riesgo=0, bajo_riesgo=0,
        prioritarios=[dict(producto_id="P001", producto="Antipulgas Bravecto Perro")]))
    services.data_quality_service = CalidadPrueba()
    return services


def test_ST01_inicio_y_navegacion(client, escenario):
    r = client.get("/")
    assert r.status_code == 200
    assert b"VetAssistant IA" in r.data
    assert b"Predicci" in r.data
    assert b"Dashboard" in r.data


def test_ST02_consulta_textual_y_respuesta(client, escenario):
    r = client.post("/", data={"pregunta": "Cuanto stock hay del producto P001"})
    assert r.status_code == 200
    assert b"Stock total: 5 unidades" in r.data
    assert escenario.assistant_service.preguntas == ["Cuanto stock hay del producto P001"]


def test_ST03_memoria_conversacion_y_limpiar_chat(client, escenario):
    client.post("/", data={"pregunta": "Cuanto stock hay del producto P001"})
    client.post("/", data={"pregunta": "Otra consulta"})
    with client.session_transaction() as ses:
        assert len(ses["chat"]) == 4
    r = client.get("/clear")
    assert r.status_code == 302
    with client.session_transaction() as ses:
        assert ses["chat"] == []


def test_ST04_dashboard_con_indicadores(client, escenario):
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert b"Dashboard" in r.data
    assert b"Antipulgas Bravecto Perro" in r.data


def test_ST05_pantalla_prediccion_y_prioridades(client, escenario):
    r = client.get("/predicciones-stock")
    assert r.status_code == 200
    assert b"Predicci" in r.data
    assert b"Antipulgas Bravecto Perro" in r.data
    assert b"Registrar evaluaci" in r.data


def test_ST06_api_prediccion_siete_dias(client, escenario):
    r = client.get("/api/predicciones-stock?dias=7")
    assert r.status_code == 200
    assert r.json["horizonte_dias"] == 7
    assert r.json["alto_riesgo"] + r.json["medio_riesgo"] + r.json["bajo_riesgo"] == r.json["total_productos"]


def test_ST07_horizonte_invalido(client, escenario):
    r = client.get("/api/predicciones-stock?dias=14")
    assert r.status_code == 400
    assert "7 días" in r.json["error"]


def test_ST08_detalle_producto_y_no_encontrado(client, escenario):
    valido = client.get("/api/predicciones-stock/P001")
    ausente = client.get("/api/predicciones-stock/P999")
    assert valido.status_code == 200
    assert valido.json["producto"]["producto_id"] == "P001"
    assert ausente.status_code == 404


def test_ST09_api_alertas(client, escenario):
    r = client.get("/api/alertas-riesgo")
    assert r.status_code == 200
    assert r.json["alto_riesgo"] == 1
    assert r.json["prioritarios"][0]["producto_id"] == "P001"


def test_ST10_registro_explicito_y_lectura_sin_guardado(client, escenario):
    vista = client.get("/predicciones-stock")
    assert vista.status_code == 200
    assert escenario.evaluation_service.registros == 0
    r = client.post("/predicciones-stock/registrar-evaluacion")
    assert r.status_code == 302
    assert "evaluacion=17" in r.location
    assert escenario.evaluation_service.registros == 1


def test_ST11_registro_fallido_informa_error(client, escenario):
    escenario.evaluation_service = RegistroPrueba(None)
    r = client.post("/predicciones-stock/registrar-evaluacion")
    assert r.status_code == 302
    assert "error=1" in r.location


def test_ST12_calidad_datos_vista_y_api(client, escenario):
    api = client.get("/api/calidad-datos")
    vista = client.get("/calidad-datos")
    assert api.status_code == 200
    assert api.json["estado"] == "REVISAR"
    assert vista.status_code == 200
    assert b"Control de calidad" in vista.data


def test_ST13_health_y_cabeceras_seguridad(client, escenario):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json["estado"] == "activo"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
