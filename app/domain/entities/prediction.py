from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class StockPrediction:
    producto_id: str
    producto: str
    categoria: str
    probabilidad_riesgo: float
    nivel_riesgo: str
    stock_actual: int
    demanda_estimada_7d: int
    stock_proyectado_7d: int
    factores_observados: List[str]
    recomendacion: str
