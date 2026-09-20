from __future__ import annotations


class DashboardService:
    def __init__(self, consultation_repository, product_repository, intent_engine):
        self.consultations = consultation_repository
        self.products = product_repository
        self.intent_engine = intent_engine

    def data(self) -> dict:
        metricas = self.intent_engine.metrics()
        consultas_por_intencion = self.consultations.by_intention()
        labels = [item[0] for item in consultas_por_intencion] if consultas_por_intencion else []
        values = [item[1] for item in consultas_por_intencion] if consultas_por_intencion else []
        return {
            "accuracy": round(metricas.get("accuracy", 0) * 100, 2),
            "precision": round(metricas.get("precision", 0) * 100, 2),
            "recall": round(metricas.get("recall", 0) * 100, 2),
            "f1": round(metricas.get("f1", 0) * 100, 2),
            "total_consultas": self.consultations.total(),
            "consultas_por_intencion": consultas_por_intencion,
            "productos_mas_buscados": self.consultations.most_searched_products(),
            "stock_critico": self.products.get_critical_stock(),
            "productos_por_vencer": self.products.get_expiring_products(),
            "labels": labels,
            "values": values,
        }
