from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RiskEvaluation:
    id: int
    fecha_evaluacion: datetime
    total_productos: int
    alto_riesgo: int
    medio_riesgo: int
    bajo_riesgo: int
