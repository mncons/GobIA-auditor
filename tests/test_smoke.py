"""Tests de humo.

Sólo verifican que el scaffold importa y que los schemas básicos son
coherentes. No realizan llamadas a SECOP, Anthropic, Ollama o Qdrant.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal


def test_imports_basicos() -> None:
    """Verifica que los módulos del paquete cargan sin efectos colaterales."""
    import src  # noqa: F401
    import src.api.contest  # noqa: F401
    import src.api.main  # noqa: F401
    import src.config  # noqa: F401
    import src.detection.llm_router  # noqa: F401
    import src.detection.rules  # noqa: F401
    import src.ingestion.normalizer  # noqa: F401
    import src.ingestion.secop_client  # noqa: F401
    import src.main  # noqa: F401
    import src.reporting.report  # noqa: F401
    import src.storage.contest_store  # noqa: F401
    import src.storage.qdrant_store  # noqa: F401


def test_contract_schema_valido() -> None:
    """Construye un Contract con los campos mínimos y valida defaults."""
    from src.ingestion.normalizer import Contract

    c = Contract(
        id="CO-X-123",
        entity="Alcaldía Demo",
        contractor="Proveedor Demo SAS",
        contractor_id="900000000",
        value=Decimal("1500000"),
        signed_date=date(2026, 1, 15),
        modality="minima_cuantia",
        sector="ejecutiva",
    )
    assert c.id == "CO-X-123"
    assert c.value == Decimal("1500000")
    assert c.start_date is None  # default razonable


def test_rule_engine_detecta_concentracion() -> None:
    """RuleEngine activa OP-01 cuando un proveedor concentra el lote."""
    from src.detection.rules import RuleEngine
    from src.ingestion.normalizer import Contract

    contratos = [
        Contract(id=f"C{i}", entity="E1", contractor="P", contractor_id="900",
                 value=Decimal("1000000"))
        for i in range(4)
    ]
    contratos.append(
        Contract(id="C-otro", entity="E1", contractor="Otro",
                 contractor_id="901", value=Decimal("1000000"))
    )

    hits = RuleEngine().evaluate(contratos)
    rule_ids = {h.rule_id for h in hits}
    assert "OP-01" in rule_ids


def test_cli_parser_carga() -> None:
    """El parser de la CLI reconoce los tres subcomandos."""
    from src.main import _build_parser

    parser = _build_parser()
    ns = parser.parse_args(
        ["ingest", "--date-from", "2026-01-01", "--date-to", "2026-01-31"]
    )
    assert ns.command == "ingest"
    assert ns.date_from == date(2026, 1, 1)
