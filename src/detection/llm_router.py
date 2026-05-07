"""LLM Router con fallback Anthropic → Ollama (ADR-002, ADR-007).

Estrategia:
- Primario: Anthropic ``claude-haiku-4-5-20251001`` (costo-eficiente
  para análisis masivo). El modelo Opus se reserva para razonamiento
  jurídico explícito invocado a mano.
- Fallback automático a Ollama ``qwen3:8b`` si:
  - ``OFFLINE_MODE=1`` en env / settings,
  - ``ANTHROPIC_API_KEY`` ausente o vacía,
  - timeout (>6s) en la llamada Anthropic,
  - HTTP 5xx de Anthropic.
- Si ambos fallan se levanta ``RouterError``.

``route`` es async y devuelve metadata de la ejecución (modelo,
latencia, tokens, costo, fallback usado). Cada llamada emite un
log JSON estructurado.

``analyze_contract`` mantiene la firma estable usada por la CLI; con
``use_llm=True`` invoca ``route`` y combina linealmente
``score = 0.7·rule_score + 0.3·llm_severity`` (ADR-007).
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from typing import Any

import httpx
from pydantic import BaseModel, Field

from src.config import get_settings
from src.detection.rules import RuleHit
from src.ingestion.normalizer import Contract

logger = logging.getLogger(__name__)

DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_OLLAMA_MODEL = "qwen3:8b"
ANTHROPIC_TIMEOUT_S = 6.0
OLLAMA_TIMEOUT_S = 60.0
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# USD por 1M tokens (input, output) — claude-haiku-4-5 pricing 2026.
ANTHROPIC_PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (1.0, 5.0),
}

LLM_WEIGHT = 0.3
RULE_WEIGHT = 0.7


class RouterError(RuntimeError):
    """Falla terminal del Router (ambos proveedores caídos)."""


class OpacityScore(BaseModel):
    """Score agregado de opacidad para un contrato."""

    contract_id: str
    score: float = Field(ge=0.0, le=1.0)
    signals: list[str] = Field(default_factory=list)
    rationale: str = ""
    source_url: str = ""
    model_used: str = "rules-only"


async def route(
    prompt: str,
    task_type: str = "scoring",
    *,
    fallback_to_local: bool = True,
    max_tokens: int = 256,
    temperature: float = 0.0,
) -> dict[str, Any]:
    """Despacha a Anthropic con fallback automático a Ollama.

    Args:
        prompt: Texto a enviar al LLM.
        task_type: Etiqueta del tipo de tarea (logging y enrutamiento
            futuro). Hoy informativo.
        fallback_to_local: Si True (default), una falla recuperable de
            Anthropic activa Ollama. Si False, se levanta ``RouterError``.
        max_tokens: Máximo de tokens en la respuesta.
        temperature: Determinismo (0.0 para auditoría).

    Returns:
        Dict con ``output``, ``model_used``, ``latency_ms``,
        ``tokens_in``, ``tokens_out``, ``cost_usd``, ``fallback_used``,
        ``fallback_reason``.

    Raises:
        RouterError: Si Anthropic falla y o bien ``fallback_to_local``
            es False, o bien Ollama también falla.
    """
    settings = get_settings()
    fallback_reason: str | None = None

    if settings.offline_mode:
        fallback_reason = "OFFLINE_MODE=1"
    elif not settings.anthropic_api_key:
        fallback_reason = "ANTHROPIC_API_KEY ausente"

    if fallback_reason is None:
        try:
            return await _call_anthropic(
                prompt,
                api_key=settings.anthropic_api_key,
                max_tokens=max_tokens,
                temperature=temperature,
                task_type=task_type,
            )
        except (httpx.TimeoutException, TimeoutError) as e:
            fallback_reason = f"timeout: {e!s}"
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if 500 <= status < 600:
                fallback_reason = f"anthropic-5xx-{status}"
            else:
                # 4xx, 401, etc. — error del cliente, no fallback.
                raise RouterError(
                    f"Anthropic error no recuperable: {status}"
                ) from e

    if not fallback_to_local:
        raise RouterError(f"Anthropic falló: {fallback_reason}")

    try:
        return await _call_ollama(
            prompt,
            base_url=settings.ollama_base_url,
            max_tokens=max_tokens,
            temperature=temperature,
            fallback_reason=fallback_reason,
            task_type=task_type,
        )
    except Exception as e:
        raise RouterError(
            f"Ambos proveedores fallaron (anthropic: {fallback_reason}; "
            f"ollama: {e!s})"
        ) from e


async def _call_anthropic(
    prompt: str,
    *,
    api_key: str,
    max_tokens: int,
    temperature: float,
    task_type: str,
) -> dict[str, Any]:
    start = time.monotonic()
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": DEFAULT_ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    async with httpx.AsyncClient(timeout=ANTHROPIC_TIMEOUT_S) as client:
        resp = await client.post(ANTHROPIC_URL, json=payload, headers=headers)
        resp.raise_for_status()

    body = resp.json()
    latency_ms = (time.monotonic() - start) * 1000
    output = ""
    if isinstance(body.get("content"), list) and body["content"]:
        first = body["content"][0]
        if isinstance(first, dict):
            output = first.get("text", "") or ""
    usage = body.get("usage", {}) or {}
    tokens_in = int(usage.get("input_tokens", 0) or 0)
    tokens_out = int(usage.get("output_tokens", 0) or 0)
    p_in, p_out = ANTHROPIC_PRICING.get(DEFAULT_ANTHROPIC_MODEL, (0.0, 0.0))
    cost = tokens_in / 1_000_000 * p_in + tokens_out / 1_000_000 * p_out
    result: dict[str, Any] = {
        "output": output,
        "model_used": DEFAULT_ANTHROPIC_MODEL,
        "latency_ms": latency_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": cost,
        "fallback_used": False,
        "fallback_reason": None,
    }
    _log_call(provider="anthropic", task_type=task_type, **result)
    return result


async def _call_ollama(
    prompt: str,
    *,
    base_url: str,
    max_tokens: int,
    temperature: float,
    fallback_reason: str | None,
    task_type: str,
) -> dict[str, Any]:
    start = time.monotonic()
    payload = {
        "model": DEFAULT_OLLAMA_MODEL,
        "prompt": prompt,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
        "stream": False,
    }
    url = f"{base_url.rstrip('/')}/api/generate"
    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT_S) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()

    body = resp.json()
    latency_ms = (time.monotonic() - start) * 1000
    tokens_in = int(body.get("prompt_eval_count", 0) or 0)
    tokens_out = int(body.get("eval_count", 0) or 0)
    result: dict[str, Any] = {
        "output": body.get("response", "") or "",
        "model_used": DEFAULT_OLLAMA_MODEL,
        "latency_ms": latency_ms,
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "cost_usd": 0.0,
        "fallback_used": fallback_reason is not None,
        "fallback_reason": fallback_reason,
    }
    _log_call(provider="ollama", task_type=task_type, **result)
    return result


def _log_call(*, provider: str, task_type: str, **fields: Any) -> None:
    record = {
        "event": "llm_call",
        "provider": provider,
        "task_type": task_type,
        **fields,
    }
    logger.info(json.dumps(record, default=str))


def analyze_contract(
    contract: Contract,
    hits: list[RuleHit],
    *,
    use_llm: bool = False,
) -> OpacityScore:
    """Combina reglas y (opcionalmente) LLM en un OpacityScore.

    Si ``use_llm=True`` se invoca ``route`` y se mezcla linealmente
    ``score = 0.7·rule_score + 0.3·llm_severity`` (ADR-007). Si el
    Router falla terminalmente (RouterError), el score se entrega
    igual usando solo las reglas y el ``model_used`` queda como
    ``rules-only``; la rationale anota la falla.
    """
    rule_score = _aggregate_rule_score(hits)
    signals = sorted({h.rule_id for h in hits})
    rationale_parts = [h.rationale for h in hits]

    if not hits:
        return OpacityScore(
            contract_id=contract.id,
            score=0.0,
            source_url=contract.source_url,
            model_used="rules-only",
        )

    if not use_llm:
        return OpacityScore(
            contract_id=contract.id,
            score=rule_score,
            signals=signals,
            rationale=" · ".join(rationale_parts),
            source_url=contract.source_url,
            model_used="rules-only",
        )

    prompt = _build_prompt(contract, hits)
    try:
        result = _run_route(prompt)
    except RouterError as e:
        return OpacityScore(
            contract_id=contract.id,
            score=rule_score,
            signals=signals,
            rationale=(
                " · ".join(rationale_parts)
                + f" [llm caído: {e}; score = solo reglas]"
            ),
            source_url=contract.source_url,
            model_used="rules-only",
        )

    llm_severity = _parse_llm_severity(result["output"])
    final_score = min(
        1.0, RULE_WEIGHT * rule_score + LLM_WEIGHT * llm_severity
    )
    return OpacityScore(
        contract_id=contract.id,
        score=final_score,
        signals=signals,
        rationale=(
            " · ".join(rationale_parts)
            + f" | LLM severity={llm_severity:.2f} ({result['model_used']})"
        ),
        source_url=contract.source_url,
        model_used=result["model_used"],
    )


def _run_route(prompt: str) -> dict[str, Any]:
    """Wrap async ``route`` para usarlo desde código sync.

    Si ya hay un event loop corriendo (e.g. Streamlit con uvicorn) se
    levanta error: en ese caso el llamador debe usar ``await route``
    directamente.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(route(prompt))
    raise RouterError(
        "analyze_contract sync invocada desde async context; "
        "usá `await route(...)` directamente"
    )


def _aggregate_rule_score(hits: list[RuleHit]) -> float:
    if not hits:
        return 0.0
    return min(1.0, sum(h.weight for h in hits) / len(hits))


def _build_prompt(contract: Contract, hits: list[RuleHit]) -> str:
    lines = [
        "Eres un auditor de contratación pública en Colombia.",
        "Evaluá la siguiente alerta de opacidad estadística sobre un",
        "contrato del SECOP II y devolvé UN único número entre 0 y 1",
        "que represente la severidad cualitativa adicional a las reglas.",
        "NO acuses corrupción. NO afirmes intencionalidad. Cita la",
        "regla legal solo si es explícitamente aplicable.",
        "",
        f"Contrato: {contract.id}",
        f"Entidad: {contract.entity}",
        f"Proveedor: {contract.contractor}",
        f"Modalidad: {contract.modality}",
        f"Valor: {contract.value}",
        "",
        "Reglas activadas:",
    ]
    for h in hits:
        lines.append(f"- [{h.rule_id}] {h.rationale}")
    lines.append("")
    lines.append("Responde SOLO con el número (e.g. 0.55).")
    return "\n".join(lines)


def _parse_llm_severity(text: str) -> float:
    """Extrae el primer número en [0, 1] del output del LLM."""
    m = re.search(r"\b(?:0?\.\d+|0|1(?:\.0)?)\b", text.strip())
    if not m:
        return 0.0
    try:
        v = float(m.group(0))
    except ValueError:
        return 0.0
    return max(0.0, min(1.0, v))
