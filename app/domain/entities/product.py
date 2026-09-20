from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Product:
    id: Optional[int]
    producto_id: str
    producto: str
    categoria: str
    stock_actual: float
    stock_minimo: float
    stock_seguridad: float
    punto_reorden: float
    lead_time_dias: float

    def to_prediction_dict(self) -> dict:
        return {
            "id": self.id,
            "producto_id": self.producto_id,
            "producto": self.producto,
            "categoria": self.categoria,
            "stock_actual": self.stock_actual,
            "stock_minimo": self.stock_minimo,
            "stock_seguridad": self.stock_seguridad,
            "punto_reorden": self.punto_reorden,
            "lead_time_dias": self.lead_time_dias,
        }
