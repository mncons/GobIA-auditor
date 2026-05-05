"""LLM Router: enriquecimiento cualitativo del score de opacidad.

Estrategia: Anthropic Claude Opus 4.7 como modelo principal; Ollama
local (qwen3) como fallback para soberanía técnica y demo offline.

Esta función es invocada solamente sobre contratos que ya activaron al
menos una regla determinística — el LLM no decide opacidad por sí mismo
(ver ADR-003).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.detection.rules import RuleHit
from src.ingestion.normalizer import Contract


class OpacityScore(BaseModel):
    """Score agregado de opacidad para un contrato.

    Attributes:
        contract_id: Identificador del contrato evaluado.
        score: Valor agregado en [0.0, 1.0]. NO es probabilidad de
            corrupción; es índice compuesto de señales activadas.
        signals: Ids de señales activadas (e.g. ["OP-01", "OP-02"]).
        rationale: Explicación humana, citable, sin atribuciones de
            intencionalidad.
        source_url: URL pública del contrato en community.secop.gov.co.
        model_used: Nombre del modelo que generó la racionalización.
    """

    contract_id: str
    score: float = Field(ge=0.0, le=1.0)
    signals: list[str] = Field(default_factory=list)
    rationale: str = ""
    source_url: str = ""
    model_used: str = "rules-only"


def analyze_contract(
    contract: Contract,
    hits: list[RuleHit],
    *,
    use_llm: bool = False,
) -> OpacityScore:
    """Calcula el OpacityScore final combinando reglas y LLM opcional.

    Args:
        contract: Contrato normalizado bajo evaluación.
        hits: RuleHits que disparó este contrato. Si está vacío, el
            score es 0.0 y no se invoca al LLM.
        use_llm: Si True, intenta enriquecer con Anthropic / Ollama.
            Si False, devuelve un score basado únicamente en reglas
            (modo determinístico, auditable, gratuito).

    Returns:
        OpacityScore listo para persistir y reportar.

    Notes:
        STUB del routing real: en este sprint la combinación de reglas
        es lineal y la llamada a LLM no se ejecuta para no gastar cuota
        durante desarrollo. La firma sí es estable.
    """
    if not hits:
        return OpacityScore(
            contract_id=contract.id,
            score=0.0,
            source_url=contract.source_url,
            model_used="rules-only",
        )

    base_score = min(1.0, sum(h.weight for h in hits) / len(hits))
    signals = sorted({h.rule_id for h in hits})
    rationale = " · ".join(h.rationale for h in hits)

    if use_llm:
        # WHY: el llamado real a Anthropic / Ollama queda diferido al
        # próximo sprint para no gastar cuota durante el scaffold.
        # Mantener el branch documentado preserva la firma de routing.
        rationale = f"[stub-llm-router] {rationale}"
        model_used = "claude-opus-4-7+ollama-fallback"
    else:
        model_used = "rules-only"

    return OpacityScore(
        contract_id=contract.id,
        score=base_score,
        signals=signals,
        rationale=rationale,
        source_url=contract.source_url,
        model_used=model_used,
    )
