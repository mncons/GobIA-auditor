"""Motor de reglas determinísticas para señales de opacidad.

Reglas reales (no stubs) sobre las que el LLM Router puede después
añadir contexto cualitativo:

- OP-01 Concentración por proveedor dentro de una entidad (top-share).
- OP-02 Valor del contrato fuera del rango intercuartílico del lote.
- OP-13 HHI de mercado (Σ share²) por entity, complementa OP-01.

Funciones puras adicionales (uso externo, no se invocan
automáticamente por ``RuleEngine.evaluate`` porque requieren peers
contextuales o historial de modificaciones que el motor no posee):

- ``temporal_anomaly`` — fast-response y duration-outlier vs cohort.
- ``modification_excess`` — adición acumulada y conteo (Art. 40
  parágrafo Ley 80 de 1993).
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

from src.ingestion.normalizer import Contract


@dataclass
class RuleHit:
    """Activación de una regla sobre un contrato concreto.

    Attributes:
        contract_id: Id del contrato que dispara la señal.
        rule_id: Identificador de la señal (e.g. "OP-01").
        weight: Peso de la regla, en el rango [0.0, 1.0].
        rationale: Frase explicativa citable.
    """

    contract_id: str
    rule_id: str
    weight: float
    rationale: str


@dataclass
class RuleEngine:
    """Motor de reglas estadísticas auditables.

    Attributes:
        concentration_threshold: Fracción de adjudicaciones a un mismo
            proveedor sobre el total de la entidad a partir del cual se
            considera concentración relevante.
        iqr_multiplier: Multiplicador de IQR para considerar un valor
            como outlier (default 1.5, convención Tukey).
    """

    concentration_threshold: float = 0.4
    iqr_multiplier: float = 1.5
    hhi_threshold: float = 0.25

    def evaluate(self, contracts: list[Contract]) -> list[RuleHit]:
        """Ejecuta todas las reglas sobre el lote de contratos.

        Args:
            contracts: Lista de contratos ya normalizados.

        Returns:
            Lista de RuleHit con todas las activaciones disparadas.
        """
        hits: list[RuleHit] = []
        hits.extend(self._concentration_by_contractor(contracts))
        hits.extend(self._value_iqr_outlier(contracts))
        hits.extend(self._hhi_market_concentration(contracts))
        return hits

    def _concentration_by_contractor(
        self, contracts: list[Contract]
    ) -> list[RuleHit]:
        """Detecta concentración de adjudicaciones por proveedor (OP-01).

        Args:
            contracts: Lote de contratos a evaluar.

        Returns:
            RuleHits para cada contrato cuya entidad concentra al
            proveedor por encima de concentration_threshold.
        """
        by_entity: dict[str, list[Contract]] = defaultdict(list)
        for c in contracts:
            by_entity[c.entity].append(c)

        hits: list[RuleHit] = []
        for entity, lote in by_entity.items():
            if len(lote) < 3:
                # WHY: con menos de 3 contratos por entidad, la fracción
                # no es estadísticamente significativa.
                continue
            counts = Counter(c.contractor_id or c.contractor for c in lote)
            total = len(lote)
            for c in lote:
                key = c.contractor_id or c.contractor
                fraction = counts[key] / total
                if fraction >= self.concentration_threshold:
                    hits.append(
                        RuleHit(
                            contract_id=c.id,
                            rule_id="OP-01",
                            weight=min(1.0, fraction),
                            rationale=(
                                f"En {entity!r} el proveedor representa "
                                f"{fraction:.0%} de los contratos del lote "
                                f"({counts[key]}/{total})."
                            ),
                        )
                    )
        return hits

    def _value_iqr_outlier(self, contracts: list[Contract]) -> list[RuleHit]:
        """Detecta valores fuera del IQR del lote (OP-02).

        Args:
            contracts: Lote de contratos a evaluar.

        Returns:
            RuleHits para cada contrato cuyo valor cae fuera del rango
            [Q1 - k*IQR, Q3 + k*IQR] del lote, con k = iqr_multiplier.
        """
        valores = [float(c.value) for c in contracts if c.value > 0]
        if len(valores) < 4:
            # WHY: cuartiles requieren al menos 4 puntos para ser estables.
            return []

        q1, q3 = _quantiles(valores)
        iqr = q3 - q1
        low = q1 - self.iqr_multiplier * iqr
        high = q3 + self.iqr_multiplier * iqr

        hits: list[RuleHit] = []
        for c in contracts:
            v = float(c.value)
            if c.value <= 0:
                continue
            if v < low or v > high:
                desviacion = (v - q3) / iqr if v > q3 else (q1 - v) / iqr
                hits.append(
                    RuleHit(
                        contract_id=c.id,
                        rule_id="OP-02",
                        weight=min(1.0, abs(desviacion) / 4.0),
                        rationale=(
                            f"Valor {v:,.0f} fuera de IQR del lote "
                            f"[{low:,.0f}, {high:,.0f}]; "
                            f"|desviacion|={abs(desviacion):.2f} IQR."
                        ),
                    )
                )
        return hits


    def _hhi_market_concentration(
        self, contracts: list[Contract]
    ) -> list[RuleHit]:
        """Detecta concentración de mercado por entity vía HHI (OP-13).

        El índice Herfindahl-Hirschman (Σ share²) se computa por entity
        usando el valor adjudicado como proxy de cuota. HHI ≥ 0.25 es
        umbral DOJ convencional para "alta concentración".
        """
        markets = hhi_concentration(
            contracts, threshold=self.hhi_threshold
        )
        hits: list[RuleHit] = []
        for entity, info in markets.items():
            if not info["threshold_exceeded"]:
                continue
            top = info["top_concentrators"][0]
            for c in contracts:
                if c.entity != entity or c.value <= 0:
                    continue
                hits.append(
                    RuleHit(
                        contract_id=c.id,
                        rule_id="OP-13",
                        weight=min(1.0, float(info["hhi"])),
                        rationale=(
                            f"Mercado de {entity!r}: HHI={info['hhi']:.2f} "
                            f"(umbral {self.hhi_threshold}). "
                            f"Concentrador líder {top['supplier']} con "
                            f"{top['share']:.0%} del valor adjudicado."
                        ),
                    )
                )
        return hits


def _quantiles(values: list[float]) -> tuple[float, float]:
    """Calcula Q1 y Q3 de una lista de valores.

    Args:
        values: Lista de números.

    Returns:
        Tupla (Q1, Q3).
    """
    qs = statistics.quantiles(values, n=4)
    return qs[0], qs[2]


def hhi_concentration(
    contracts: list[Contract],
    *,
    threshold: float = 0.25,
    min_lote: int = 3,
) -> dict[str, dict[str, Any]]:
    """Calcula el HHI de mercado por entity (OP-13).

    Args:
        contracts: Lote a evaluar.
        threshold: Umbral a partir del cual se marca alta concentración
            (default 0.25, convención DOJ — "highly concentrated").
        min_lote: Mínimo de contratos por entity para ser estadísticamente
            evaluable.

    Returns:
        Dict ``{entity: {hhi, top_concentrators, threshold_exceeded,
        total_value}}``. ``top_concentrators`` lista los 3 mayores
        proveedores por share.
    """
    by_entity: dict[str, list[Contract]] = defaultdict(list)
    for c in contracts:
        by_entity[c.entity].append(c)

    out: dict[str, dict[str, Any]] = {}
    for entity, lote in by_entity.items():
        if len(lote) < min_lote:
            continue
        total_value = sum(float(c.value) for c in lote if c.value > 0)
        if total_value <= 0:
            continue
        shares: dict[str, float] = defaultdict(float)
        for c in lote:
            if c.value <= 0:
                continue
            supplier = c.contractor_id or c.contractor
            shares[supplier] += float(c.value) / total_value
        hhi = sum(s * s for s in shares.values())
        top = sorted(shares.items(), key=lambda kv: -kv[1])[:3]
        out[entity] = {
            "hhi": hhi,
            "top_concentrators": [
                {"supplier": sup, "share": share} for sup, share in top
            ],
            "threshold_exceeded": hhi >= threshold,
            "total_value": total_value,
        }
    return out


def temporal_anomaly(
    contract: Contract,
    peers: list[Contract],
    *,
    fast_response_days: int = 10,
    duration_sigma: float = 2.0,
    min_peers: int = 4,
) -> dict[str, Any]:
    """Detecta anomalías temporales contra un cohort de peers (OP-03/05).

    Args:
        contract: Contrato a evaluar.
        peers: Cohort comparable (e.g. mismo CPV o modalidad). El motor
            no infiere el cohort: lo arma el llamador.
        fast_response_days: Plazo de respuesta (días entre firma y
            inicio) por debajo del cual se levanta ``fast_response_flag``.
        duration_sigma: Múltiplo de σ del cohort fuera del cual se marca
            ``duration_outlier_flag``.
        min_peers: Mínimo de peers con plazo conocido para que el outlier
            de duración sea estadísticamente válido.

    Returns:
        Dict con ``fast_response_flag``, ``duration_outlier_flag``,
        ``days_observed`` (plazo del contrato evaluado), ``peer_count``
        (peers con duración computable) y ``peer_mean_days``.
    """
    days_observed: int | None = None
    if contract.start_date and contract.end_date:
        days_observed = (contract.end_date - contract.start_date).days

    fast_response_flag = (
        contract.signed_date is not None
        and contract.start_date is not None
        and (contract.start_date - contract.signed_date).days
        < fast_response_days
    )

    peer_durations: list[int] = []
    for p in peers:
        if p.start_date and p.end_date:
            peer_durations.append((p.end_date - p.start_date).days)

    duration_outlier_flag = False
    peer_mean: float | None = None
    if days_observed is not None and len(peer_durations) >= min_peers:
        peer_mean = statistics.mean(peer_durations)
        peer_std = statistics.pstdev(peer_durations) or 1.0
        if abs(days_observed - peer_mean) > duration_sigma * peer_std:
            duration_outlier_flag = True

    return {
        "fast_response_flag": fast_response_flag,
        "duration_outlier_flag": duration_outlier_flag,
        "days_observed": days_observed,
        "peer_count": len(peer_durations),
        "peer_mean_days": peer_mean,
    }


def modification_excess(
    history: dict[str, Any],
    *,
    pct_threshold: float = 0.5,
    count_threshold: int = 2,
) -> dict[str, Any]:
    """Cuantifica adiciones contractuales (OP-06; Art. 40 parágrafo Ley 80).

    Args:
        history: Dict con dos claves obligatorias:
            - ``initial_value``: valor inicial del contrato (numérico).
            - ``additions``: lista de adiciones individuales (numéricas).
        pct_threshold: Fracción del valor inicial que dispara
            ``exceeds_50pct``. Default 0.5 (Art. 40 parágrafo Ley 80
            de 1993: las adiciones no pueden superar el 50% del valor
            inicial expresado en SMMLV).
        count_threshold: Conteo a partir del cual se marca
            ``exceeds_count_threshold``.

    Returns:
        Dict con ``addition_pct``, ``addition_count``,
        ``addition_total``, ``initial_value``, ``exceeds_50pct``,
        ``exceeds_count_threshold``.
    """
    initial = float(history.get("initial_value", 0) or 0)
    raw_adds = history.get("additions") or []
    adds = [float(x) for x in raw_adds if x is not None]
    addition_count = len(adds)
    addition_total = sum(adds)
    addition_pct = addition_total / initial if initial > 0 else 0.0
    return {
        "initial_value": initial,
        "addition_total": addition_total,
        "addition_count": addition_count,
        "addition_pct": addition_pct,
        "exceeds_50pct": addition_pct > pct_threshold,
        "exceeds_count_threshold": addition_count > count_threshold,
    }
