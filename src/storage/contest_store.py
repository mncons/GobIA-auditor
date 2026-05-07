"""SQLite store para impugnaciones (ADR-008).

La tabla ``contests`` retiene cada impugnación en estado ``received``
hasta que un revisor humano (Marlon o Gustavo) la mueve a
``under_review`` y luego a ``resolved_kept`` o ``resolved_changed``
con notas de resolución. Retención por defecto: 90 días.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel

DB_PATH = Path("data/contests.db")

DDL = """
CREATE TABLE IF NOT EXISTS contests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    email TEXT NOT NULL,
    role TEXT NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'received',
    resolution_notes TEXT,
    reviewed_at TEXT,
    reviewer_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_contract_id ON contests(contract_id);
"""


class ContestRecord(BaseModel):
    """Registro de impugnación tal como se persiste en SQLite."""

    id: int
    contract_id: str
    reason: str
    email: str
    role: str
    created_at: str
    status: str
    resolution_notes: str | None = None
    reviewed_at: str | None = None
    reviewer_id: str | None = None


_db_path: Path = DB_PATH


def set_db_path(path: Path) -> None:
    """Reemplaza la ruta de la DB (usado por tests)."""
    global _db_path
    _db_path = path


def _connect() -> sqlite3.Connection:
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Crea tabla e índice si no existen (idempotente)."""
    with _connect() as conn:
        conn.executescript(DDL)
        conn.commit()


def create_contest(
    contract_id: str,
    reason: str,
    email: str,
    role: str,
) -> ContestRecord:
    """Inserta una impugnación nueva en estado 'received'."""
    init_db()
    now = datetime.now(UTC).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO contests (contract_id, reason, email, role, "
            "created_at, status) VALUES (?, ?, ?, ?, ?, 'received')",
            (contract_id, reason, email, role, now),
        )
        contest_id = cur.lastrowid
        conn.commit()
    if contest_id is None:
        raise RuntimeError("SQLite did not assign id on insert")
    return ContestRecord(
        id=contest_id,
        contract_id=contract_id,
        reason=reason,
        email=email,
        role=role,
        created_at=now,
        status="received",
    )


def get_contest(contest_id: int) -> ContestRecord | None:
    """Recupera una impugnación por id; None si no existe."""
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM contests WHERE id = ?", (contest_id,)
        ).fetchone()
    if row is None:
        return None
    return ContestRecord(**dict(row))


def list_by_contract(contract_id: str) -> list[ContestRecord]:
    """Lista impugnaciones de un contrato en orden de creación."""
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM contests WHERE contract_id = ? ORDER BY id",
            (contract_id,),
        ).fetchall()
    return [ContestRecord(**dict(r)) for r in rows]
