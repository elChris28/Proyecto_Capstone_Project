from __future__ import annotations

from typing import Optional

from app.domain.observers.alert_observer import AlertObserver, RiskEvaluationEvent


class BellAlertObserver(AlertObserver):
    """Observer concreto asociado a la campana de alertas de la interfaz."""

    def __init__(self):
        self.last_event: Optional[RiskEvaluationEvent] = None

    def update(self, event: RiskEvaluationEvent) -> None:
        self.last_event = event

    def last_registered_summary(self) -> Optional[dict]:
        if self.last_event is None:
            return None
        event = self.last_event
        return {
            "evaluacion_id": event.evaluacion_id,
            "fecha_evaluacion": event.fecha_evaluacion.strftime("%Y-%m-%d %H:%M:%S"),
            "total_productos": event.total_productos,
            "alto_riesgo": event.alto_riesgo,
            "medio_riesgo": event.medio_riesgo,
            "bajo_riesgo": event.bajo_riesgo,
        }
