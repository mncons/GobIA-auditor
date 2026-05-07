# AGENTS.md — GobIA Auditor

> Estándar abierto AGENTS.md (no `CLAUDE.md`). Cualquier asistente de IA
> que trabaje sobre este repo (Claude Code, Codex, Cursor, Aider, etc.)
> debe leer este archivo al inicio de cada sesión.
> Mantenerlo bajo 200 líneas. Si crece, audita y borra.

---

## Repository purpose

**GobIA Auditor** es la implementación del equipo **Veedores Amplificados**
(MNC Consultoría) para el reto **GobIA Auditor** de la **Hackathon Nacional
Colombia 5.0** (MinTIC, U. Distrital, TEVEANDINA, edición 2026).

Misión: detectar señales de **opacidad estadística** sobre contratos
publicados en **SECOP II** (dataset Socrata `jbjy-vk9h` en `datos.gov.co`)
y producir un reporte auditable, citable y revisable por humanos.

---

## Architecture overview

Pipeline lineal: `SECOP II → Ingestor → Normalizador → Memory Store
(Qdrant) → Detection Engine (reglas + LLM Router) → Reporter`.

Detalle completo en [`docs/architecture.md`](docs/architecture.md). Las
ADRs vigentes son ADR-001..004 (Qdrant, Claude+Ollama, reglas+LLM,
FastAPI), ADR-007 (combinación lineal regla+LLM), ADR-008 (`/contest`,
Pack 4 Responsiveness) y ADR-009 (Streamlit dashboard no-decisorio).

Este repo hereda el patrón de agentes del monorepo MNC AgentOS:
`/home/thinkpad/projects/mnc-agentos/packages/engine-core/`. La
correspondencia es:

- `channel-adapters` → CLI + FastAPI internos (Telegram en fase 2).
- `llm-router` → `src/detection/llm_router.py` (Anthropic + Ollama).
- `memory-store` → `src/storage/qdrant_store.py` sobre Qdrant.
- `agent-scheduler` → pendiente; cron simple por ahora.

GobIA es la **cuarta aplicación** del patrón "monitor autónomo sobre
datasets del Estado" después de FundingRadar (Minciencias, iNNpulsa, SENA).

---

## Stack and conventions

- **Lenguaje:** Python 3.11.
- **Framework web:** FastAPI (typing nativo, OpenAPI auto).
- **HTTP cliente:** httpx async.
- **Tests:** pytest.
- **Lint:** ruff (config en `pyproject.toml`).
- **Validación de datos:** Pydantic v2.
- **Type hints obligatorios** en funciones públicas.
- **Docstrings en español, formato Google style.**
- **Comentarios en español.** Si el "por qué" no es obvio, prefijar
  con `# WHY:`.
- **Commits convencionales:** `feat:`, `fix:`, `docs:`, `chore:`,
  `test:`, `refactor:`. Cuerpo opcional cuando la decisión no es trivial.
- **Nombres de archivos:** sin tildes ni espacios; snake_case en Python,
  kebab-case en docs. Fechas ISO `YYYY-MM-DD`.

---

## What Claude Code MUST do

1. **Antes de cada commit**: correr `ruff check .` y `pytest -q`. Si
   alguno falla, no commitear hasta resolver — abrir TODO en
   `docs/sprint-log-YYYY-MM-DD.md` si la causa raíz no es inmediata.
2. **Commits atómicos por feature.** No mezclar refactors con cambios
   funcionales en el mismo commit.
3. **Sprint log**: actualizar `docs/sprint-log-YYYY-MM-DD.md` al iniciar
   y al cerrar cada sesión, con TODOs y decisiones tomadas.
4. **Respetar el time-box documentado** en cada sprint log. Si se agota,
   parar y registrar el estado.
5. **Citar fuente** SECOP en todo hallazgo de ejemplo: `id_contrato` +
   URL en `community.secop.gov.co`.
6. **Verificar tu trabajo antes de devolver respuesta** (Cherney hack 3):
   ¿corre? ¿pasa lint? ¿pasa tests? ¿está documentado?

---

## What Claude Code MUST NOT do

1. **No inventar endpoints** SECOP fuera de
   `https://www.datos.gov.co/resource/jbjy-vk9h.json`. Si se necesita
   otro dataset, abrir ADR antes de tocar código.
2. **No llamar APIs reales con datos de producción** durante desarrollo.
   Usar fixtures en `tests/fixtures/` o data sintética generada.
3. **No usar nombres de contratistas reales** en ejemplos de docs ni en
   tests. Sólo ficticios o anonimizados.
4. **No afirmar corrupción.** Sólo señalar opacidad estadística con
   justificación cuantificada. Esta restricción es contractual con la
   audiencia (jurado y veedores) — ver `CONSTITUTION.md`.
5. **No instalar dependencias** que no estén en `requirements.txt` sin
   justificarlas en el commit que las añade.
6. **No tocar `.env`**. Usar `.env.example` como referencia.
7. **No hacer `git push`** sin autorización explícita. Las ramas
   permanecen locales hasta recibir credenciales del repo público.
8. **No SPA frontend** (Next.js, Tailwind, React) en este vertical.
   Sí se permite **un único dashboard de auditoría no-decisorio**
   (`streamlit_app.py`) que solo consulta y ofrece form de impugnación
   `POST /contest`; ningún UI puede modificar el score automáticamente.
   Ver ADR-009.

---

## Definition of Done

- [ ] `pytest -q` verde.
- [ ] `ruff check .` sin warnings.
- [ ] Docstrings en español formato Google donde se añadió código nuevo.
- [ ] Documentación actualizada (`docs/` o README según corresponda).
- [ ] Commit con mensaje convencional explicativo.
- [ ] `docs/sprint-log-YYYY-MM-DD.md` actualizado.
- [ ] Si se introdujo decisión arquitectónica nueva: ADR añadido a
  `docs/architecture.md`.

---

## Escalation

Si Claude Code se atasca:

1. **Parar.** No inventar APIs, campos ni datos para "destrabar".
2. **Registrar TODO** en `docs/sprint-log-YYYY-MM-DD.md` con:
   - Qué se intentó.
   - Qué falló.
   - Qué hipótesis quedan abiertas.
3. **Pasar al siguiente bloque** del sprint si existe; el bloque
   atascado queda para revisión humana en la siguiente sesión.
4. **Nunca** desactivar tests ni linters para hacer pasar CI. Si CI
   está roto, la prioridad es entender por qué.

Contacto humano: `info@mnconsultoria.org` (Marlon Naranjo, capitán).
