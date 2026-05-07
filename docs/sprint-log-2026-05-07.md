# Sprint log — 2026-05-07 (overnight pre-hackathon)

> Sesión overnight de cierre antes del Hackathon Nacional Colombia 5.0
> (8-9 may 2026, Corferias). Ventana cerrada antes de que el jurado
> revise el repo público (0 vistas en GitHub al inicio).

## Tag de release

`v0.2-combate` apunta al último commit de la sesión. La rama `main`
queda lista para que el jurado audite.

## Commits (9 atómicos)

| SHA      | Tipo  | Resumen                                                                |
|----------|-------|------------------------------------------------------------------------|
| 96e9ff7  | fix   | `urlproceso.url` del payload Socrata (cierra TODO[ALTA] sprint previo) |
| 8022aab  | docs  | ADR-007 (combinación lineal), 008 (`/contest`), 009 (Streamlit)        |
| a10355c  | feat  | FastAPI + `POST/GET /contest` (Pack 4 Responsiveness)                  |
| 7a58d08  | feat  | `SecopClient` real con cache 24h, retry exp, retry-after, paginación   |
| d260b17  | feat  | OP-13 HHI + funciones puras `temporal_anomaly` y `modification_excess` |
| 828cef5  | feat  | `llm_router.route` con fallback Anthropic→Ollama, ADR-007 lineal       |
| 0702c96  | docs  | 3 ejemplos end-to-end con citas legales (Decreto 1082, Ley 80, 1150)   |
| e9da32a  | feat  | `BaseAdapter`, `SecopAdapter`, `GenericSocrataAdapter` (reto sorpresa) |
| dd3d179  | feat  | `streamlit_app.py` dashboard con tabs Analizar / Modelo / Impugnar     |

## Hecho — completitud por tarea

| Tarea original           | Estado | Nota                                                  |
|--------------------------|--------|-------------------------------------------------------|
| 1 — Setup + cleanup      | 100%   | Ollama vacío y URL validada como hallazgo.            |
| 5 — `/contest`           | 100%   | API + SQLite + tests + smoke vía uvicorn verificados. |
| 1 — `secop_client`       | 95%    | Falta `bulk_snapshot` con parquet (cae a JSONL).      |
| 2 — Reglas               | 90%    | OP-13 integrada al RuleEngine; temporal y modif puras |
|                          |        | sin auto-invocación desde `evaluate`.                 |
| 3 — `llm_router`         | 100%   | Anthropic+Ollama+OFFLINE_MODE+RouterError, 10 tests.  |
| 4 — Ejemplos             | 100%   | 3 archivos `.md` con curl + output + cita legal.      |
| 6 — Adapter genérico     | 100%   | `field_mapping` requeridos: id/buyer_name/supplier.   |
| 7 — Streamlit            | 95%    | Tres tabs OK. No tiene gauge plotly; usa `st.metric`. |

## Pendiente

### TODO[ALTA]

1. **Instalar `qwen3:8b` en Ollama.** `ollama list` devolvió vacío en
   esta sesión. El fallback no se puede probar sin él. Verificar
   `OLLAMA_MODELS` apuntando a `/mnt/data/LLLMs/models` o ejecutar
   `ollama pull qwen3:8b`.
2. **CONSTITUTION vs llm_router default.** CONSTITUTION declara
   `claude-opus-4-7` como modelo principal; `llm_router` ahora usa
   `claude-haiku-4-5-20251001` por costo. Reconciliar — abrir ADR-010
   ("haiku para análisis masivo, opus para razonamiento jurídico").

### TODO[MEDIA]

3. **OP-14 oferente único.** Función pura no implementada;
   `docs/examples/example_02_oferente_unico.md` la describe
   conceptualmente. Páez la formaliza post-hackathon.
4. **RuleEngine no auto-invoca temporal/modificación.** Las funciones
   puras existen (`temporal_anomaly`, `modification_excess`) pero
   `RuleEngine.evaluate` no las llama porque requieren peers/historia.
   Diseñar handle: `RuleEngine.evaluate_with_context(contracts, peers_by_cpv, history_by_id)`.
5. **`bulk_snapshot` parquet.** Hoy escribe JSONL. Agregar rama
   parquet con `pyarrow` cuando esté instalado, JSONL fallback.
6. **Pricing Anthropic hardcodeado.** Si cambia el pricing de
   `claude-haiku-4-5-20251001` (1.0 / 5.0 USD por 1M tokens) hay que
   actualizar `src/detection/llm_router.py:ANTHROPIC_PRICING`.

### TODO[BAJA]

7. **Fixture sintético T-10** del sprint previo sigue abierto. Útil
   para CI sin red.
8. **ADR-005 embeddings y ADR-006 calendario feriados** previstos en
   sprint-log-2026-05-04 siguen pendientes.

## Smoke test — comandos para mañana 8-may

```bash
cd /home/thinkpad/projects/gobia-auditor
source .venv/bin/activate

# 1. Verificar deps y Ollama
ollama list                                              # qwen3:8b TODO
ruff check . && pytest -q                                # 41 verde

# 2. Levantar servicios (opcional Qdrant)
docker compose up -d qdrant
uvicorn src.api.main:app --port 8000 --reload &
streamlit run streamlit_app.py --server.port 8501 &

# 3. Smoke API
curl localhost:8000/healthz                              # {"status":"ok"}
curl -X POST localhost:8000/contest \
  -H 'Content-Type: application/json' \
  -d '{"contract_id":"CO1.PCCNTR.SMOKE",
       "reason":"smoke test desde paso 9 del overnight",
       "contestant_email":"smoke@test.org",
       "contestant_role":"veedor"}'

# 4. Abrir dashboard
xdg-open http://localhost:8501
```

## Hallazgos / sorpresas técnicas

- **URL canónica resuelta.** El dataset `jbjy-vk9h` ya expone
  `urlproceso.url` apuntando a
  `community.secop.gov.co/.../OpportunityDetail/Index?noticeUID=...`
  (NO `ContractDetailView/Index?contractId=`, que era la convención
  asumida antes). Cierra el TODO[ALTA] previo y mejora la
  defendibilidad de cada hallazgo (cita validada).
- **Ollama partió vacío.** `ollama list` devolvió 0 modelos pese a la
  partición DATA. El fallback queda parcialmente roto hasta el pull.
- **HHI ≠ top-share.** Una entidad puede tener top-share=40% pero HHI
  bajo si los otros 60% se reparten parejo. Mantener OP-01 y OP-13
  separadas resultó la decisión correcta (ahora hay tests que
  documentan ambos casos: 4-paritario marca HHI=0.25, 5-paritario
  marca HHI=0.20).
- **Pivote frontend documentado en gobierno.** ADR-008 + ADR-009 +
  edición de `AGENTS.md` evitaron que el repo tenga dashboard sin
  cobertura formal de la decisión arquitectónica.
- **`pytest-httpx` strict mode.** Mocks no usados levantan assert al
  cierre. Bug del adapter genérico se evidenció con cache vieja
  sirviendo respuestas y dejando el mock huérfano. Solución: inyectar
  `SecopClient` con cache aislada por test.
- **Streamlit + asyncio.run.** Funciona porque cada interacción
  corre el script desde cero sin loop preexistente. Si en el futuro
  se mete `streamlit-async` u otro layer, revisar `_run_route` en
  `llm_router.py`.

## Próxima sesión (post D1 / antes del pitch D2)

- Resolver TODO[ALTA] 1 (Ollama qwen3) antes de Día 1 8 mayo.
- Si reto sorpresa trae dataset distinto: Páez define `field_mapping`,
  `GenericSocrataAdapter` lo alimenta al `RuleEngine` sin más cambios.
- Preparar 3 capturas del Streamlit con caso real para slides D2.
