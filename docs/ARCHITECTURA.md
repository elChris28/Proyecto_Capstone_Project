# Arquitectura de Software — VetAssistant IA

## 1. Patrón de arquitectura seleccionado

El proyecto aplica **Arquitectura en Capas (Layered Architecture)**. La aplicación web se divide en cuatro capas principales y un módulo transversal de utilidades compartidas.

```text
┌──────────────────────────────────────────────┐
│ PRESENTACIÓN                                 │
│ Flask Blueprints · HTML · CSS · API REST     │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│ APLICACIÓN                                   │
│ Casos de uso / servicios                     │
│ Assistant · Prediction · Alert · Evaluation  │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│ DOMINIO                                      │
│ Entidades · contratos · Strategy · Observer  │
└──────────────────────▲───────────────────────┘
                       │ implementado por
┌──────────────────────┴───────────────────────┐
│ INFRAESTRUCTURA                              │
│ MySQL · Repository · modelos ML · artefactos │
└──────────────────────────────────────────────┘
```

La creación de objetos concretos se concentra en `app/container.py`, que actúa como **Composition Root**. De esta forma, los servicios de aplicación reciben sus dependencias por constructor y no crean conexiones MySQL ni motores de Machine Learning por su cuenta.

## 2. Responsabilidad de cada capa

### Presentación — `app/presentation/`

Responsable de la interacción HTTP y de la interfaz visual.

- `routes/assistant_routes.py`: pantalla principal y conversación.
- `routes/dashboard_routes.py`: dashboard del asistente.
- `routes/prediction_routes.py`: predicciones, registro de evaluación y endpoints REST.
- `templates/`: HTML.
- `static/`: CSS y recursos de interfaz.

La presentación invoca servicios de aplicación mediante el contenedor registrado en Flask.

### Aplicación — `app/application/`

Contiene los casos de uso y coordina el flujo del sistema.

- `AssistantService`: conversación y consultas de inventario.
- `PredictionService`: coordina inventario actual y motor de predicción.
- `EvaluationService`: registra snapshots de evaluación.
- `AlertService`: construye el resumen para la campana.
- `DashboardService`: prepara métricas y datos del dashboard.
- `BellAlertObserver`: observador concreto para las alertas de la campana.

Esta capa no contiene SQL ni carga directamente archivos `.pkl`.

### Dominio — `app/domain/`

Contiene conceptos y contratos independientes de Flask y MySQL.

- Entidades: `Product`, `StockPrediction`, `RiskEvaluation`.
- Strategy: contrato y estrategias para ejecutar clasificadores.
- Observer: `AlertObserver`, `AlertSubject` y `RiskEvaluationEvent`.

### Infraestructura — `app/infrastructure/`

Implementa detalles tecnológicos.

- `database/mysql_connection.py`: creación de conexiones MySQL bajo demanda.
- `database/repositories/`: consultas y persistencia.
- `ml/intent_predictor.py`: inferencia del clasificador de intenciones.
- `ml/stock_predictor.py`: inferencia del riesgo de quiebre a 7 días.

## 3. Patrones de diseño implementados

### Repository

Encapsula el acceso a MySQL.

- `ProductRepository`
- `ConsultationRepository`
- `PredictionHistoryRepository`

Los servicios de aplicación no ejecutan sentencias SQL directamente.

### Strategy

`PredictionStrategy` permite ejecutar diferentes estimadores con una interfaz común:

- `LogisticRegressionStrategy`
- `RandomForestStrategy`
- `GradientBoostingStrategy`

El modelo desplegado actualmente usa la estrategia de **Gradient Boosting**.

### Observer

Cuando se registra una evaluación, `EvaluationService` emite un `RiskEvaluationEvent` mediante `AlertSubject`. `BellAlertObserver` recibe el evento y conserva el resumen necesario para la campana.

Este patrón permite añadir otros canales de notificación posteriormente sin modificar la lógica del modelo.

## 4. Principios SOLID aplicados

- **SRP**: rutas, servicios, repositorios, inferencia ML y persistencia tienen responsabilidades separadas.
- **DIP**: los servicios reciben repositorios y motores por inyección de dependencias en `ServiceContainer`.
- **OCP**: es posible añadir nuevas estrategias predictivas u observadores sin reescribir los casos de uso existentes.

## 5. Estructura definitiva del proyecto

```text
Proyecto_Capstone_Project/
│
├── app/                              # Aplicación en ejecución
│   ├── presentation/                 # Capa de presentación
│   │   ├── routes/
│   │   ├── templates/
│   │   └── static/
│   ├── application/                  # Capa de aplicación
│   │   ├── services/
│   │   └── observers/
│   ├── domain/                       # Capa de dominio
│   │   ├── entities/
│   │   ├── strategies/
│   │   └── observers/
│   ├── infrastructure/               # Capa de infraestructura
│   │   ├── database/
│   │   │   └── repositories/
│   │   └── ml/
│   ├── shared/                       # Utilidades transversales
│   ├── container.py                  # Composition Root / DI
│   └── __init__.py                   # Application Factory Flask
│
├── data/                             # Fuentes y datos procesados
│   ├── dataset_intenciones.csv
│   ├── dataset_veterinario.csv
│   ├── inventario_actual.csv
│   └── features_actuales_7d.csv
│
├── models/                           # Artefactos entrenados
│   ├── intent/
│   │   ├── modelo_intenciones.pkl
│   │   ├── vectorizer.pkl
│   │   └── metricas.json
│   └── stock/
│       ├── modelo_quiebre_stock.pkl
│       ├── metricas_quiebre_stock.json
│       └── importancia_variables.json
│
├── scripts/                          # Procesos offline del ciclo ML
│   ├── training/
│   │   ├── train_intent_model.py
│   │   └── train_stock_model.py
│   └── analysis/
│       └── calculate_feature_importance.py
│
├── docs/                             # Documentación y recursos
│   ├── ARCHITECTURA.md
│   ├── INSTRUCCIONES.txt
│   └── assets/
│
├── config.py                         # Configuración transversal
├── main.py                           # Punto de entrada
├── requirements.txt
├── .env.example
└── README.md
```

## 6. Por qué `main.py`, `config.py`, `data/`, `models/` y `scripts/` no están dentro de una capa

La Arquitectura en Capas organiza principalmente los componentes que participan en la **ejecución de la aplicación**. No obliga a colocar todos los archivos del repositorio dentro de `app/`.

- `main.py` es únicamente el punto de entrada que crea y arranca Flask.
- `config.py` concentra configuración transversal y rutas de artefactos.
- `data/` contiene fuentes y resultados de preparación de datos.
- `models/` contiene artefactos serializados generados durante entrenamiento.
- `scripts/` contiene procesos **offline** de entrenamiento y análisis; no forman parte del flujo HTTP normal.
- `docs/` contiene documentación del proyecto.

Esta separación evita mezclar el ciclo de entrenamiento de Machine Learning con el código que atiende consultas en producción.

## 7. Flujo principal de ejecución

```text
Usuario
  ↓
Blueprint / Presentación
  ↓
Servicio de Aplicación
  ↓
Repository ───────────────→ MySQL
  ↓
Prediction Engine ────────→ modelo .pkl + features
  ↓
Resultado / alerta / API
```

## 8. Flujo offline de Machine Learning

```text
Dataset histórico
  ↓
scripts/training/train_stock_model.py
  ↓
features + comparación de modelos
  ↓
models/stock/modelo_quiebre_stock.pkl
  ↓
scripts/analysis/calculate_feature_importance.py
  ↓
models/stock/importancia_variables.json
```

El entrenamiento no se ejecuta cuando un usuario abre el asistente o consulta una predicción.
