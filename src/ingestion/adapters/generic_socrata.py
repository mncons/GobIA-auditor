"""Adapter genérico para datasets Socrata distintos a SECOP II.

Recibe un ``dataset_url`` y un ``field_mapping`` que traduce los
nombres del dataset destino a los del Contract canónico. Reusa el
``SecopClient`` (httpx + cache + retry + paginación) sin reescribir
nada.

Ejemplo (reto sorpresa hackathon — energía SUI):

    mapping = {
        "id": "id_contrato_sui",
        "buyer_name": "nombre_entidad",
        "supplier_name": "nombre_operador",
        "supplier_id": "nit_operador",
        "value": "valor_negociacion",
        "date": "fecha_firma",
        "modality": "tipo_negociacion",
    }
    adapter = GenericSocrataAdapter(
        dataset_url="https://www.datos.gov.co/resource/abcd-1234.json",
        field_mapping=mapping,
    )
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from src.ingestion.adapters.base import BaseAdapter
from src.ingestion.normalizer import Contract
from src.ingestion.secop_client import SecopClient

REQUIRED_KEYS = ("id", "buyer_name", "supplier_name")


class GenericSocrataAdapter(BaseAdapter):
    """Adapter genérico Socrata via field_mapping declarativo."""

    def __init__(
        self,
        dataset_url: str,
        field_mapping: dict[str, str],
        client: SecopClient | None = None,
    ) -> None:
        missing = [k for k in REQUIRED_KEYS if k not in field_mapping]
        if missing:
            raise ValueError(
                f"field_mapping incompleto, faltan: {missing}. "
                f"Requeridos siempre: {REQUIRED_KEYS}"
            )
        self.dataset_url = dataset_url
        self.field_mapping = field_mapping
        self._client = client

    async def fetch(
        self,
        filters: dict[str, Any],
        limit: int = 1000,
    ) -> AsyncIterator[dict[str, Any]]:
        client = self._client or SecopClient(base_url=self.dataset_url)
        async with client:
            async for item in client.search_contracts(filters, limit=limit):
                yield item

    def normalize(self, raw: dict[str, Any]) -> Contract | None:
        m = self.field_mapping
        cid = str(raw.get(m["id"], "") or "")
        entity = str(raw.get(m["buyer_name"], "") or "")
        contractor = str(raw.get(m["supplier_name"], "") or "")
        if not cid or not entity or not contractor:
            return None

        contractor_id: str | None = None
        if "supplier_id" in m:
            value = raw.get(m["supplier_id"])
            if value:
                contractor_id = str(value)

        value_dec = Decimal("0")
        if "value" in m:
            try:
                value_dec = Decimal(str(raw.get(m["value"], "0") or "0"))
            except InvalidOperation:
                value_dec = Decimal("0")

        return Contract(
            id=cid,
            entity=entity,
            contractor=contractor,
            contractor_id=contractor_id,
            value=value_dec,
            signed_date=_parse_date_field(raw, m, "date"),
            start_date=_parse_date_field(raw, m, "start_date"),
            end_date=_parse_date_field(raw, m, "end_date"),
            modality=str(raw.get(m.get("modality", ""), "") or "no_definida"),
            sector=str(raw.get(m.get("sector", ""), "") or "no_definido"),
            source_url=str(raw.get(m.get("source_url", ""), "") or ""),
        )


def _parse_date_field(
    raw: dict[str, Any], mapping: dict[str, str], key: str
) -> date | None:
    field = mapping.get(key)
    if not field:
        return None
    raw_val = raw.get(field)
    if not raw_val:
        return None
    try:
        return date.fromisoformat(str(raw_val)[:10])
    except ValueError:
        return None
