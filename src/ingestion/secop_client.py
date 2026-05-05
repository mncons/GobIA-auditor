"""Cliente HTTP para el endpoint público de SECOP II.

La fuente única de verdad es el dataset Socrata jbjy-vk9h en datos.gov.co.
No se debe consultar otro endpoint: la auditabilidad de los hallazgos
depende de mantener la fuente fija y citable.
"""

from __future__ import annotations

from datetime import date

import httpx

from src.config import get_settings


class SecopClient:
    """Cliente mínimo para SECOP II vía API Socrata.

    La integración real (paginación, manejo de tokens, retries) se
    implementa en sprints posteriores. Este cliente expone la firma
    estable que usará el resto del sistema.
    """

    def __init__(self, base_url: str | None = None, timeout: float = 30.0) -> None:
        """Inicializa el cliente.

        Args:
            base_url: Override del endpoint Socrata. Por defecto usa el
                valor de Settings.secop_api_base.
            timeout: Tiempo máximo en segundos por request HTTP.
        """
        settings = get_settings()
        self.base_url = base_url or settings.secop_api_base
        self.timeout = timeout

    async def get_contracts(
        self,
        date_from: date,
        date_to: date,
        limit: int = 1000,
    ) -> list[dict]:
        """Obtiene contratos firmados en un rango de fechas.

        Args:
            date_from: Fecha inicial (inclusive) de firma del contrato.
            date_to: Fecha final (inclusive) de firma del contrato.
            limit: Máximo de filas por página Socrata.

        Returns:
            Lista de dicts crudos tal como los devuelve Socrata. La
            normalización a Contract ocurre en normalizer.py.

        Notes:
            STUB. Esta implementación construye los parámetros pero no
            ejecuta la llamada todavía: se valida la firma del cliente
            sin gastar cuota de la API durante desarrollo. Ver
            docs/sprint-log-2026-05-04.md para el plan de integración.
        """
        params = {
            "$where": f"fecha_de_firma between '{date_from}' and '{date_to}'",
            "$limit": limit,
        }
        # WHY: el request real queda diferido. Mantener la firma async +
        # httpx asegura que el llamador ya pueda integrarse contra ella.
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            _ = client  # se usará al activar la integración real
            _ = params
            return []
