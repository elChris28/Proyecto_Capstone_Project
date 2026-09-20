from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass(frozen=True)
class RiskEvaluationEvent:
    evaluacion_id: int
    fecha_evaluacion: datetime
    total_productos: int
    alto_riesgo: int
    medio_riesgo: int
    bajo_riesgo: int


class AlertObserver(ABC):
    @abstractmethod
    def update(self, event: RiskEvaluationEvent) -> None:
        raise NotImplementedError


class AlertSubject:
    """Subject del patrón Observer para eventos de evaluación de riesgo."""

    def __init__(self):
        self._observers: List[AlertObserver] = []

    def attach(self, observer: AlertObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: AlertObserver) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event: RiskEvaluationEvent) -> None:
        for observer in list(self._observers):
            observer.update(event)
