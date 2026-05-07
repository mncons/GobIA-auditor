"""FastAPI app raíz: healthz + montaje de routers (ADR-008)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.contest import router as contest_router
from src.storage.contest_store import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(
    title="GobIA Auditor",
    description=(
        "Motor de auditoría sobre SECOP II. Endpoint /contest implementa "
        "Pack 4 Responsiveness del 6-Pack of Care (ADR-008). Ningún UI "
        "modifica score; humano revisa toda impugnación en ≤7 días "
        "hábiles (CONSTITUTION §10)."
    ),
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


app.include_router(contest_router)
