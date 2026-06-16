DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "TU_CONTRASEÑA",
    "database": "inventario_ml"
}

SECRET_KEY = "inventario_ml_secret"

DATASET_PATH = "dataset.csv"
MODELO_PATH = "modelo_intenciones.pkl"
VECTORIZER_PATH = "vectorizer.pkl"
METRICAS_PATH = "metricas.json"

UMBRAL_DESCONOCIDO = 0.20
UMBRAL_MULTIPLE = 0.14
FACTOR_CERCANIA = 0.55
MAX_INTENCIONES = 3