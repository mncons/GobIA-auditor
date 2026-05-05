"""CLI principal de GobIA Auditor.

Subcomandos:
    ingest   — descarga contratos de SECOP en un rango de fechas.
    analyze  — corre el detection engine sobre los contratos cargados.
    report   — genera el reporte Markdown final.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import date

from src.detection.llm_router import analyze_contract
from src.detection.rules import RuleEngine
from src.ingestion.normalizer import Contract, normalize
from src.ingestion.secop_client import SecopClient
from src.reporting.report import generate as generate_report


def _build_parser() -> argparse.ArgumentParser:
    """Construye el parser de CLI con sus tres subcomandos.

    Returns:
        ArgumentParser configurado.
    """
    parser = argparse.ArgumentParser(
        prog="gobia-auditor",
        description="Detección de opacidad en contratos SECOP II.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="Descarga contratos de SECOP II.")
    p_ingest.add_argument("--date-from", required=True, type=date.fromisoformat)
    p_ingest.add_argument("--date-to", required=True, type=date.fromisoformat)

    p_analyze = sub.add_parser(
        "analyze",
        help="Corre reglas + LLM sobre contratos cargados.",
    )
    p_analyze.add_argument(
        "--strategy",
        default="rules",
        choices=["rules", "rules+llm"],
        help="rules: solo determinístico; rules+llm: enriquecido.",
    )

    p_report = sub.add_parser("report", help="Genera reporte Markdown.")
    p_report.add_argument("--format", default="md", choices=["md"])
    p_report.add_argument("--out", default="-")

    return parser


async def _cmd_ingest(args: argparse.Namespace) -> int:
    """Ejecuta el subcomando `ingest`.

    Args:
        args: Argumentos parseados (date_from, date_to).

    Returns:
        Exit code POSIX (0 éxito).
    """
    client = SecopClient()
    raw = await client.get_contracts(args.date_from, args.date_to)
    contracts: list[Contract] = [normalize(r) for r in raw]
    print(f"[ingest] descargados {len(contracts)} contratos (stub).")
    return 0


def _cmd_analyze(args: argparse.Namespace) -> int:
    """Ejecuta el subcomando `analyze`.

    Args:
        args: Argumentos parseados (strategy).

    Returns:
        Exit code POSIX (0 éxito).
    """
    engine = RuleEngine()
    contracts: list[Contract] = []  # se cargará desde storage en sprint posterior
    hits = engine.evaluate(contracts)
    use_llm = args.strategy == "rules+llm"
    scores = [analyze_contract(c, [h for h in hits if h.contract_id == c.id], use_llm=use_llm) for c in contracts]
    print(f"[analyze] {len(scores)} scores generados (estrategia={args.strategy}).")
    return 0


def _cmd_report(args: argparse.Namespace) -> int:
    """Ejecuta el subcomando `report`.

    Args:
        args: Argumentos parseados (format, out).

    Returns:
        Exit code POSIX (0 éxito).
    """
    text = generate_report(scores=[])
    if args.out == "-":
        print(text)
    else:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"[report] reporte escrito en {args.out}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada de la CLI.

    Args:
        argv: Lista de argumentos; si None, usa sys.argv.

    Returns:
        Exit code POSIX.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "ingest":
        return asyncio.run(_cmd_ingest(args))
    if args.command == "analyze":
        return _cmd_analyze(args)
    if args.command == "report":
        return _cmd_report(args)
    parser.error(f"comando desconocido: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
