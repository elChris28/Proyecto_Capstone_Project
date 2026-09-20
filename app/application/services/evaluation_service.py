from __future__ import annotations

from datetime import datetime

from app.domain.observers.alert_observer import RiskEvaluationEvent


class EvaluationService:
    """Caso de uso para registrar snapshots y notificar observers."""

    def __init__(self, prediction_service, history_repository, alert_subject):
        self.predictions = prediction_service
        self.history = history_repository
        self.alert_subject = alert_subject

    def register_current(self):
        resumen = self.predictions.summary()
        evaluacion_id = self.history.save_evaluation(resumen)
        if evaluacion_id is None:
            return None

        self.alert_subject.notify(
            RiskEvaluationEvent(
                evaluacion_id=evaluacion_id,
                fecha_evaluacion=datetime.now(),
                total_productos=int(resumen.get("total_productos", 0)),
                alto_riesgo=int(resumen.get("alto_riesgo", 0)),
                medio_riesgo=int(resumen.get("medio_riesgo", 0)),
                bajo_riesgo=int(resumen.get("bajo_riesgo", 0)),
            )
        )
        return evaluacion_id

    def latest(self, limite=6):
        return self.history.latest_evaluations(limite)
