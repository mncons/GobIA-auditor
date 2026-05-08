# AGENTS.md — GobIA Auditor

> Estándar abierto AGENTS.md (no `CLAUDE.md` — fuente única para este
> repo). Cualquier asistente de IA (Claude Code, Codex, Cursor, Aider,
> etc.) debe leer este archivo al inicio de cada sesión.
>
> Tope blando: 320 líneas. Si crece más, mover el Apéndice A a
> `docs/notebooklm-cuadernos-relevantes.md` y dejar aquí solo la
> referencia.

---

## Repository purpose

**GobIA Auditor** es la implementación del equipo **Veedores Amplificados**
(MNC Consultoría) para el reto **GobIA Auditor** de la **Hackathon
Nacional Colombia 5.0** (MinTIC, U. Distrital, TEVEANDINA, edición 2026).

Misión: detectar señales de **opacidad estadística** sobre contratos
publicados en **SECOP II** (dataset Socrata `jbjy-vk9h` en
`datos.gov.co`) y producir un reporte auditable, citable y revisable
por humanos.

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
datasets del Estado" después de FundingRadar (Minciencias, iNNpulsa,
SENA).

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
  `test:`, `refactor:`. Cuerpo opcional cuando la decisión no es
  trivial.
- **Nombres de archivos:** sin tildes ni espacios; snake_case en
  Python, kebab-case en docs. Fechas ISO `YYYY-MM-DD`.

---

## Investigación obligatoria: NotebookLM antes de codificar

**Antes de proponer arquitectura, desarrollar estrategia o escribir
código**, conéctate al MCP `notebooklm-mcp` y consulta el cuaderno más
relevante de la lista curada en el **Apéndice A** (53 cuadernos,
edición 2026-05-07). Extrae **exclusivamente** las respuestas, guías o
código condensado de NotebookLM y basa tus acciones de desarrollo
únicamente en esa información.

> Esta lista **sustituye y deja obsoleta** la referencia previa a "122
> cuadernos del usuario". El Apéndice A es la fuente vigente y cerrada.

Reglas de consulta:

1. **Una pregunta puntual por consulta.** No pidas resumen completo.
2. **Cita el título del cuaderno** en commits, ADRs y sprint logs.
   Ej: `feat(detection): umbral pHHI=0.85 — fuente NLM "Evolución y
   Estado del Arte: RAG, CAG, RAFT y GraphRAG"`.
3. **No pegues citas largas** en código ni docs. Resume en tus palabras.
4. **Si la lógica con datos verificables del repo o del dataset SECOP
   choca con el cuaderno, gana la lógica.** Documenta el desacuerdo
   en un ADR.
5. **Si el MCP no responde** o el cuaderno no aporta, marca la decisión
   como provisional con `[NEEDS-NLM-VERIFY]` en el sprint log y no
   commitees código que dependa de patrones no verificados.
6. **Si la pregunta no encaja en ninguno de los 53 cuadernos**, declara
   "fuera de corpus NotebookLM curado" y pide guía humana o usa fuente
   externa verificable con cita.
7. **Verifica con `claude mcp list`** que el MCP esté activo al inicio.

Alternativa CLI (otra terminal): `nlm query "<título>" "<pregunta>"`.

---

## What Claude Code MUST do

1. **Antes de cada commit:** correr `ruff check .` y `pytest -q`. Si
   alguno falla, no commitear hasta resolver — abrir TODO en
   `docs/sprint-log-YYYY-MM-DD.md` si la causa raíz no es inmediata.
2. **Commits atómicos por feature.** No mezclar refactors con cambios
   funcionales en el mismo commit.
3. **Sprint log:** actualizar `docs/sprint-log-YYYY-MM-DD.md` al
   iniciar y al cerrar cada sesión, con TODOs y decisiones tomadas.
4. **Respetar el time-box documentado** en cada sprint log. Si se
   agota, parar y registrar el estado.
5. **Citar fuente SECOP** en todo hallazgo de ejemplo: `id_contrato` +
   URL en `community.secop.gov.co`.
6. **Verificar tu trabajo antes de devolver respuesta** (Cherney
   hack 3): ¿corre? ¿pasa lint? ¿pasa tests? ¿está documentado?
7. **Consultar NotebookLM** (sección anterior) antes de proponer
   arquitectura, estrategia o código nuevo. Citar el título del
   cuaderno consultado.
8. **Cerrar la sesión con el prompt de Compound Engineering** del
   **Apéndice B**. Confirmar que el cuaderno NotebookLM fue creado
   antes de cerrar la terminal.

---

## What Claude Code MUST NOT do

1. **No inventar endpoints SECOP** fuera de
   `https://www.datos.gov.co/resource/jbjy-vk9h.json`. Si se necesita
   otro dataset, abrir ADR antes de tocar código.
2. **No llamar APIs reales con datos de producción** durante
   desarrollo. Usar fixtures en `tests/fixtures/` o data sintética
   generada.
3. **No usar nombres de contratistas reales** en ejemplos de docs ni
   en tests. Sólo ficticios o anonimizados.
4. **No afirmar corrupción.** Sólo señalar opacidad estadística con
   justificación cuantificada. Esta restricción es contractual con la
   audiencia (jurado y veedores) — ver `CONSTITUTION.md`.
5. **No instalar dependencias** que no estén en `requirements.txt`
   sin justificarlas en el commit que las añade.
6. **No tocar `.env`.** Usar `.env.example` como referencia.
7. **No hacer `git push`** sin autorización explícita. Las ramas
   permanecen locales hasta recibir credenciales del repo público.
8. **No SPA frontend** (Next.js, Tailwind, React) en este vertical.
   Sí se permite **un único dashboard de auditoría no-decisorio**
   (`streamlit_app.py`) que solo consulta y ofrece form de impugnación
   `POST /contest`; ningún UI puede modificar el score
   automáticamente. Ver ADR-009.
9. **No basar decisiones técnicas en memoria del modelo** cuando
   exista un cuaderno relevante en el Apéndice A. Consulta primero.
10. **No inventar IDs ni títulos de cuadernos NotebookLM** fuera de
    los listados en el Apéndice A.

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
- [ ] Si se consultó NotebookLM: título del cuaderno citado en el
  commit o ADR.

---

## Escalation

Si Claude Code se atasca:

1. **Parar.** No inventar APIs, campos ni datos para "destrabar".
2. **Registrar TODO** en `docs/sprint-log-YYYY-MM-DD.md` con: qué se
   intentó, qué falló, qué hipótesis quedan abiertas.
3. **Pasar al siguiente bloque** del sprint si existe; el bloque
   atascado queda para revisión humana en la siguiente sesión.
4. **Nunca** desactivar tests ni linters para hacer pasar CI. Si CI
   está roto, la prioridad es entender por qué.

Contacto humano: `info@mnconsultoria.org` (Marlon Naranjo, capitán).

---

## Apéndice A — Cuadernos NotebookLM curados (53)

Lista vigente al 2026-05-07. Selecciona **uno** por consulta, el más
relevante a la solicitud. Sustituye al inventario anterior de 122. Si
un cuaderno no aparece en tu instancia NotebookLM, registra la falta
en el sprint log; no inventes IDs ni títulos.

### Núcleo agéntico, skills y agentes IA

- 🛠️ Guía Maestra de Claude: Automatización, Skills y Agentes IA
- 🤖 Guía de Codex CLI y el Futuro de la Programación con Agentes
- 🤖 Guía Estratégica de Cloud Code para Meta Ads y Programación
- 🤖 Ecosistema Gentle AI: Tutorial de Engram, SDD y Skills
- 🦞 Agentes de IA: Revolución, Seguridad y el Futuro Digital
- 🤖 Dominio de Agentes de IA: Guía Estratégica y Técnica
- 🤖 Dominio de Agentes de IA y Automatización Avanzada
- 🤖 El Nuevo Paradigma del Desarrollo y los Agentes de IA
- 👨‍🏫 Desarrollo Moderno: Agentes de IA, Kotlin, Python y UX
- 🤝 IA: Del Genio en la Lámpara al Compañero de Equipo
- 🤖 Cooperative Systems for Language Programming

### RAG, modelos fundacionales y entrenamiento

- 🎓 Bootcamp de Sistemas RAG y Agentes de IA 2025
- 🧠 Evolución y Estado del Arte: RAG, CAG, RAFT y GraphRAG
- 🤖 Entrenamiento y Post-entrenamiento de Modelos de Lenguaje Pequeños
- 🧠 Modelos Fundacionales e IA Generativa: El Camino Hacia la AGI
- 🤖 Fronteras de la Inteligencia Artificial: Modelos, Hardware y Aplicaciones
- 📈 Índice Económico Anthropic: Primitivas y Evolución de la IA
- 🤖 Siraj — Compendio de Inteligencia Artificial y Algoritmos de Aprendizaje Máximo

### Datos, Python e ingeniería

- 🎓 Entrevista Técnica y Hoja de Ruta para Científicos de Datos
- 🐍 Python, Datos y el Ecosistema IT: Guía Integral de Programación
- 🐍 Guía Maestra para Aprender Python, Ciencia de Datos e IA
- 📍 Optimización, Planificación y Algoritmos de Inteligencia Artificial colectiva

### Stack, entorno y DevOps

- 🚀 Guía Maestra de Desarrollo, Arquitectura y Stack Tecnológico 2025
- 👩‍💻 Guía Rápida de Warp: Entorno de Desarrollo Agente
- 🐧 Guía Integral del Sistema Operativo UNIX
- 🐳 n8n y Docker: Guías de Instalación y Uso
- 📚 containers — Aplicaciones de productividad calificadas
- 💻 Tendencias y Herramientas de IA para Programación

### Seguridad, ética y políticas

- 🤖 Miessler — El futuro de la IA: Seguridad, creatividad y sociedad
- 🤖 El Horizonte de la IA: Seguridad, Agentes y Futuro
- 📈 Visiones de IA: Seguridad, Política y el Futuro 2025

### Negocio, SaaS y consultoría

- 🚀 Estrategias Maestras para el Éxito en Software B2B
- 🚀 Fundamentos y Estrategias para el Éxito de una Startup
- 🚀 Ecosistema Startup: Innovación, IA y Estrategia de Crecimiento
- 💻 Estrategias de Negocio y Venta para SaaS
- 🤖 Negocios SAAS
- 🤖 Guía Maestra de Automatización e Inteligencia Artificial para Negocios
- 🤖 Dominio de la IA: Herramientas, Automatización y Estrategias Empresariales
- 🚀 Estrategias de Consultoría en IA, Criptoactivos y Negocios Digitales
- 🤖 5 Industrias con Alta Demanda de Automatización con IA (2025) — CO II..Sales..Mindset SaaS
- ⚙️ Estrategias Maestras: IA, Automatización y Disciplina
- 🚀 Estrategias de Riqueza y Emprendimiento en la Era IA
- 🚀 Estrategias Digitales: Influencia, IA y Marketing para Emprendedores
- 🚀 Innovación, Metas y Estrategias en la Era de la IA

### Panorama IA, geopolítica y futuro

- 🤖 Panorama de la Evolución y Avances de la Inteligencia Artificial
- 🚀 Nuevas Fronteras: IA, China y Estrategia Empresarial
- 🤖 La Nueva Frontera: IA, Robótica y la Carrera Tecnológica Global
- 🤖 Horizontes de la IA: De la Ingeniería al Futuro Global
- 🤖 Fronteras de la IA: Ciencia, Salud y Futuro Profesional
- 🧪 Laboratorios Autónomos: El Futuro de la Investigación Científica con IA

### Colombia y contexto local (ancla GobIA)

- 🏗️ Arquitectura y Estrategia de IA en Colombia
- ⚛️ Convocatoria ColombIA Inteligente: Cuántica e IA en los Territorios

### Finanzas, blockchain y cripto

- 🤖 Inteligencia Artificial, Blockchain y Finanzas: Guía de Implementación Técnica

### Cómo consultar

```bash
# Verificar que el MCP esté activo
claude mcp list

# Desde el chat: invocar la tool del MCP con título + pregunta puntual.
# Alternativa CLI desde otra terminal:
nlm query "<título-del-cuaderno>" "<pregunta puntual>"
```

---

## Apéndice B — Cierre de sesión: Compound Engineering Prompt

Al finalizar cada sesión o jornada, **antes de cerrar la terminal**,
envía exactamente este prompt para evitar pudrición de memoria local
y consolidar la sesión como cuaderno auditable de largo plazo:

> Haz un resumen exhaustivo y estructurado de todas las decisiones
> técnicas, código, errores solucionados y estrategias que
> desarrollamos en la sesión de hoy. A continuación, utiliza tu
> conexión MCP con NotebookLM para crear un NUEVO cuaderno (titulado
> con la fecha y nombre del proyecto actual) y guarda todo este
> resumen allí como la primera fuente. Confírmame cuando el nuevo
> cuaderno esté creado y la información respaldada.

**Convención de nombre del nuevo cuaderno:**
`gobia-auditor_YYYY-MM-DD_resumen-sesion`
(ej: `gobia-auditor_2026-05-07_detector-opacidad-v1`).

**Si el MCP NotebookLM no está disponible al cierre:** persistir el
resumen en `docs/sprint-log-YYYY-MM-DD.md` con un TODO
`[NEEDS-NLM-SYNC]` para respaldarlo en la siguiente sesión que tenga
el MCP activo. El sprint-log es bitácora local del repo; el cuaderno
NotebookLM es memoria externa que sobrevive a borrados de contexto.
**No cerrar sesión sin resumen.**

---

Última revisión: 2026-05-07. Próxima auditoría programada: 2026-06-07.
