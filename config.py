import os
from pathlib import Path

from dotenv import load_dotenv

# Raíz del proyecto. Se usa como referencia única para datos, modelos y .env.
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
INTENT_MODEL_DIR = MODELS_DIR / "intent"
STOCK_MODEL_DIR = MODELS_DIR / "stock"

load_dotenv(BASE_DIR / ".env")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "inventario_ml"),
    "port": int(os.getenv("DB_PORT", 3306)),
}

SECRET_KEY = os.getenv("SECRET_KEY", "inventario_ml_secret")

# Asistente de intenciones (NLP)
DATASET_PATH = DATA_DIR / "dataset_intenciones.csv"
MODELO_PATH = INTENT_MODEL_DIR / "modelo_intenciones.pkl"
VECTORIZER_PATH = INTENT_MODEL_DIR / "vectorizer.pkl"
METRICAS_PATH = INTENT_MODEL_DIR / "metricas.json"

# Modelo de riesgo de quiebre de stock
MODELO_QUIEBRE_PATH = STOCK_MODEL_DIR / "modelo_quiebre_stock.pkl"
METRICAS_QUIEBRE_PATH = STOCK_MODEL_DIR / "metricas_quiebre_stock.json"
IMPORTANCIA_VARIABLES_PATH = STOCK_MODEL_DIR / "importancia_variables.json"
FEATURES_ACTUALES_PATH = DATA_DIR / "features_actuales_7d.csv"

# Umbrales del asistente NLP
UMBRAL_DESCONOCIDO = 0.30
UMBRAL_MULTIPLE = 0.14
FACTOR_CERCANIA = 0.55
MAX_INTENCIONES = 3
