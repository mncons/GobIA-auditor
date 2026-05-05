"""Generador de reportes Markdown sobre OpacityScores."""

from __future__ import annotations

from datetime import datetime

from src.detection.llm_router import OpacityScore


def generate(scores: list[OpacityScore], top_n: int = 20) -> str:
    """Genera un reporte Markdown ordenado por score descendente.

    Args:
        scores: Lista de OpacityScore producidos por el detection engine.
        top_n: Cuántos hallazgos incluir como máximo.

    Returns:
        Texto Markdown listo para escribir a disco o publicar tras
        revisión humana.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    sorted_scores = sorted(scores, key=lambda s: s.score, reverse=True)[:top_n]

    lines: list[str] = []
    lines.append("# Reporte GobIA Auditor")
    lines.append("")
    lines.append(f"_Generado: {timestamp}_")
    lines.append("")
    lines.append(
        "> **Aviso.** Este reporte señala opacidad estadística sobre "
        "datos públicos de SECOP II. No constituye acusación de "
        "corrupción ni dictamen jurídico. Cada hallazgo debe ser "
        "validado por veedores humanos antes de su publicación."
    )
    lines.append("")
    lines.append(f"Hallazgos incluidos: **{len(sorted_scores)}**")
    lines.append("")

    if not sorted_scores:
        lines.append("Sin hallazgos por encima del umbral.")
        return "\n".join(lines) + "\n"

    lines.append("## Top hallazgos")
    lines.append("")
    for i, s in enumerate(sorted_scores, start=1):
        lines.append(f"### {i}. Contrato {s.contract_id}")
        lines.append("")
        lines.append(f"- **Score:** {s.score:.2f}")
        lines.append(f"- **Señales activadas:** {', '.join(s.signals) or '—'}")
        lines.append(f"- **Modelo:** {s.model_used}")
        lines.append(f"- **Fuente:** {s.source_url or 'no disponible'}")
        if s.rationale:
            lines.append("")
            lines.append(f"> {s.rationale}")
        lines.append("")

    return "\n".join(lines) + "\n"
