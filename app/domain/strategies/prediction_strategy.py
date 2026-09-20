from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PredictionStrategy(ABC):
    """Contrato para ejecutar modelos de clasificación de riesgo.

    Strategy permite cambiar el estimador sin modificar el motor de inferencia.
    """

    def __init__(self, estimator: Any):
        self.estimator = estimator

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    def predict_probability(self, X):
        return self.estimator.predict_proba(X)[:, 1]


class LogisticRegressionStrategy(PredictionStrategy):
    @property
    def name(self) -> str:
        return "Regresión Logística"


class RandomForestStrategy(PredictionStrategy):
    @property
    def name(self) -> str:
        return "Random Forest"


class GradientBoostingStrategy(PredictionStrategy):
    @property
    def name(self) -> str:
        return "Gradient Boosting"


class GenericSklearnStrategy(PredictionStrategy):
    @property
    def name(self) -> str:
        return self.estimator.__class__.__name__


def build_prediction_strategy(estimator: Any) -> PredictionStrategy:
    """Selecciona la estrategia apropiada según el estimador cargado."""
    nombre = estimator.__class__.__name__.lower()

    if "logistic" in nombre:
        return LogisticRegressionStrategy(estimator)
    if "randomforest" in nombre:
        return RandomForestStrategy(estimator)
    if "gradientboost" in nombre or "histgradientboost" in nombre:
        return GradientBoostingStrategy(estimator)

    return GenericSklearnStrategy(estimator)
