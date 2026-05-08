"""Smoke real contra Ollama local con qwen3:1.7b (ADR-002, ADR-010).

Diferente a ``test_llm_router.py``: este módulo NO mockea — pega contra
``http://localhost:11434`` real. Se marca con ``@pytest.mark.integration``
y se excluye del run normal con ``pytest -q -m "not integration"``.

Skip-policy:
- Si Ollama no responde en 1s → ``pytest.skip``.
- Si ``qwen3:1.7b`` no está pulled → ``pytest.skip`` con instrucción.

Latencia objetivo en T495 sin GPU: <25s para un prompt de ~50 tokens con
el modelo ya caliente (segunda llamada o `keep_alive` activo). Si excede,
``pytest.xfail`` con el dato — no rompe el suite, deja la señal.
"""

from __future__ import annotations

import os
import time
from datetime import date
from decimal import Decimal

import httpx
import pytest

from src.detection.llm_router import DEFAULT_OLLAMA_MODEL, route
from src.detection.rules import RuleHit
from src.ingestion.normalizer import Contract

pytestmark = pytest.mark.integration

OLLAMA_BASE = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
LATENCY_BUDGET_S = 25.0


@pytest.fixture(scope="module")
def ollama_alive() -> None:
    """Skipea si Ollama no responde o si qwen3:1.7b no está instalado."""
    try:
        resp = httpx.get(f"{OLLAMA_BASE}/api/tags", timeout=1.0)
        resp.raise_for_status()
    except (httpx.HTTPError, httpx.ConnectError) as e:
        pytest.skip(f"Ollama no responde en {OLLAMA_BASE} ({e!s})")
    models = {m.get("name") for m in resp.json().get("models", [])}
    if DEFAULT_OLLAMA_MODEL not in models:
        pytest.skip(
            f"{DEFAULT_OLLAMA_MODEL} no instalado — correr "
            f"`ollama pull {DEFAULT_OLLAMA_MODEL}`"
        )


@pytest.fixture
def offline_real(monkeypatch) -> None:
    """Fuerza OFFLINE_MODE y apunta al Ollama real."""
    monkeypatch.setenv("OFFLINE_MODE", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("OLLAMA_BASE_URL", OLLAMA_BASE)


def _prompt_smoke() -> str:
    """Prompt ~50 tokens equivalente al de scoring real (ADR-007)."""
    contract = Contract(
        id="CO1.PCCNTR.SMOKE-INT",
        entity="EntidadSmoke",
        contractor="ProveedorSmoke",
        contractor_id="900",
        value=Decimal("50000000"),
        signed_date=date(2026, 4, 1),
        modality="minima_cuantia",
    )
    hit = RuleHit(
        contract_id=contract.id,
        rule_id="OP-01",
        weight=0.6,
        rationale="proveedor concentra 80% del lote",
    )
    return (
        "Devolvé un único número en [0,1] como severidad cualitativa "
        f"para el contrato {contract.id} de {contract.entity} "
        f"con proveedor {contract.contractor}. Regla activa: "
        f"[{hit.rule_id}] {hit.rationale}. Responde SOLO el número."
    )


@pytest.mark.asyncio
async def test_smoke_offline_qwen3_1_7b_responde_bajo_25s(
    ollama_alive, offline_real
) -> None:
    """Smoke real: route() debe responder con qwen3:1.7b sin <think>.

    Latencia <25s es un soft-fail (xfail) — depende de si el modelo está
    caliente. La aserción dura es: respuesta válida y sin bloque de
    razonamiento explícito (think=False efectivo).
    """
    prompt = _prompt_smoke()
    start = time.monotonic()
    res = await route(prompt, task_type="smoke-integration")
    elapsed = time.monotonic() - start

    assert res["model_used"] == DEFAULT_OLLAMA_MODEL
    assert res["fallback_used"] is True
    assert res["fallback_reason"] == "OFFLINE_MODE=1"
    assert isinstance(res["output"], str) and len(res["output"]) > 0
    # WHY: si el bloque <think>...</think> aparece, think=False no llegó.
    assert "<think>" not in res["output"].lower()

    if elapsed > LATENCY_BUDGET_S:
        pytest.xfail(
            f"latencia {elapsed:.1f}s excede budget {LATENCY_BUDGET_S}s "
            f"— modelo frío, GPU compartida o T495 saturada"
        )
