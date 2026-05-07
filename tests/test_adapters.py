"""Tests para adapters: SECOP y GenericSocrata."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.ingestion.adapters import GenericSocrataAdapter, SecopAdapter
from src.ingestion.secop_client import SecopCache, SecopClient


@pytest.fixture
def cache(tmp_path):
    return SecopCache(path=tmp_path / "cache.db", ttl_hours=24)


SECOP_SAMPLE = {
    "id_contrato": "CO1.PCCNTR.ADAPT-001",
    "nombre_entidad": "Entidad Adapter",
    "proveedor_adjudicado": "Proveedor Adapter SAS",
    "nit_del_proveedor_adjudicado": "900000999",
    "valor_del_contrato": "5000000",
    "fecha_de_firma": "2026-02-10T00:00:00.000",
    "modalidad_de_contratacion": "Mínima cuantía",
    "rama": "Ejecutiva",
    "urlproceso": {
        "url": (
            "https://community.secop.gov.co/Public/Tendering/"
            "OpportunityDetail/Index?noticeUID=CO1.NTC.000999"
        )
    },
}

ENERGY_SAMPLE = {
    "id_contrato_sui": "SUI-2026-0001",
    "nombre_entidad": "Empresa Pública Distrital",
    "nombre_operador": "Operador Energía S.A. ESP",
    "nit_operador": "800123456",
    "valor_negociacion": "150000000",
    "fecha_firma": "2026-03-15T00:00:00.000",
    "tipo_negociacion": "Bolsa día siguiente",
}

ENERGY_DATASET = "https://www.datos.gov.co/resource/abcd-1234.json"


@pytest.mark.asyncio
async def test_secop_adapter_fetch_y_normalize(httpx_mock, cache) -> None:
    httpx_mock.add_response(json=[SECOP_SAMPLE])
    adapter = SecopAdapter(client=SecopClient(cache=cache))

    items = [item async for item in adapter.fetch({"$where": "1=1"}, limit=10)]
    assert len(items) == 1

    contract = adapter.normalize(items[0])
    assert contract is not None
    assert contract.id == "CO1.PCCNTR.ADAPT-001"
    assert contract.contractor == "Proveedor Adapter SAS"
    assert contract.value == Decimal("5000000")
    assert contract.signed_date == date(2026, 2, 10)
    assert contract.source_url.startswith("https://community.secop.gov.co/")


def test_secop_adapter_normalize_sin_id_devuelve_none() -> None:
    adapter = SecopAdapter()
    assert adapter.normalize({"nombre_entidad": "x"}) is None


@pytest.mark.asyncio
async def test_generic_socrata_aplica_field_mapping(httpx_mock, cache) -> None:
    httpx_mock.add_response(json=[ENERGY_SAMPLE])
    mapping = {
        "id": "id_contrato_sui",
        "buyer_name": "nombre_entidad",
        "supplier_name": "nombre_operador",
        "supplier_id": "nit_operador",
        "value": "valor_negociacion",
        "date": "fecha_firma",
        "modality": "tipo_negociacion",
    }
    client = SecopClient(base_url=ENERGY_DATASET, cache=cache)
    adapter = GenericSocrataAdapter(ENERGY_DATASET, mapping, client=client)
    items = [item async for item in adapter.fetch({}, limit=10)]
    contract = adapter.normalize(items[0])

    assert contract is not None
    assert contract.id == "SUI-2026-0001"
    assert contract.contractor == "Operador Energía S.A. ESP"
    assert contract.contractor_id == "800123456"
    assert contract.value == Decimal("150000000")
    assert contract.signed_date == date(2026, 3, 15)
    assert contract.modality == "Bolsa día siguiente"


def test_generic_socrata_field_mapping_incompleto_falla() -> None:
    with pytest.raises(ValueError, match="field_mapping incompleto"):
        GenericSocrataAdapter(ENERGY_DATASET, {"id": "x"})


def test_generic_socrata_normalize_sin_supplier_devuelve_none() -> None:
    mapping = {
        "id": "id_contrato_sui",
        "buyer_name": "nombre_entidad",
        "supplier_name": "nombre_operador",
    }
    adapter = GenericSocrataAdapter(ENERGY_DATASET, mapping)
    raw = {"id_contrato_sui": "X", "nombre_entidad": "E"}  # falta supplier
    assert adapter.normalize(raw) is None
