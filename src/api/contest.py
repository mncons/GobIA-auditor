"""Endpoint /contest: impugnación de hallazgos (ADR-008).

Implementa Pack 4 Responsiveness del 6-Pack of Care (Tang & Green,
Oxford 2025). El endpoint recibe la impugnación, deja constancia en
SQLite y responde con un acuse explícito de revisión humana. Bajo
ninguna circunstancia modifica el score automáticamente.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.storage.contest_store import (
    ContestRecord,
    create_contest,
    get_contest,
    list_by_contract,
)

router = APIRouter(prefix="/contest", tags=["contest"])

ContestantRole = Literal["citizen", "contractor", "entity", "veedor"]

ACK_TEXT = (
    "Recibimos tu impugnación. Este sistema NO decide; un humano la "
    "revisa en máximo 7 días hábiles. Te notificaremos al correo "
    "provisto. CONSTITUTION §10 — revisión humana obligatoria."
)


class ContestCreate(BaseModel):
    """Payload aceptado por POST /contest."""

    contract_id: str = Field(..., min_length=1, max_length=200)
    reason: str = Field(..., min_length=10, max_length=2000)
    contestant_email: str | None = Field(default=None, max_length=200)
    contestant_role: ContestantRole


class ContestCreateResponse(BaseModel):
    """Acuse de recibo del POST /contest."""

    contest_id: int
    status: str
    review_eta_days: int
    acknowledgment_text: str


@router.post("", response_model=ContestCreateResponse, status_code=201)
def post_contest(payload: ContestCreate) -> ContestCreateResponse:
    """Registra una impugnación; NO modifica score (ADR-008)."""
    record = create_contest(
        contract_id=payload.contract_id,
        reason=payload.reason,
        email=payload.contestant_email or "",
        role=payload.contestant_role,
    )
    return ContestCreateResponse(
        contest_id=record.id,
        status=record.status,
        review_eta_days=7,
        acknowledgment_text=ACK_TEXT,
    )


@router.get("/{contest_id}", response_model=ContestRecord)
def get_contest_route(contest_id: int) -> ContestRecord:
    """Recupera una impugnación por id."""
    record = get_contest(contest_id)
    if record is None:
        raise HTTPException(status_code=404, detail="contest not found")
    return record


@router.get("", response_model=list[ContestRecord])
def list_contests(
    contract_id: str = Query(..., min_length=1, max_length=200),
) -> list[ContestRecord]:
    """Lista impugnaciones de un contrato en orden de creación."""
    return list_by_contract(contract_id)
