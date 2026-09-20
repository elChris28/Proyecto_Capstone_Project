# 🐾 VetAssistant IA + Predicción de Quiebre de Stock

Proyecto Flask para una veterinaria que integra dos componentes de Machine Learning:

1. **Asistente de inventario con NLP**: TF-IDF + Multinomial Naive Bayes para reconocer intenciones relacionadas con stock, ubicación, vencimiento y consultas del inventario.
2. **Predicción de riesgo de quiebre de stock a 7 días**: modelo supervisado que combina histórico de ventas, inventario actual y variables operativas.

El proyecto está organizado con **Arquitectura en Capas** y aplica formalmente los patrones **Repository, Strategy y Observer**.

---

## 🧱 Arquitectura

La aplicación en ejecución se encuentra dentro de `app/`:

```text
app/
├── presentation/      # Flask, rutas, templates y CSS
├── application/       # Casos de uso / servicios
├── domain/            # Entidades, Strategy y Observer
├── infrastructure/    # MySQL, repositories y motores ML
├── shared/            # Utilidades transversales
├── container.py       # Composition Root / Dependency Injection
└── __init__.py        # Flask Application Factory
```

Los recursos que no forman parte del flujo HTTP se mantienen separados:

```text
data/                  # datasets y features
models/                # modelos y métricas serializadas
scripts/               # entrenamiento y análisis offline
docs/                  # documentación
```

`main.py` se mantiene en la raíz porque es el punto de entrada y `config.py` porque concentra configuración transversal.

Consulta `docs/ARCHITECTURA.md` para la explicación completa.

---

## 📁 Estructura principal

```text
Proyecto_Capstone_Project/
│
├── app/
│   ├── presentation/
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   └── shared/
│
├── data/
│   ├── dataset_intenciones.csv
│   ├── dataset_veterinario.csv
│   ├── inventario_actual.csv
│   └── features_actuales_7d.csv
│
├── models/
│   ├── intent/
│   │   ├── modelo_intenciones.pkl
│   │   ├── vectorizer.pkl
│   │   └── metricas.json
│   └── stock/
│       ├── modelo_quiebre_stock.pkl
│       ├── metricas_quiebre_stock.json
│       └── importancia_variables.json
│
├── scripts/
│   ├── training/
│   │   ├── train_intent_model.py
│   │   └── train_stock_model.py
│   └── analysis/
│       └── calculate_feature_importance.py
│
├── docs/
├── config.py
├── main.py
├── requirements.txt
└── .env.example
```

---

## 🔮 Predicción de quiebre de stock

El modelo utiliza, entre otras, las siguientes variables:

- stock actual;
- stock de seguridad;
- punto de reorden;
- lead time;
- ventas de 3, 7, 14 y 30 días;
- promedio y variabilidad de ventas;
- lags de demanda;
- días de cobertura;
- relación stock/demanda;
- tendencia reciente;
- promociones;
- categoría;
- variables de calendario.

La etiqueta preventiva considera riesgo cuando la demanda real de los siguientes siete días consumiría el stock disponible hasta alcanzar la zona de stock de seguridad.

El histórico original no contiene snapshots diarios reales de inventario, por lo que el proceso académico simula la evolución histórica del stock utilizando demanda, punto de reorden, stock de seguridad y lead time.

---

## 🧠 Modelos comparados

`scripts/training/train_stock_model.py` compara:

- Regresión Logística;
- Random Forest;
- Gradient Boosting (`HistGradientBoostingClassifier`).

La validación utiliza un **split temporal 70 % / 15 % / 15 %** para entrenamiento, validación y test.

Resultado incluido:

| Modelo | Accuracy | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| Regresión Logística | 87.22 % | 77.12 % | 80.37 % | 78.71 % |
| Random Forest | 86.82 % | 76.13 % | 80.37 % | 78.19 % |
| **Gradient Boosting** | **87.41 %** | **77.01 %** | **81.48 %** | **79.18 %** |

El modelo seleccionado se almacena en:

```text
models/stock/modelo_quiebre_stock.pkl
```

Las métricas se almacenan en:

```text
models/stock/metricas_quiebre_stock.json
```

---

## 🚦 Semáforo operativo

El modelo sigue siendo un clasificador binario y conserva su umbral validado para el cálculo de métricas. La interfaz añade una capa de priorización:

- 🔴 **ALTO:** probabilidad ≥ 75 %.
- 🟡 **MEDIO:** probabilidad ≥ 50 % y < 75 %.
- 🟢 **BAJO:** probabilidad < 50 %.

El nivel MEDIO es una categoría operativa de vigilancia, no una tercera clase aprendida por el modelo.

---

## 📊 Módulo de predicción

Ruta principal:

```text
http://127.0.0.1:5000/predicciones-stock
```

Incluye:

- resumen ALTO / MEDIO / BAJO;
- top de productos prioritarios;
- probabilidad de riesgo;
- stock actual y demanda estimada;
- stock proyectado;
- factores observados y recomendación;
- comparación de modelos;
- importancia global de variables;
- registro e historial de evaluaciones;
- filtros por producto, categoría y nivel.

---

## 🔔 Campana de alertas

El inicio del asistente incorpora una campana que consulta las alertas predictivas actuales y muestra los productos de mayor prioridad.

Abrir la campana no registra una nueva evaluación. El historial se guarda solamente cuando el usuario utiliza la acción de registrar evaluación en el módulo predictivo.

---

## 🔌 API REST

Endpoints principales:

```text
GET /api/alertas-riesgo
GET /api/predicciones-stock?dias=7
GET /api/predicciones-stock/<producto_id>
```

El horizonte predictivo soportado actualmente es de **7 días**.

---

## 🗄️ MySQL

En operación:

- MySQL aporta el catálogo e inventario actual.
- El vínculo con el histórico se realiza mediante `producto_id`.
- El motor recalcula las variables dependientes del stock con el inventario actual antes de inferir.
- Un producto de MySQL sin histórico suficiente se reporta como tal y no recibe una predicción inventada.

---

## 🧩 Patrones de diseño

### Repository

Los repositorios encapsulan las consultas a MySQL:

- `ProductRepository`
- `ConsultationRepository`
- `PredictionHistoryRepository`

### Strategy

Las estrategias encapsulan la ejecución de los algoritmos supervisados:

- `LogisticRegressionStrategy`
- `RandomForestStrategy`
- `GradientBoostingStrategy`

### Observer

`EvaluationService` genera un evento al registrar una evaluación y `BellAlertObserver` lo recibe mediante `AlertSubject`.

---

## ⚙️ Instalación

En Windows:

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download es_core_news_sm
```

Crea `.env` a partir de `.env.example` y configura la conexión MySQL.

Luego:

```bash
python main.py
```

---

## ♻️ Reentrenar el modelo de stock

Solo cuando cambien los datos históricos o la lógica de preparación:

```bash
python -m scripts.training.train_stock_model
```

El proceso actualiza:

```text
data/features_actuales_7d.csv
models/stock/modelo_quiebre_stock.pkl
models/stock/metricas_quiebre_stock.json
```

Después puede recalcularse la importancia de variables:

```bash
python -m scripts.analysis.calculate_feature_importance
```

Salida:

```text
models/stock/importancia_variables.json
```

---

## 💬 Reentrenar el clasificador de intenciones

Solo si cambia `data/dataset_intenciones.csv`:

```bash
python -m scripts.training.train_intent_model
```

Actualiza:

```text
models/intent/modelo_intenciones.pkl
models/intent/vectorizer.pkl
models/intent/metricas.json
```

---

## 🔎 Interpretabilidad

La importancia global se calcula mediante **Permutation Importance agrupada** sobre una muestra del conjunto TEST temporal y utiliza el umbral real del modelo desplegado.

La medida representa la caída promedio del F1 al permutar cada variable. No debe interpretarse como causalidad para un producto individual.

---

## ⚠️ Nota académica

El dataset es sintético. Para una implementación productiva, la simulación histórica de inventario debería sustituirse por snapshots reales de inventario, ventas y movimientos de reposición obtenidos del sistema transaccional de la organización.
