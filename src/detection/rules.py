"""Motor de reglas determinísticas para señales de opacidad.

Implementa dos reglas reales (no stubs) sobre las que el LLM Router
puede después añadir contexto cualitativo:

- OP-01 Concentración por proveedor dentro de una entidad.
- OP-02 Valor del contrato fuera del rango intercuartílico del lote.
"""

from __future__ import annotations

import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass

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


def _quantiles(values: list[float]) -> tuple[float, float]:
    """Calcula Q1 y Q3 de una lista de valores.

    Args:
        values: Lista de números.

    Returns:
        Tupla (Q1, Q3).
    """
    qs = statistics.quantiles(values, n=4)
    return qs[0], qs[2]


