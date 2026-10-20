# Evidencia de avance funcional - Versión posterior a PC08

## Alcance de lo implementado

La versión original documentada acreditaba **63/87 SP = 72.4 %** (PB05-PB12). Se
conservan los 87 SP del Product Backlog (misma denominador, sin crear tareas nuevas).

En esta entrega se agregan dos bloques de trabajo, con evidencia técnica concreta:

| PB / subactividad | SP ya acreditados | SP añadidos | Evidencia |
| --- | ---: | ---: | --- |
| PB05-PB12, línea base predictiva | 63 | 0 | Modelo, alertas, API REST y dashboard existentes |
| PB04, modelo de datos implementado (esquema y agrupación de productos por ID) | 0 | 5 | scripts/database/schema.sql, init_schema.py, product_repository.py, tests/test_database_schema.py, test_product_aggregation.py |
| PB13, QA automatizada | 0 | 3 | 26 pruebas ejecutables en tests/, resultados en evidencias/ |
| PB13, monitoreo de calidad / drift descriptivo | 0 | 2 | DataQualityService, /calidad-datos, /api/calidad-datos, verify_offline.py |
| PB13, configuración de seguridad base | 0 | 1 | Login de producción, protección de APIs, CSRF, cabeceras, modo HTTPS configurable, tests/test_security.py |
| PB13, UAT con usuarios y puesta en producción validada | 0 | 0 / 2 pendientes | docs/PLAN_UAT_Y_DESPLIEGUE.md |
| PB01-PB03 y otras tareas excluidas del crédito funcional | 0 | 0 | No se acredita documentación de análisis/diseño |

**Avance funcional técnico acreditable = (63+5+3+2+1) / 87 = 74 / 87 = 85.06 %**, redondeado a **85.1 %**. El desglose interno de PB13 es de esta actualización y debe ser aceptado por el docente; no debe confundirse con resultados de UAT o un despliegue aprobado. PB04 había sido excluido del cálculo inicial por corresponder a diseño; aquí se acredita por nueva implementación material (DDL, CLI, agrupación multi-lote), no por presentar únicamente el diagrama.

## Resultado de pruebas

Consultar `evidencias/pruebas_automatizadas.txt`, generado mediante pytest sobre 26 pruebas. La ejecución es offline/con datos simulados en tests para MySQL; no comprueba acceso real a la base del negocio. La inferencia usa el modelo serializado y el archivo CSV real adjunto al proyecto, sin reentrenamiento.

## Restricciones e inconsistencias conocidas

- El CSV de ventas contiene **1,039,500** registros y los metadatos del modelo indican **1,021,500** registros de modelamiento; diferencia de 18,000, ya observada en el Anexo G de PC08.
- Los resultados obtenidos desde `inventario_actual.csv` pueden diferir de los 95 altos, 44 medios y 361 bajos mostrados en PC08; esas capturas corresponden a otro escenario de MySQL y no deben sustituirse sin una ejecución equivalente.
- No hay servicio MySQL activo ni servidor HTTPS en este entorno de evaluación; los controles y contratos están implementados y probados de manera local/simulada, pero no existe acta de UAT de usuarios ni mediciones reales PRE/POS.
- El monitor PSI compara el stock operativo con el escenario de referencia de features; es un indicador de desplazamiento de datos, no un test de deriva del desempeño del clasificador.

## Reproducción

```
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
python -m scripts.qa.verify_offline --output evidencias/verificacion_offline.json
python -m scripts.database.init_schema --check
python main.py
```

Se requiere una MySQL configurada para rutas normales de inventario. El módulo offline y los tests no requieren MySQL.
