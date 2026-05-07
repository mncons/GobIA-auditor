"""Normalizador: dict crudo de SECOP -> objeto Contract validado."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class Contract(BaseModel):
    """Representación canónica de un contrato SECOP II.

    Attributes:
        id: Identificador único del contrato en SECOP.
        entity: Nombre de la entidad estatal contratante.
        contractor: Razón social del proveedor adjudicado.
        contractor_id: NIT del proveedor (público).
        value: Valor del contrato en pesos colombianos.
        signed_date: Fecha de firma del contrato.
        start_date: Fecha de inicio de ejecución.
        end_date: Fecha de fin de ejecución.
        modality: Modalidad de contratación (licitación, mínima cuantía, etc.).
        sector: Sector administrativo o rama de la entidad.
        source_url: URL pública del contrato en community.secop.gov.co.
    """

    id: str
    entity: str
    contractor: str
    contractor_id: str | None = None
    value: Decimal = Field(default=Decimal("0"))
    signed_date: date | None = None
    start_date: date | None = None
    end_date: date | None = None
    modality: str = "no_definida"
    sector: str = "no_definido"
    source_url: str = ""


def normalize(raw: dict) -> Contract:
    """Convierte un registro Socrata crudo en Contract validado.

    Args:
        raw: Dict tal como llega desde la API Socrata de datos.gov.co.

    Returns:
        Instancia de Contract con campos canónicos.

    Notes:
        Mapeo de campos basado en los nombres comunes del dataset
        jbjy-vk9h. Campos faltantes en la fuente quedan en su default.
    """
    return Contract(
        id=str(raw.get("id_contrato") or raw.get("referencia_contrato") or ""),
        entity=str(raw.get("nombre_entidad") or ""),
        contractor=str(raw.get("proveedor_adjudicado") or ""),
        contractor_id=raw.get("nit_del_proveedor_adjudicado"),
        value=Decimal(str(raw.get("valor_del_contrato") or "0")),
        signed_date=_parse_date(raw.get("fecha_de_firma")),
        start_date=_parse_date(raw.get("fecha_de_inicio_del_contrato")),
        end_date=_parse_date(raw.get("fecha_de_fin_del_contrato")),
        modality=str(raw.get("modalidad_de_contratacion") or "no_definida"),
        sector=str(raw.get("rama") or raw.get("entidad_rama") or "no_definido"),
        source_url=_build_source_url(raw),
    )


def _parse_date(value: str | None) -> date | None:
    """Parsea una fecha ISO devuelta por Socrata.

    Args:
        value: Fecha en formato ISO o None.

    Returns:
        Objeto date, o None si el valor es vacío o inválido.
    """
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _build_source_url(raw: dict) -> str:
    """Construye la URL pública del contrato.

    Args:
        raw: Dict crudo de Socrata.

    Returns:
        URL en community.secop.gov.co o cadena vacía si no es derivable.

    Notes:
        Estrategia validada el 2026-05-07 contra `jbjy-vk9h`:
        el dataset Socrata YA expone la URL canónica del expediente
        en `raw["urlproceso"]["url"]` apuntando a
        `community.secop.gov.co/Public/Tendering/OpportunityDetail/Index?noticeUID=...`.
        Se prefiere ese valor. Si falta, se construye desde
        `proceso_de_compra` como aproximación; si tampoco existe se
        retorna cadena vacía y el llamador filtra el contrato
        (CONSTITUTION §10: cero hallazgos sin URL fuente).
    """
    urlproceso = raw.get("urlproceso")
    if isinstance(urlproceso, dict):
        url = urlproceso.get("url")
        if isinstance(url, str) and url.startswith("https://community.secop.gov.co/"):
            return url
    proceso = raw.get("proceso_de_compra")
    if proceso:
        return (
            "https://community.secop.gov.co/Public/Tendering/"
            f"OpportunityDetail/Index?noticeUID={proceso}"
        )
    return ""
