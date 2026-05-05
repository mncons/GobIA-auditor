# plan.md — GobIA Auditor

> **Cómo** lo construimos: stack, restricciones y trade-offs.
> Hereda gobierno de `mnc-agentos/AGENTS.md` y se restringe a la
> verticalidad de monitoreo de SECOP II.
> Para el QUÉ y POR QUÉ ver `spec.md`. Para descomposición de
> trabajo ver `tasks.md`.

---

## 1. Herencia desde MNC AgentOS

Este vertical no nace en vacío: hereda explícitamente del monorepo
`/home/thinkpad/projects/mnc-agentos/`:

- **Patrón de agente**: `engine-core` define `channel-adapters`,
  `llm-router`, `memory-store`, `agent-scheduler`. GobIA implementa
  los cuatro adaptados a Python.
- **Plantilla de gobierno**: `mnc-agentos/docs/templates/CONSTITUTION-template.md`
  fue la base de nuestro `CONSTITUTION.md` (ver mapeo 1:1 de las 13
  secciones).
- **Reglas operativas** del `AGENTS.md` raíz del monorepo se aplican
  directamente: trifecta letal, prohibición de inventar info, sin
  llaves en código, comentarios pedagógicos `# WHY:`, ADRs numerados.
- **Patrón "monitor autónomo sobre datasets del Estado"**: precedente
  FundingRadar (Minciencias / iNNpulsa / SENA). GobIA es la cuarta
  aplicación del patrón, esta vez sobre SECOP II.

Lo que **no** se hereda y se diferencia explícitamente:

- Stack runtime (ver §2).
- Canales primarios (engine-core arrancó con Telegram/grammy; GobIA
  arranca con CLI + reporte Markdown estático).

---

## 2. Stack y por qué Python aquí, no Bun+TS

`mnc-agentos` es **Bun + TypeScript** (grammy, SQLite con FTS5,
Telegram-first). GobIA Auditor es **Python 3.11**. Esta divergencia
es deliberada y se justifica así:

| Eje | mnc-agentos (Bun+TS) | GobIA (Python) |
|---|---|---|
| Carga dominante | Mensajería conversacional | Análisis estadístico de datasets |
| Latencia objetivo | Sub-segundo en chat | Lote nocturno, no interactivo |
| Librerías clave | grammy, hono, fastify | pandas, numpy, scipy, statsmodels |
| Cliente LLM principal | API HTTP directa | Anthropic SDK Python (mantenido oficialmente) |
| Cliente Qdrant | qdrant-js | qdrant-client (más maduro, Pydantic-friendly) |
| SDK Socrata | No oficial en TS | sodapy y httpx triviales |
| Talento del equipo | Marlon, Jaime C. | Jaime Páez (VIRTUS, Investigador Senior Minciencias) |
| Análisis con cuadernos | Awkward | Jupyter nativo |
| Despliegue | Bun runtime en VPS | Python 3.11-slim en Docker |

**Conclusión:** la elección de stack se hace **por carga dominante
del vertical**, no por consistencia con el monorepo. El patrón es
compartido (CONSTITUTION + ADRs + skills declaradas + memory store
vectorial); la implementación es lenguaje-apropiada.

Una segunda razón es **soberanía del equipo**: el dominio analítico
en GobIA pertenece a Jaime Páez, cuyo flujo de investigación es
Python-nativo (Minciencias, grupo VIRTUS). Forzar TS añadiría
fricción sin beneficio en este vertical.

---

## 3. Componentes

```
src/
├── config.py                      Settings tipadas (pydantic-settings)
├── ingestion/
│   ├── secop_client.py           httpx async contra Socrata jbjy-vk9h
│   └── normalizer.py             dict crudo → Contract (Pydantic)
├── detection/
│   ├── rules.py                  RuleEngine determinístico (OP-01..)
│   └── llm_router.py             OpacityScore = reglas + LLM opcional
├── storage/
│   └── qdrant_store.py           Qdrant memory store (upsert/search)
├── reporting/
│   └── report.py                 OpacityScore[] → Markdown citable
└── main.py                       CLI argparse: ingest / analyze / report
```

Detalle de contratos entre componentes en
[`docs/architecture.md`](architecture.md).

---

## 4. Decisiones que ya están firmadas (ADRs)

| ADR | Decisión | Trade-off aceptado |
|---|---|---|
| 001 | Qdrant, no pgvector | Un servicio extra; alineación con engine-core |
| 002 | Claude Opus 4.7 + Ollama qwen3 fallback | Doble integración; soberanía y demo offline |
| 003 | Reglas + LLM, no sólo LLM | Más código de reglas; auditabilidad y costo |
| 004 | FastAPI, no Flask | Curva nueva para algunos; typing y OpenAPI auto |

ADRs futuros previstos:

- **ADR-005** — Estrategia de embeddings para Qdrant (modelo, idioma).
- **ADR-006** — Calendario de feriados (dependencia externa o hardcoded).
- **ADR-007** — Política de cache de prompts/respuestas LLM para
  trazabilidad y auditoría externa.

---

## 5. Restricciones duras

Heredadas de `AGENTS.md` y del `CONSTITUTION.md`:

- **No inventar endpoints** SECOP fuera de
  `https://www.datos.gov.co/resource/jbjy-vk9h.json`.
- **No usar nombres de contratistas reales** en docs ni tests.
- **No instalar dependencias** fuera de `requirements.txt` sin
  justificarlas en el commit.
- **No hacer push** a remotos sin autorización explícita del capitán.
- **Cero hallazgos** sin URL fuente (regla cero del reporte).
- **Type hints obligatorios** en funciones públicas; **docstrings
  Google style en español**; comentarios en español.
- **Definition of Done** del repo aplica a todo PR
  (`AGENTS.md` §Definition of Done).

---

## 6. Métricas de avance del proyecto

Durante hackathon, métricas que el capitán observa por ciclo:

- # de señales implementadas (target: ≥4 al cierre del demo).
- # de tests automatizados verdes (target: ≥6 al cierre del demo).
- # de ADRs cerradas (target: ≥4 al cierre).
- Tiempo de ejecución end-to-end sobre fixture (target: <2 min).
- Líneas de código en `src/` (target: <2000 — si crece más, es señal
  de sobre-ingeniería para un MVP).

Post-hackathon, métricas que el agente respeta (definidas en
`CONSTITUTION.md` §10).

---

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Socrata cambia el schema del dataset | Normalizador con defaults seguros + tests sobre fixture estable |
| LLM alucina justificaciones | Reglas determinísticas son la única fuente de "señal disparada"; LLM solo enriquece narrativa |
| Costo Anthropic se dispara en producción | `use_llm=False` por defecto; LLM sólo sobre contratos que ya activaron una regla |
| Falsos positivos altos en OP-01 | Umbral configurable, validación con Jaime P. sobre datos reales antes del demo |
| Lectura sensacionalista de los hallazgos | `CONSTITUTION.md` §3 + revisión humana antes de publicar (`§4 restricción 3`) |

---

## 8. Lo que este plan NO cubre

- Despliegue a producción permanente (post-hackathon).
- Integración con SECOP I (legacy) — sólo SECOP II en este alcance.
- Canales de notificación push (Telegram, email) — fase 2.
- Modelo de embeddings definitivo — pendiente de ADR-005.
- Estrategia de monetización — fuera de alcance del vertical MIT.
