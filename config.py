import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "inventario_ml"),
    "port": int(os.getenv("DB_PORT", 3306))
}

SECRET_KEY = os.getenv("SECRET_KEY", "inventario_ml_secret")

DATASET_PATH = "dataset.csv"
MODELO_PATH = "modelo_intenciones.pkl"
VECTORIZER_PATH = "vectorizer.pkl"
METRICAS_PATH = "metricas.json"

UMBRAL_DESCONOCIDO = 0.30
UMBRAL_MULTIPLE = 0.14
FACTOR_CERCANIA = 0.55
MAX_INTENCIONES = 3