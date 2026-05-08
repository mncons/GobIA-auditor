"""Tests del LLM Router (ADR-002, ADR-007).

Todos los tests son offline: usan ``pytest-httpx`` para interceptar
llamadas a Anthropic y Ollama. Cero llamadas reales a Anthropic.
"""

from __future__ import annotations

import json
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
async def test_ollama_payload_override_via_env(
    httpx_mock, monkeypatch
) -> None:
    """Env vars OLLAMA_* deben sobreescribir los defaults sin recompilar.

    Útil para demo D2: si hay GPU disponible, OLLAMA_MODEL=qwen3:8b +
    OLLAMA_NUM_PREDICT=512 + OLLAMA_THINK=1 cambian el payload sin tocar
    código. El model_used reportado debe reflejar el override real.
    """
    monkeypatch.setenv("OFFLINE_MODE", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("OLLAMA_BASE_URL", OLLAMA_BASE)
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setenv("OLLAMA_NUM_PREDICT", "512")
    monkeypatch.setenv("OLLAMA_TEMPERATURE", "0.7")
    monkeypatch.setenv("OLLAMA_THINK", "1")
    monkeypatch.setenv("OLLAMA_KEEP_ALIVE", "-1")

    httpx_mock.add_response(url=OLLAMA_GENERATE, json=_ollama_response())
    res = await route("eval")

    body = json.loads(httpx_mock.get_requests(url=OLLAMA_GENERATE)[0].content)
    assert body["model"] == "qwen3:8b"
    assert body["think"] is True
    assert body["keep_alive"] == "-1"
    assert body["options"]["num_predict"] == 512
    assert body["options"]["temperature"] == 0.7
    assert res["model_used"] == "qwen3:8b"


@pytest.mark.asyncio
async def test_ollama_payload_endurecido(httpx_mock, offline_mode) -> None:
    """Valida que el payload Ollama lleva los 5 ajustes de demo D2.

    pytest-httpx con add_response NO valida bodies por defecto. Sin este
    test, mover think/keep_alive/num_predict adentro de options (donde
    Ollama los ignora) no rompería ningún test.
    """
    httpx_mock.add_response(url=OLLAMA_GENERATE, json=_ollama_response())
    await route("eval", max_tokens=999, temperature=0.99)
    body = json.loads(httpx_mock.get_requests(url=OLLAMA_GENERATE)[0].content)
    assert body["model"] == "qwen3:1.7b"
    assert body["think"] is False
    assert body["keep_alive"] == "30m"
    assert body["stream"] is False
    assert body["options"]["num_predict"] == 120
    assert body["options"]["temperature"] == 0.3
    # WHY: max_tokens/temperature del caller NO se filtran al payload Ollama.
    assert "max_tokens" not in body["options"]
    assert body["options"]["num_predict"] != 999
    assert body["options"]["temperature"] != 0.99


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
