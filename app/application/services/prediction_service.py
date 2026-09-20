from __future__ import annotations


class PredictionService:
    """Caso de uso de predicción: coordina inventario + motor ML.

    El servicio depende de abstracciones recibidas por composición; no importa
    directamente módulos de infraestructura.
    """

    def __init__(self, product_repository, history_repository, prediction_engine):
        self.products = product_repository
        self.history = history_repository
        self.engine = prediction_engine

    def summary(self) -> dict:
        inventario = self.products.get_prediction_inventory()
        return self.engine.summary(inventory=inventario)

    def predict_all(self) -> list[dict]:
        inventario = self.products.get_prediction_inventory()
        return self.engine.predict_all(inventory=inventario)

    def find_from_text(self, texto: str):
        inventario = self.products.get_prediction_inventory()
        return self.engine.find_from_text(texto, inventory=inventario)

    def product_detail(self, producto_id: str):
        producto_id = (producto_id or "").strip().upper()
        resumen = self.summary()
        producto = next(
            (item for item in resumen["productos"] if item["producto_id"].upper() == producto_id),
            None,
        )
        if producto is None:
            return None
        return {
            "fecha_evaluacion": resumen.get("fecha_evaluacion"),
            "fecha_corte": resumen.get("fecha_corte"),
            "horizonte_dias": resumen.get("horizonte_dias"),
            "umbral_alto": resumen.get("umbral"),
            "umbral_medio": resumen.get("umbral_medio"),
            "umbral_modelo_validado": resumen.get("umbral_modelo_validado"),
            "producto": producto,
            "historial_registrado": self.history.product_history(producto_id, limite=10),
        }
