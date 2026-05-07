"""Contrato de adapter de ingestión."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from src.ingestion.normalizer import Contract


class BaseAdapter(ABC):
    """Adapter mínimo: ``fetch`` items crudos y ``normalize`` a ``Contract``."""

    @abstractmethod
    def fetch(
        self,
        filters: dict[str, Any],
        limit: int = 1000,
    ) -> AsyncIterator[dict[str, Any]]:
        """Itera items crudos del dataset filtrado."""

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> Contract | None:
        """Convierte un item crudo a ``Contract``; None si datos mínimos faltan."""
