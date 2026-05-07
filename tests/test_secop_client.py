"""Tests del SecopClient: cache, retry, paginación, validación."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from src.ingestion.secop_client import SecopCache, SecopClient, SecopHTTPError

pytestmark = pytest.mark.asyncio

SAMPLE = {
    "id_contrato": "CO1.PCCNTR.X",
    "nombre_entidad": "Entidad Demo",
    "proveedor_adjudicado": "Proveedor SAS",
    "valor_del_contrato": "100000",
    "fecha_de_firma": "2026-01-15T00:00:00.000",
    "urlproceso": {
        "url": (
            "https://community.secop.gov.co/Public/Tendering/"
            "OpportunityDetail/Index?noticeUID=CO1.NTC.000001"
        )
    },
}

SECOP_BASE = "https://www.datos.gov.co/resource/jbjy-vk9h.json"


@pytest.fixture
def cache(tmp_path: Path) -> SecopCache:
    return SecopCache(path=tmp_path / "cache.db", ttl_hours=24)


@pytest.fixture
def non_mocked_hosts() -> list[str]:
    """pytest-httpx: no interceptar otros hosts."""
    return []


async def test_get_contracts_cache_miss_then_hit(
    httpx_mock, cache: SecopCache
) -> None:
    httpx_mock.add_response(json=[SAMPLE], status_code=200)
    async with SecopClient(cache=cache) as client:
        first = await client.get_contracts(date(2026, 1, 1), date(2026, 1, 31))
        second = await client.get_contracts(date(2026, 1, 1), date(2026, 1, 31))
    assert first == [SAMPLE]
    assert second == [SAMPLE]
    # Solo 1 request HTTP — el segundo call lo sirvió la cache SQLite
    assert len(httpx_mock.get_requests()) == 1


async def test_get_contracts_429_retry_after(
    httpx_mock, cache: SecopCache
) -> None:
    httpx_mock.add_response(status_code=429, headers={"retry-after": "0"})
    httpx_mock.add_response(json=[SAMPLE], status_code=200)
    async with SecopClient(cache=cache) as client:
        out = await client.get_contracts(date(2026, 1, 1), date(2026, 1, 2))
    assert out == [SAMPLE]
    assert len(httpx_mock.get_requests()) == 2


async def test_get_contracts_5xx_exhausts_retries(
    httpx_mock, cache: SecopCache
) -> None:
    for _ in range(3):
        httpx_mock.add_response(status_code=500)
    async with SecopClient(cache=cache) as client:
        with pytest.raises(SecopHTTPError):
            await client.get_contracts(date(2026, 1, 1), date(2026, 1, 2))
    assert len(httpx_mock.get_requests()) == 3


async def test_fetch_contract_devuelve_dict_o_none(
    httpx_mock, cache: SecopCache
) -> None:
    httpx_mock.add_response(json=[SAMPLE])
    async with SecopClient(cache=cache) as client:
        c = await client.fetch_contract("CO1.PCCNTR.X")
    assert c == SAMPLE

    httpx_mock.add_response(json=[])
    async with SecopClient(cache=cache) as client:
        miss = await client.fetch_contract("CO1.PCCNTR.MISS")
    assert miss is None


async def test_respuesta_no_lista_raises(
    httpx_mock, cache: SecopCache
) -> None:
    httpx_mock.add_response(json={"error": "bad"}, status_code=200)
    async with SecopClient(cache=cache) as client:
        with pytest.raises(SecopHTTPError):
            await client.get_contracts(date(2026, 1, 1), date(2026, 1, 2))


async def test_search_contracts_pagina_y_termina(
    httpx_mock, cache: SecopCache
) -> None:
    page1 = [{"id_contrato": f"P1-{i}", "valor_del_contrato": "1"} for i in range(3)]
    page2 = [{"id_contrato": "P2-0", "valor_del_contrato": "2"}]
    httpx_mock.add_response(json=page1)
    httpx_mock.add_response(json=page2)

    out: list[dict] = []
    async with SecopClient(cache=cache) as client:
        async for item in client.search_contracts(
            {"$where": "valor_del_contrato > 0"}, limit=10, page_size=3
        ):
            out.append(item)
    assert len(out) == 4
    assert out[0]["id_contrato"] == "P1-0"
    assert out[3]["id_contrato"] == "P2-0"


async def test_app_token_se_envia_si_provisto(
    httpx_mock, cache: SecopCache
) -> None:
    httpx_mock.add_response(json=[SAMPLE])
    async with SecopClient(cache=cache, app_token="abc123") as client:
        await client.get_contracts(date(2026, 1, 1), date(2026, 1, 2))
    req = httpx_mock.get_requests()[0]
    assert req.headers.get("x-app-token") == "abc123"
