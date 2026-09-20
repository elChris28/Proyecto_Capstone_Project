from __future__ import annotations

from app.application.observers.bell_alert_observer import BellAlertObserver
from app.application.services.alert_service import AlertService
from app.application.services.assistant_service import AssistantService
from app.application.services.dashboard_service import DashboardService
from app.application.services.evaluation_service import EvaluationService
from app.application.services.prediction_service import PredictionService
from app.domain.observers.alert_observer import AlertSubject
from app.infrastructure.database.mysql_connection import MySQLConnectionFactory
from app.infrastructure.database.repositories.consultation_repository import ConsultationRepository
from app.infrastructure.database.repositories.prediction_history_repository import PredictionHistoryRepository
from app.infrastructure.database.repositories.product_repository import ProductRepository
from app.infrastructure.ml.intent_predictor import IntentPredictionEngine
from app.infrastructure.ml.stock_predictor import StockPredictionEngine


class ServiceContainer:
    """Composition Root de la aplicación.

    Centraliza la creación e inyección de dependencias. Las capas superiores
    reciben repositorios y motores por constructor en lugar de crearlos por su cuenta.
    """

    def __init__(self):
        # Infraestructura
        self.db = MySQLConnectionFactory()
        self.product_repository = ProductRepository(self.db)
        self.consultation_repository = ConsultationRepository(self.db)
        self.history_repository = PredictionHistoryRepository(self.db)
        self.intent_engine = IntentPredictionEngine()
        self.stock_engine = StockPredictionEngine()

        # Observer de alertas
        self.alert_subject = AlertSubject()
        self.bell_observer = BellAlertObserver()
        self.alert_subject.attach(self.bell_observer)

        # Casos de uso / servicios de aplicación
        self.prediction_service = PredictionService(
            self.product_repository,
            self.history_repository,
            self.stock_engine,
        )
        self.evaluation_service = EvaluationService(
            self.prediction_service,
            self.history_repository,
            self.alert_subject,
        )
        self.alert_service = AlertService(
            self.prediction_service,
            self.bell_observer,
        )
        self.assistant_service = AssistantService(
            self.product_repository,
            self.consultation_repository,
            self.prediction_service,
            self.intent_engine,
        )
        self.dashboard_service = DashboardService(
            self.consultation_repository,
            self.product_repository,
            self.intent_engine,
        )
