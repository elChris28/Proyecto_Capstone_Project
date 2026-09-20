# V7 — Arquitectura limpia definitiva

Esta versión elimina la estructura híbrida de transición de la V6 y deja el proyecto organizado de forma coherente con la Arquitectura en Capas.

## Cambios principales

- Se retiraron las fachadas antiguas de raíz: `asistente.py`, `database.py`, `predictor.py` y `riesgo_stock.py`.
- `dataset.csv` pasó a `data/dataset_intenciones.csv`.
- Los modelos y métricas se separaron en `models/intent/` y `models/stock/`.
- Los procesos offline se movieron a `scripts/training/` y `scripts/analysis/`.
- `utils.py` pasó a `app/shared/utils.py`.
- La documentación y el GIF de demostración se movieron a `docs/`.
- `PredictionService`, `AssistantService` y `DashboardService` ya no importan directamente motores de infraestructura; reciben sus dependencias mediante `ServiceContainer`.
- Se agregaron adaptadores `IntentPredictionEngine` y `StockPredictionEngine`.
- `app/__init__.py` usa imports diferidos dentro de `create_app()`, evitando inicializar Flask durante tareas offline.
- Se actualizaron todas las rutas a datasets, modelos, métricas e importancia de variables.
- Se retiraron del paquete final `.git`, `venv`, cachés de Python y credenciales `.env`.

## Comandos actuales

```bash
python main.py
python -m scripts.training.train_stock_model
python -m scripts.analysis.calculate_feature_importance
python -m scripts.training.train_intent_model
```

La explicación formal se encuentra en `docs/ARCHITECTURA.md`.
