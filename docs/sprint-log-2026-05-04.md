# Sprint log — 2026-05-04 → 2026-05-05

## Contexto

- **Evento:** Hackathon Nacional Colombia 5.0 (MinTIC, U. Distrital,
  TEVEANDINA), edición 2026.
- **Cierre de inscripción:** 2026-05-04 23:45 (hora Colombia).
- **Equipo:** Veedores Amplificados.
  - Marlon Naranjo *(capitán, MNC Consultoría)*.
  - Gustavo Puerta *(jurídico-contractual)*.
  - Jaime Cárdenas *(infraestructura)*.
  - Jaime Páez *(investigación / ML)*.
- **Reto:** GobIA Auditor — Detección de Opacidad en Contratos
  Públicos sobre SECOP II.

## Sprint goal

Pasar de **scaffold defendible** (estado al cierre de inscripción) a
**demo funcional sobre datos sintéticos** durante la noche del
2026-05-04 al 2026-05-05. El demo debe correr end-to-end:
`ingest → analyze → report` sobre un fixture de 50–200 contratos
sintéticos con al menos OP-01 y OP-02 disparando hallazgos reales y
explicables.

## Estado al inicio del sprint (commit `feat: GobIA Auditor — initial scaffold`)

- README, LICENSE, .gitignore, .env.example, requirements.txt,
  pyproject.toml en su sitio.
- `docs/architecture.md` con ADR-001 a ADR-004.
- `docs/opacity-signals.md` con 12 señales catalogadas.
- `src/` con skeleton ejecutable.
- `tests/test_smoke.py` con 4 tests verdes (`pytest -q` confirmado).
- `ruff check .` sin warnings.
- Docker Compose y CI configurados.

## TODOs

> Claude Code y operadores humanos pueblan esta lista a medida que
> avanza el sprint. Cada ítem que se termine se marca con `[x]` y se
> referencia el commit que lo cerró.

- [ ] Generar fixture sintético en `tests/fixtures/secop_sample.json`
  con 100–200 contratos cubriendo casos OP-01 (concentración) y OP-02
  (outlier de valor).
- [ ] Activar la llamada real de `SecopClient.get_contracts` contra el
  endpoint Socrata, con paginación `$limit/$offset` y reintentos.
- [ ] Implementar OP-04 (adjudicación en feriado) usando un calendario
  estático de feriados nacionales colombianos.
- [ ] Implementar OP-05 (último día hábil del mes).
- [ ] Implementar OP-11 (fragmentación bajo umbral de modalidad).
- [ ] Conectar `QdrantStore` real (no stub) y elegir embedding
  (sentence-transformers o similar — abrir ADR-005 si se adopta).
- [ ] Conectar `LLMRouter` real con Anthropic Opus 4.7 + fallback
  Ollama qwen3; cachear prompts y respuestas para auditoría.
- [ ] CLI `analyze`: cargar contratos desde Qdrant + Postgres en lugar
  de la lista vacía actual.
- [ ] FastAPI: exponer `/contracts`, `/scores`, `/report` para canales
  futuros.
- [ ] Generar reporte de demo y review final con Gustavo (validación
  jurídica de la narrativa) antes del envío.

## Decisions

Las decisiones arquitectónicas activas están documentadas en
`docs/architecture.md`:

- **ADR-001** Qdrant como memory store (vs. pgvector).
- **ADR-002** Claude Opus 4.7 con fallback Ollama qwen3.
- **ADR-003** Detección híbrida reglas + LLM (no sólo LLM).
- **ADR-004** FastAPI (vs. Flask).

Decisiones operativas tomadas durante este sprint:

- **D-2026-05-04-01:** durante el time-box de inscripción (15 min) NO
  se llaman APIs reales (SECOP, Anthropic, Qdrant). Toda la
  funcionalidad sensible queda como stub con firma estable y test de
  humo de imports.
- **D-2026-05-04-02:** los smoke tests cubren imports y schemas, no
  integración. La integración real queda priorizada en TODOs.

## Open questions

> Dudas pendientes de revisión humana antes de cerrar el sprint.

- ¿La URL `community.secop.gov.co/Public/Tendering/ContractDetailView/Index?contractId=...`
  es la canónica para citar contratos? Validar con Gustavo y, si no,
  ajustar `_build_source_url` en `src/ingestion/normalizer.py`.
- ¿El umbral de concentración por proveedor (0.4 default) es razonable
  o produce demasiados falsos positivos sobre datos reales? Evaluar
  con Jaime P. tras correr el primer batch real.
- ¿Conviene agregar un calendario oficial de feriados como dependencia
  externa o mantenerlo hardcoded? Decidir antes de implementar OP-04.
- ¿Cuál es la cota de costo aceptable por sesión Anthropic durante el
  demo? Acordar con Marlon antes de habilitar `use_llm=True` en
  producción.
- ¿Se incluye el JNI/RUES como fuente externa para OP-12 (CIIU del
  contratista) o se posterga a fase post-hackathon?

## Bitácora

- **2026-05-04 ~21:50** Repo inicializado; primer commit con scaffold
  defendible. `pytest -q` y `ruff check .` verdes.
- **2026-05-04 (siguiente)** segundo commit con `AGENTS.md`,
  `CONSTITUTION.md`, `docs/team.md` y este sprint-log.
