"""Adapter sobre SECOP II (jbjy-vk9h) — envuelve ``SecopClient``."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from src.ingestion.adapters.base import BaseAdapter
from src.ingestion.normalizer import Contract, normalize
from src.ingestion.secop_client import SecopClient


class SecopAdapter(BaseAdapter):
    """Adapter de SECOP II (dataset Socrata canónico ``jbjy-vk9h``)."""

    def __init__(self, client: SecopClient | None = None) -> None:
        self.client = client or SecopClient()

    async def fetch(
        self,
        filters: dict[str, Any],
        limit: int = 1000,
    ) -> AsyncIterator[dict[str, Any]]:
        """Itera contratos paginados respetando los filtros Socrata dados."""
        async with self.client:
            async for item in self.client.search_contracts(
                filters, limit=limit
            ):
                yield item

    def normalize(self, raw: dict[str, Any]) -> Contract | None:
        """Aplica el normalizer canónico; retorna None si falta ``id_contrato``."""
        if not raw.get("id_contrato") and not raw.get("referencia_contrato"):
            return None
        return normalize(raw)
