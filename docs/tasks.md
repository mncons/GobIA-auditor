# tasks.md — GobIA Auditor

> Descomposición ejecutable del trabajo. Cada tarea es **atómica**
> (un commit), **verificable** (tiene Definition of Done específica)
> y **trazable** a un objetivo de `spec.md` o restricción de `plan.md`.
>
> Convenciones:
> - `[ ]` pendiente, `[x]` cerrada (anota commit hash).
> - `T-NN` id estable de la tarea.
> - **Owner** indicativo: el agente o persona responsable principal.

---

## Sprint 0 — Inscripción (cerrado el 2026-05-04 ~21:55)

- [x] **T-00** Scaffold inicial defendible — *commit `8af654e`*.
  - Owner: Marlon + Claude Code.
  - DoD: README, LICENSE, src/ skeleton, smoke tests verdes, ruff
    limpio, docker-compose, CI yaml.
- [x] **T-01** Documentación de gobierno — *commit `6aeb4c6`*.
  - Owner: Marlon.
  - DoD: AGENTS.md, CONSTITUTION.md, sprint-log, team.md.
- [x] **T-02** Artefactos spec-driven (este archivo y hermanos).
  - Owner: Marlon + Claude Code.
  - DoD: docs/spec.md, docs/plan.md, docs/tasks.md commiteados.

---

## Sprint 1 — Demo funcional sobre fixture sintético (overnight 2026-05-04 → 05-05)

### Bloque A — Datos sintéticos y fixtures

- [ ] **T-10** Generar fixture sintético `tests/fixtures/secop_sample.json`.
  - Owner: Jaime Páez (diseño) + Claude Code (generación).
  - Contiene 100–200 contratos con nombres ficticios.
  - Garantiza al menos 3 hits de OP-01 y 3 hits de OP-02.
  - DoD: `pytest tests/test_fixtures.py` verde validando shape.

- [ ] **T-11** Loader de fixture en CLI `analyze --from-fixture`.
  - Owner: Claude Code.
  - DoD: `python -m src.main analyze --strategy rules --from-fixture
    tests/fixtures/secop_sample.json` imprime conteo de hits.

### Bloque B — Reglas adicionales

- [ ] **T-20** Implementar OP-04 (adjudicación en feriado).
  - Owner: Jaime Páez.
  - Calendario hardcoded de feriados nacionales 2024–2026 (decisión
    en ADR-006 si se externaliza).
  - DoD: test que pasa fecha en feriado real y verifica OP-04 disparada.

- [ ] **T-21** Implementar OP-05 (último día hábil del mes).
  - Owner: Jaime Páez.
  - DoD: test sobre fechas conocidas (2026-01-30, 2026-02-27).

- [ ] **T-22** Implementar OP-11 (fragmentación bajo umbral de modalidad).
  - Owner: Jaime Páez + Gustavo (umbrales legales).
  - DoD: test sobre pares entidad-NIT cuyos valores agregados superan
    umbral mínima cuantía.

### Bloque C — Persistencia real

- [ ] **T-30** Conectar `QdrantStore.upsert` real con embeddings.
  - Owner: Jaime Cárdenas + Claude Code.
  - Bloqueado por ADR-005 (modelo de embeddings).
  - DoD: smoke test que arranca Qdrant en docker-compose y persiste 10
    contratos del fixture.

- [ ] **T-31** Esquema Postgres para `OpacityScore` con trazabilidad.
  - Owner: Jaime Cárdenas.
  - DoD: migración SQL en `migrations/0001_initial.sql`; test de roundtrip.

### Bloque D — Ingesta real (con fixture, no producción)

- [ ] **T-40** Activar request real en `SecopClient.get_contracts`.
  - Owner: Claude Code.
  - Paginación `$limit`/`$offset`, retry con backoff exponencial.
  - **No** se ejecuta contra producción durante CI; mockeado con
    httpx.MockTransport.
  - DoD: test con MockTransport que valida URL, params y manejo de
    errores 5xx.

### Bloque E — LLM Router real

- [ ] **T-50** Conectar Anthropic SDK en `LLMRouter` cuando `use_llm=True`.
  - Owner: Marlon.
  - Cache local de prompts/respuestas en sqlite para auditoría.
  - DoD: test con cliente mockeado; integración real verificada
    manualmente con `python -m src.main analyze --strategy rules+llm`.

- [ ] **T-51** Fallback Ollama qwen3.
  - Owner: Jaime Cárdenas.
  - Conmutación automática al detectar fallo de Anthropic.
  - DoD: test que simula fallo Anthropic y verifica que se invoca
    Ollama con el mismo prompt.

### Bloque F — Reporte y demo

- [ ] **T-60** Generar `reports/demo-2026-05-05.md` sobre el fixture.
  - Owner: Marlon.
  - Top 10 hallazgos, racionalización citable, todos con URL fuente.
  - DoD: revisión humana de Gustavo (sin atribuciones, sin nombres
    reales) y commit a la rama `develop`.

- [ ] **T-61** Script de demo `scripts/demo.sh` ejecutable end-to-end.
  - Owner: Jaime Cárdenas.
  - DoD: `bash scripts/demo.sh` produce el reporte en <2 min sobre
    laptop estándar sin red externa.

---

## Sprint 2 — Endurecimiento previo a presentación

- [ ] **T-70** FastAPI: endpoints `/contracts`, `/scores`, `/report`.
  - Owner: Claude Code.
  - DoD: `uvicorn src.api:app` arranca; OpenAPI accesible en `/docs`.

- [ ] **T-71** Documento `docs/demo-script.md` con narrativa de jurado.
  - Owner: Marlon.
  - 7 minutos cronometrados; menciona: spec, ADRs, hallazgo ejemplo,
    guardarriles éticos, roadmap post-hackathon.

- [ ] **T-72** Auditoría final del repo público.
  - Owner: Marlon.
  - Checklist: cero secretos, cero nombres reales, cero hallazgos
    sin URL, README ≤200 líneas, AGENTS.md ≤200 líneas.

---

## Backlog post-hackathon

- [ ] **T-80** Integración con OCDS Red Flags Guide (OCP).
- [ ] **T-81** Cruce con CIIU del contratista (RUES) → OP-12.
- [ ] **T-82** Calendario de feriados como dependencia externa
  (decisión en ADR-006 cuando aplique).
- [ ] **T-83** Bot Telegram de notificación de hallazgos críticos
  (canal compartido con engine-core).
- [ ] **T-84** Sitio estático de publicación de reportes mensuales.
- [ ] **T-85** Métricas de deriva del agente (`CONSTITUTION.md` §10)
  con dashboard mínimo.

---

## Reglas para mover tareas

1. **Una tarea = un commit** preferiblemente. Si una tarea genera
   más de un commit, marcar sub-tareas con `T-NN.a`, `T-NN.b`.
2. Ningún `[x]` sin commit hash anotado.
3. Si una tarea se bloquea, anotar **bloqueador** explícito y abrir
   *Open question* en el sprint-log del día.
4. Si aparece trabajo no listado: añadir tarea en `tasks.md` antes de
   ejecutar (no trabajo "fantasma").
5. Si se decide **no hacer** una tarea: tachar con `~~T-NN~~` y
   anotar razón en una línea, **no borrar** (trazabilidad).
