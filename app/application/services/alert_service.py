from __future__ import annotations


class AlertService:
    """Caso de uso de alertas para la campana del asistente."""

    def __init__(self, prediction_service, bell_observer):
        self.predictions = prediction_service
        self.bell_observer = bell_observer

    def bell_summary(self) -> dict:
        resumen = self.predictions.summary()
        prioritarios = [
            {
                "producto_id": item.get("producto_id"),
                "producto": item.get("producto"),
                "categoria": item.get("categoria"),
                "stock_actual": item.get("stock_actual"),
                "demanda_estimada_7d": item.get("demanda_estimada_7d"),
                "porcentaje_riesgo": item.get("porcentaje_riesgo"),
                "nivel_riesgo": item.get("nivel_riesgo"),
                "recomendacion": item.get("recomendacion"),
            }
            for item in resumen.get("top_prioritarios", [])[:5]
        ]
        return {
            "fecha_evaluacion": resumen.get("fecha_evaluacion"),
            "horizonte_dias": resumen.get("horizonte_dias", 7),
            "total_productos": resumen.get("total_productos", 0),
            "alto_riesgo": resumen.get("alto_riesgo", 0),
            "medio_riesgo": resumen.get("medio_riesgo", 0),
            "bajo_riesgo": resumen.get("bajo_riesgo", 0),
            "umbral_alto": resumen.get("umbral", 75),
            "umbral_medio": resumen.get("umbral_medio", 50),
            "prioritarios": prioritarios,
            "ultima_evaluacion_registrada": self.bell_observer.last_registered_summary(),
        }
