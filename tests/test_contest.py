"""Tests del endpoint /contest (ADR-008)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.storage import contest_store


@pytest.fixture(autouse=True)
def temp_db(tmp_path: Path):
    """Aísla la DB SQLite por test usando tmp_path."""
    original = contest_store._db_path
    contest_store.set_db_path(tmp_path / "test_contests.db")
    contest_store.init_db()
    yield
    contest_store.set_db_path(original)


@pytest.fixture
def client():
    return TestClient(app)


def test_post_contest_valido(client) -> None:
    payload = {
        "contract_id": "CO1.PCCNTR.123456",
        "reason": "El score parece inflado por un outlier sectorial sin contexto suficiente.",
        "contestant_email": "vee@dor.org",
        "contestant_role": "veedor",
    }
    resp = client.post("/contest", json=payload)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "received"
    assert body["review_eta_days"] == 7
    assert body["contest_id"] >= 1
    assert "humano" in body["acknowledgment_text"].lower()


def test_post_contest_payload_invalido_devuelve_422(client) -> None:
    resp = client.post(
        "/contest",
        json={
            "contract_id": "CO1.PCCNTR.X",
            "reason": "corto",
            "contestant_role": "citizen",
        },
    )
    assert resp.status_code == 422


def test_get_contest_por_id_existente_y_no_existente(client) -> None:
    payload = {
        "contract_id": "CO1.PCCNTR.AAAA",
        "reason": "El plazo de adjudicación es inusualmente corto.",
        "contestant_email": "",
        "contestant_role": "citizen",
    }
    created = client.post("/contest", json=payload).json()
    contest_id = created["contest_id"]

    found = client.get(f"/contest/{contest_id}")
    assert found.status_code == 200
    assert found.json()["contract_id"] == "CO1.PCCNTR.AAAA"

    miss = client.get("/contest/999999")
    assert miss.status_code == 404


def test_list_contests_por_contract_id(client) -> None:
    cid = "CO1.PCCNTR.LIST"
    for reason in [
        "Razon una documentada con detalle suficiente.",
        "Razon dos documentada con detalle suficiente.",
    ]:
        client.post(
            "/contest",
            json={
                "contract_id": cid,
                "reason": reason,
                "contestant_role": "veedor",
            },
        )
    resp = client.get(f"/contest?contract_id={cid}")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 2
    assert all(r["contract_id"] == cid for r in body)


def test_healthz(client) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
