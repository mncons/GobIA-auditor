"""Tests para reglas estadísticas: HHI (OP-13), temporal, modificación."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.detection.rules import (
    RuleEngine,
    hhi_concentration,
    modification_excess,
    temporal_anomaly,
)
from src.ingestion.normalizer import Contract


def _c(
    cid: str,
    entity: str,
    contractor_id: str,
    value: int,
    *,
    signed: date | None = None,
    start: date | None = None,
    end: date | None = None,
    modality: str = "minima_cuantia",
) -> Contract:
    return Contract(
        id=cid,
        entity=entity,
        contractor=f"P-{contractor_id}",
        contractor_id=contractor_id,
        value=Decimal(value),
        signed_date=signed,
        start_date=start,
        end_date=end,
        modality=modality,
    )


# ---------------------------------------------------------------------------
# OP-13 HHI
# ---------------------------------------------------------------------------


def test_hhi_detecta_mercado_concentrado() -> None:
    """Un proveedor con 80% del valor → HHI alto, threshold_exceeded=True."""
    contracts = [
        _c("c1", "EntA", "900", 8000),
        _c("c2", "EntA", "900", 8000),
        _c("c3", "EntA", "901", 1000),
        _c("c4", "EntA", "902", 1000),
    ]
    res = hhi_concentration(contracts, threshold=0.25)
    assert "EntA" in res
    info = res["EntA"]
    # 16k / 18k ≈ 0.889 share del primero → HHI ≈ 0.79
    assert info["hhi"] > 0.5
    assert info["threshold_exceeded"] is True
    assert info["top_concentrators"][0]["supplier"] == "900"


def test_hhi_no_detecta_mercado_diverso() -> None:
    """4 proveedores con shares parejos → HHI bajo, no excede threshold."""
    contracts = [
        _c("c1", "EntB", "910", 1000),
        _c("c2", "EntB", "911", 1000),
        _c("c3", "EntB", "912", 1000),
        _c("c4", "EntB", "913", 1000),
    ]
    res = hhi_concentration(contracts, threshold=0.25)
    info = res["EntB"]
    # HHI = 4 × (0.25)^2 = 0.25 → exactamente en threshold; con 4 paritarios
    # el resultado es 0.25 → threshold_exceeded depende de >= ; nuestro
    # algoritmo usa ``>=`` por lo que ESTE caso paritario marca ``True``.
    # Para un caso "claramente diverso" usamos 5+ proveedores:
    contracts5 = [
        _c(f"c{i}", "EntC", f"92{i}", 1000) for i in range(5)
    ]
    res5 = hhi_concentration(contracts5, threshold=0.25)
    info5 = res5["EntC"]
    # HHI = 5 × (0.2)^2 = 0.20 < 0.25
    assert info5["threshold_exceeded"] is False
    # Sanity check del bucket paritario de 4
    assert info["threshold_exceeded"] is True


def test_hhi_descarta_lotes_pequenos_o_sin_valor() -> None:
    """Lotes con < 3 contratos o valor total 0 no aparecen en el resultado."""
    only_two = [
        _c("c1", "EntD", "930", 5000),
        _c("c2", "EntD", "930", 5000),
    ]
    assert hhi_concentration(only_two) == {}

    zero_value = [
        _c(f"c{i}", "EntE", "940", 0) for i in range(4)
    ]
    assert hhi_concentration(zero_value) == {}


def test_rule_engine_emite_op13_para_entity_concentrada() -> None:
    """RuleEngine.evaluate dispara OP-13 cuando hay HHI alto."""
    contracts = [
        _c("c1", "EntF", "950", 10000),
        _c("c2", "EntF", "950", 10000),
        _c("c3", "EntF", "950", 10000),
        _c("c4", "EntF", "951", 1000),
    ]
    hits = RuleEngine().evaluate(contracts)
    rule_ids = {h.rule_id for h in hits}
    assert "OP-13" in rule_ids


# ---------------------------------------------------------------------------
# Temporal (OP-03 / OP-05 expansión)
# ---------------------------------------------------------------------------


def test_temporal_anomaly_fast_response_dispara() -> None:
    """Plazo entre firma e inicio < 10 días hábiles → fast_response_flag=True."""
    c = _c(
        "c1",
        "EntG",
        "960",
        5000,
        signed=date(2026, 1, 10),
        start=date(2026, 1, 12),
        end=date(2026, 6, 30),
    )
    res = temporal_anomaly(c, peers=[])
    assert res["fast_response_flag"] is True
    assert res["days_observed"] is not None


def test_temporal_anomaly_duration_outlier_dispara() -> None:
    """Duración del contrato > 2σ del cohort → duration_outlier_flag=True."""
    peers = [
        _c(
            f"p{i}",
            "EntH",
            "961",
            1000,
            start=date(2026, 1, 1),
            end=date(2026, 2, 1),  # ~31 días
        )
        for i in range(6)
    ]
    target = _c(
        "target",
        "EntH",
        "962",
        1000,
        signed=date(2026, 1, 1),
        start=date(2026, 1, 1),
        end=date(2027, 1, 1),  # 365 días, claramente outlier vs ~31
    )
    res = temporal_anomaly(target, peers=peers)
    assert res["duration_outlier_flag"] is True
    assert res["peer_count"] == 6
    assert res["peer_mean_days"] is not None and res["peer_mean_days"] < 60


def test_temporal_anomaly_pocos_peers_no_evalua_duracion() -> None:
    """Con menos de min_peers (default 4) no marca duration_outlier."""
    target = _c(
        "t1",
        "EntI",
        "970",
        1000,
        signed=date(2026, 1, 1),
        start=date(2026, 1, 5),
        end=date(2026, 1, 30),
    )
    res = temporal_anomaly(target, peers=[])
    assert res["duration_outlier_flag"] is False
    assert res["peer_count"] == 0
    assert res["peer_mean_days"] is None


# ---------------------------------------------------------------------------
# Modificación (OP-06 cuantitativa, Art. 40 parágrafo Ley 80)
# ---------------------------------------------------------------------------


def test_modification_excess_supera_50_pct() -> None:
    """Adiciones que superan 50% del valor inicial → exceeds_50pct=True."""
    res = modification_excess(
        {"initial_value": 1_000_000, "additions": [600_000]}
    )
    assert res["addition_pct"] == 0.6
    assert res["exceeds_50pct"] is True
    assert res["addition_count"] == 1


def test_modification_excess_supera_count_no_pct() -> None:
    """Más de 2 adiciones pequeñas → exceeds_count, no exceeds_50pct."""
    res = modification_excess(
        {
            "initial_value": 10_000_000,
            "additions": [500_000, 400_000, 300_000],
        }
    )
    assert res["addition_count"] == 3
    assert res["exceeds_count_threshold"] is True
    assert res["exceeds_50pct"] is False


def test_modification_excess_initial_cero_no_explota() -> None:
    """initial_value=0 con adiciones → addition_pct=0, no diviende por cero."""
    res = modification_excess({"initial_value": 0, "additions": [100, 200]})
    assert res["addition_pct"] == 0.0
    assert res["exceeds_50pct"] is False
    assert res["addition_count"] == 2
