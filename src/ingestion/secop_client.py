"""Cliente HTTP para el endpoint público de SECOP II.

La fuente única de verdad es el dataset Socrata `jbjy-vk9h` en
`datos.gov.co`. La auditabilidad de los hallazgos depende de mantener
la fuente fija y citable (CONSTITUTION §10).

El cliente expone:
- ``get_contracts(date_from, date_to, limit)`` — firma estable usada
  por la CLI desde el sprint anterior.
- ``fetch_contract(contract_id)`` — un solo contrato.
- ``search_contracts(filters, limit)`` — iterador paginado.
- ``bulk_snapshot(query, output_path, max_rows)`` — JSONL en disco.

Implementa cache SQLite con TTL 24h (``data/secop_cache.db``) y
retry manual con respeto a ``Retry-After`` en 429.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import sqlite3
import time
from collections.abc import AsyncIterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from src.config import get_settings

CACHE_DB = Path("data/secop_cache.db")
CACHE_TTL_HOURS = 24
MAX_ATTEMPTS = 3

logger = logging.getLogger(__name__)


class SecopHTTPError(Exception):
    """Error no recuperable del cliente SECOP."""


def _cache_key(url: str, params: dict[str, Any] | None) -> str:
    payload = url + json.dumps(params or {}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


class SecopCache:
    """Cache SQLite con TTL para respuestas Socrata."""

    DDL = """
    CREATE TABLE IF NOT EXISTS cache (
        key TEXT PRIMARY KEY,
        body TEXT NOT NULL,
        fetched_at TEXT NOT NULL
    );
    """

    def __init__(
        self,
        path: Path = CACHE_DB,
        ttl_hours: int = CACHE_TTL_HOURS,
    ) -> None:
        self.path = path
        self.ttl = timedelta(hours=ttl_hours)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(self.DDL)
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def get(self, key: str) -> Any | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT body, fetched_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        fetched_at = datetime.fromisoformat(row["fetched_at"])
        if datetime.now(UTC) - fetched_at > self.ttl:
            return None
        return json.loads(row["body"])

    def set(self, key: str, body: Any) -> None:
        now = datetime.now(UTC).isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, body, fetched_at) "
                "VALUES (?, ?, ?)",
                (key, json.dumps(body, default=str), now),
            )
            conn.commit()


class SecopClient:
    """Cliente Socrata para SECOP II (jbjy-vk9h).

    Uso recomendado dentro de ``async with`` para reusar la conexión
    HTTP. Si se llama un método sin context manager el cliente abre y
    cierra ``httpx.AsyncClient`` ad-hoc por llamada.
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: float = 30.0,
        cache: SecopCache | None = None,
        app_token: str | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = base_url or settings.secop_api_base
        self.timeout = timeout
        self.cache = cache if cache is not None else SecopCache()
        self.app_token = app_token
        self._ctx_client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> SecopClient:
        self._ctx_client = httpx.AsyncClient(
            timeout=self.timeout, headers=self._headers()
        )
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._ctx_client is not None:
            await self._ctx_client.aclose()
            self._ctx_client = None

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self.app_token:
            h["X-App-Token"] = self.app_token
        return h

    async def _get(
        self, url: str, params: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """GET con cache + retry; devuelve lista de items."""
        key = _cache_key(url, params)
        cached = self.cache.get(key)
        if cached is not None:
            self._log(url, status=200, latency_ms=0.0, cache="hit", retries=0)
            return cached

        if self._ctx_client is not None:
            return await self._do_get(self._ctx_client, url, params, key)
        async with httpx.AsyncClient(
            timeout=self.timeout, headers=self._headers()
        ) as client:
            return await self._do_get(client, url, params, key)

    async def _do_get(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict[str, Any],
        key: str,
    ) -> list[dict[str, Any]]:
        start = time.monotonic()
        retries = 0
        last_status: int | None = None
        last_body: str | None = None

        for attempt in range(MAX_ATTEMPTS):
            try:
                resp = await client.get(url, params=params)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                retries += 1
                last_body = str(e)
                if attempt < MAX_ATTEMPTS - 1:
                    await asyncio.sleep(min(2**attempt, 10))
                    continue
                raise SecopHTTPError(f"transport: {e}") from e

            last_status = resp.status_code

            if resp.status_code == 429:
                retries += 1
                retry_after = float(resp.headers.get("retry-after", "1"))
                if attempt < MAX_ATTEMPTS - 1:
                    await asyncio.sleep(retry_after)
                    continue
                raise SecopHTTPError("rate-limit (429) tras 3 intentos")

            if 500 <= resp.status_code < 600:
                retries += 1
                last_body = resp.text[:200]
                if attempt < MAX_ATTEMPTS - 1:
                    await asyncio.sleep(min(2**attempt, 10))
                    continue
                raise SecopHTTPError(
                    f"5xx tras 3 intentos: {resp.status_code} {last_body}"
                )

            if resp.status_code >= 400:
                raise SecopHTTPError(
                    f"{resp.status_code}: {resp.text[:200]}"
                )

            try:
                body = resp.json()
            except ValueError as e:
                raise SecopHTTPError(f"JSON inválido: {e}") from e
            if not isinstance(body, list):
                raise SecopHTTPError(
                    f"Respuesta no es lista: {type(body).__name__}"
                )
            latency_ms = (time.monotonic() - start) * 1000
            self.cache.set(key, body)
            self._log(
                url,
                status=resp.status_code,
                latency_ms=latency_ms,
                cache="miss",
                retries=retries,
            )
            return body

        raise SecopHTTPError(
            f"agotado tras {MAX_ATTEMPTS} intentos (last_status={last_status})"
        )

    def _log(self, url: str, **fields: Any) -> None:
        record = {"event": "secop_request", "url": url, **fields}
        logger.info(json.dumps(record, default=str))

    async def get_contracts(
        self,
        date_from: date,
        date_to: date,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """Obtiene contratos firmados entre ``date_from`` y ``date_to``."""
        params: dict[str, Any] = {
            "$where": f"fecha_de_firma between '{date_from}' and '{date_to}'",
            "$limit": str(limit),
        }
        return await self._get(self.base_url, params)

    async def fetch_contract(
        self, contract_id: str
    ) -> dict[str, Any] | None:
        """Devuelve el contrato con ``id_contrato == contract_id`` o None."""
        params = {"id_contrato": contract_id, "$limit": "1"}
        items = await self._get(self.base_url, params)
        return items[0] if items else None

    async def search_contracts(
        self,
        filters: dict[str, Any],
        limit: int = 1000,
        page_size: int = 1000,
    ) -> AsyncIterator[dict[str, Any]]:
        """Itera contratos paginando con ``$offset``.

        Args:
            filters: Cláusulas Socrata adicionales (``$where``, etc.).
            limit: Tope total de items que se yieldan.
            page_size: Tamaño de cada página HTTP (Socrata permite 1000).
        """
        page_size = max(1, min(page_size, 1000))
        offset = 0
        own_ctx = self._ctx_client is None
        if own_ctx:
            await self.__aenter__()
        try:
            yielded = 0
            while yielded < limit:
                params = dict(filters)
                params["$limit"] = str(min(page_size, limit - yielded))
                params["$offset"] = str(offset)
                items = await self._get(self.base_url, params)
                if not items:
                    return
                for item in items:
                    yield item
                    yielded += 1
                    if yielded >= limit:
                        return
                if len(items) < page_size:
                    return
                offset += page_size
        finally:
            if own_ctx:
                await self.__aexit__(None, None, None)

    async def bulk_snapshot(
        self,
        query: dict[str, Any],
        output_path: Path,
        max_rows: int = 100_000,
    ) -> int:
        """Vuelca ``query`` a JSONL en ``output_path``; devuelve # filas."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        rows = 0
        with output_path.open("w") as f:
            async for item in self.search_contracts(query, limit=max_rows):
                f.write(json.dumps(item, default=str) + "\n")
                rows += 1
        return rows
