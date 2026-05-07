"""Tests del LLM Router (ADR-002, ADR-007).

Todos los tests son offline: usan ``pytest-httpx`` para interceptar
llamadas a Anthropic y Ollama. Cero llamadas reales a Anthropic.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import httpx
import pytest

from src.detection.llm_router import (
    DEFAULT_ANTHROPIC_MODEL,
    DEFAULT_OLLAMA_MODEL,
    OpacityScore,
    RouterError,
    analyze_contract,
    route,
)
from src.detection.rules import RuleHit
from src.ingestion.normalizer import Contract

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OLLAMA_BASE = "http://localhost:11434"
OLLAMA_GENERATE = f"{OLLAMA_BASE}/api/generate"


def _anthropic_response(text: str = "0.7") -> dict:
    return {
        "content": [{"type": "text", "text": text}],
        "usage": {"input_tokens": 120, "output_tokens": 5},
    }


def _ollama_response(text: str = "0.5") -> dict:
    return {
        "response": text,
        "prompt_eval_count": 80,
        "eval_count": 6,
    }


@pytest.fixture
def use_anthropic_key(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("OFFLINE_MODE", "0")
    monkeypatch.setenv("OLLAMA_BASE_URL", OLLAMA_BASE)


@pytest.fixture
def offline_mode(monkeypatch) -> None:
    monkeypatch.setenv("OFFLINE_MODE", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("OLLAMA_BASE_URL", OLLAMA_BASE)


@pytest.fixture
def no_anthropic_key(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("OFFLINE_MODE", "0")
    monkeypatch.setenv("OLLAMA_BASE_URL", OLLAMA_BASE)


@pytest.mark.asyncio
async def test_route_anthropic_exito(httpx_mock, use_anthropic_key) -> None:
    httpx_mock.add_response(url=ANTHROPIC_URL, json=_anthropic_response("0.6"))
    res = await route("evalúa este contrato")
    assert res["model_used"] == DEFAULT_ANTHROPIC_MODEL
    assert res["fallback_used"] is False
    assert res["tokens_in"] == 120
    assert res["tokens_out"] == 5
    assert res["cost_usd"] > 0
    assert res["output"] == "0.6"


@pytest.mark.asyncio
async def test_route_fallback_a_ollama_si_timeout(
    httpx_mock, use_anthropic_key
) -> None:
    httpx_mock.add_exception(
        httpx.TimeoutException("anthropic timeout"), url=ANTHROPIC_URL
    )
    httpx_mock.add_response(url=OLLAMA_GENERATE, json=_ollama_response("0.4"))
    res = await route("eval")
    assert res["model_used"] == DEFAULT_OLLAMA_MODEL
    assert res["fallback_used"] is True
    assert "timeout" in res["fallback_reason"]


@pytest.mark.asyncio
async def test_route_fallback_a_ollama_si_5xx(
    httpx_mock, use_anthropic_key
) -> None:
    httpx_mock.add_response(url=ANTHROPIC_URL, status_code=500)
    httpx_mock.add_response(url=OLLAMA_GENERATE, json=_ollama_response())
    res = await route("eval")
    assert res["model_used"] == DEFAULT_OLLAMA_MODEL
    assert res["fallback_used"] is True
    assert "anthropic-5xx-500" in res["fallback_reason"]


@pytest.mark.asyncio
async def test_route_offline_mode_va_directo_a_ollama(
    httpx_mock, offline_mode
) -> None:
    httpx_mock.add_response(url=OLLAMA_GENERATE, json=_ollama_response())
    res = await route("eval")
    assert res["model_used"] == DEFAULT_OLLAMA_MODEL
    assert res["fallback_used"] is True
    assert res["fallback_reason"] == "OFFLINE_MODE=1"
    # No hubo request a Anthropic
    assert all(
        r.url.host != "api.anthropic.com" for r in httpx_mock.get_requests()
    )


@pytest.mark.asyncio
async def test_route_sin_key_va_directo_a_ollama(
    httpx_mock, no_anthropic_key
) -> None:
    httpx_mock.add_response(url=OLLAMA_GENERATE, json=_ollama_response())
    res = await route("eval")
    assert res["fallback_used"] is True
    assert res["fallback_reason"] == "ANTHROPIC_API_KEY ausente"


@pytest.mark.asyncio
async def test_route_4xx_no_hace_fallback(
    httpx_mock, use_anthropic_key
) -> None:
    httpx_mock.add_response(
        url=ANTHROPIC_URL, status_code=401, json={"error": "invalid api key"}
    )
    with pytest.raises(RouterError):
        await route("eval")


@pytest.mark.asyncio
async def test_route_ambos_proveedores_caen(
    httpx_mock, use_anthropic_key
) -> None:
    httpx_mock.add_response(url=ANTHROPIC_URL, status_code=500)
    httpx_mock.add_response(url=OLLAMA_GENERATE, status_code=500)
    with pytest.raises(RouterError):
        await route("eval")


@pytest.mark.asyncio
async def test_route_fallback_disabled_propaga_error(
    httpx_mock, use_anthropic_key
) -> None:
    httpx_mock.add_response(url=ANTHROPIC_URL, status_code=500)
    with pytest.raises(RouterError):
        await route("eval", fallback_to_local=False)


# ---------------------------------------------------------------------------
# analyze_contract sync (ADR-007: combinación lineal regla+LLM)
# ---------------------------------------------------------------------------


def _contract() -> Contract:
    return Contract(
        id="CO1.PCCNTR.TEST",
        entity="EntidadTest",
        contractor="ProveedorTest",
        contractor_id="900",
        value=Decimal("1000000"),
        signed_date=date(2026, 1, 15),
        modality="minima_cuantia",
    )


def _hits() -> list[RuleHit]:
    return [
        RuleHit(
            contract_id="CO1.PCCNTR.TEST",
            rule_id="OP-01",
            weight=0.6,
            rationale="proveedor concentra 60% del lote",
        ),
    ]


def test_analyze_contract_solo_reglas_no_llama_llm() -> None:
    """use_llm=False → no debería tocar HTTP (sin pytest_httpx aquí)."""
    score = analyze_contract(_contract(), _hits(), use_llm=False)
    assert isinstance(score, OpacityScore)
    assert score.model_used == "rules-only"
    assert score.score == 0.6
    assert score.signals == ["OP-01"]


def test_analyze_contract_sin_hits_devuelve_cero() -> None:
    score = analyze_contract(_contract(), [], use_llm=True)
    assert score.score == 0.0
    assert score.model_used == "rules-only"
