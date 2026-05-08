# Sprint log — 2026-05-08 (offline tuning + ADR-010)

> Sesión post-D1 del Hackathon Nacional Colombia 5.0. Time-box: **90 min**.
> Objetivo: cerrar TODO[ALTA] #1 y #2 del sprint anterior (Ollama qwen3
> instalado + reconciliación haiku/opus dual) y agregar smoke real de
> integración antes de demo D2.

## Time-box y bloques

| # | Bloque | Tiempo objetivo | Estado |
|---|--------|----------------|--------|
| 0 | Pre-flight (sprint log apertura + NLM) | 10 min | ✅ |
| 1 | `fix(router)` qwen3:1.7b + payload endurecido | 25 min | ✅ |
| 2 | `test(integration)` smoke offline qwen3:1.7b | 25 min | ✅ |
| 3 | `docs` ADR-010 + arquitectura | 15 min | ✅ |
| 4 | Tag `v0.3-offline-tuned` + cierre + Compound Engineering | 15 min | 🔄 |

## NotebookLM — consulta de pre-flight

- **Cuaderno:** "🤖 Entrenamiento y Post-entrenamiento de Modelos de Lenguaje Pequeños" (id `c858891a-...`).
- **Pregunta:** rangos de `num_predict` y `temperature` para clasificación numérica determinista en modelos <2B sin GPU + valor del modo *thinking* en scoring.
- **Respuesta condensada (mis palabras, parafraseando — no se pegan citas):**
  - Temperatura recomendada para extracción estricta: **0.0** (algunos panelistas usan 0.20). T=0 puro a veces deja al modelo "reterco".
  - `num_predict` no tiene cifra cerrada en el corpus; lo que sí está documentado es la **regla de truncar agresivamente** para ahorrar memoria/tiempo en máquinas sin recursos.
  - Modo *thinking*: para tareas básicas tipo scoring/contar **el thinking quita valor** (peor puntaje + más latencia). El modelo *Instruct* sin thinking es igual o mejor.
- **Cómo se aplica al fix:** confirma `think=False` y la dirección de bajar `num_predict` (120 sigue siendo conservador frente al "1–5 tokens" que sugiere la nota externa al corpus, pero da margen para que el modelo escupa también una mini-rationale). `temperature=0.3` queda **un punto arriba** del rango ideal del NLM (0.0–0.20); justifico la desviación en ADR-010 (1.7B con T=0 cae en repetition-loops empíricamente).
- **MCP estado:** activo — sin `[NEEDS-NLM-VERIFY]`.

## Verificación de servicios

- `curl http://localhost:11434/api/tags` → Ollama vivo, `qwen3:1.7b` (2.0B Q4_K_M, 1.4 GB) y `qwen3:8b` ambos pulled.
- `git status` arranca con cambios sin commitear de la sesión previa en `src/detection/llm_router.py` y `tests/test_llm_router.py` (modelo + think + keep_alive a medio camino) — los integro en el commit 1 de esta sesión.
- `AGENTS.md` aparece modificado pero no es trabajo de esta sesión; no se toca en mis commits.

## Tag de release

`v0.3-offline-tuned` apunta a `ae1b8d0` (commit ADR-010), creado anotado
con `git tag -a`. **Pusheado** a `mncons/GobIA-auditor` en post-cierre.

## Commits (3 sesión + cierre + 2 post-cierre TODO[MEDIA])

| SHA      | Tipo  | Resumen                                                                        |
|----------|-------|--------------------------------------------------------------------------------|
| 3339376  | fix   | router: qwen3:1.7b + think=false + keep_alive=30m + num_predict=120 + T=0.3   |
| 496f394  | test  | integration: smoke offline qwen3:1.7b en T495 con skip-policy y xfail latency |
| ae1b8d0  | docs  | architecture: ADR-002 actualizado + ADR-010 nuevo (haiku/opus dual + offline) |
| 443e025  | chore | sprint-log cierre 2026-05-08                                                   |
| 26ef25e  | docs  | agents: refresh policy + Apéndice A (53 cuadernos NLM) + Apéndice B           |
| 768ee35  | docs  | agents: list ADR-010 in vigent ADRs (cierra TODO[MEDIA] #3)                   |

(Los dos últimos commits resuelven TODO[MEDIA] #3 y arrastran el
refresh de AGENTS.md que el usuario tenía pendiente sin commitear,
ambos pusheados al remote canónico `mncons/GobIA-auditor`.)

## Decisiones tomadas

- **Modelo offline reducido a qwen3:1.7b.** `qwen3:8b` queda como modelo de
  reserva pesado, no como fallback default. Justificación: 8 tok/s
  medidos en T495 sin GPU + thinking ON inviables para demo en vivo.
- **Asimetría intencional Anthropic vs Ollama en `_call_ollama`.** Quité
  `max_tokens`/`temperature` de la firma. El caller pasa esos args para
  Anthropic (donde tienen sentido) y la rama Ollama usa constantes
  `OLLAMA_*`. Si alguien quiere overridear desde el caller, abrir cambio
  aparte (config.py o kwargs explícitos por proveedor).
- **Temperature offline = 0.3 (no 0.0).** Desviación consciente del NLM
  ("ideal 0.0–0.20"): el 1.7B con T=0 cae en repetition-loops empíricos.
  Documentado en ADR-010 §Consecuencias. Mitigación: el peso del LLM en
  el score final es solo 0.3 (ADR-007), el ruido es acotado.
- **Integration tests excluidos del run normal.** Se marcaron con
  `@pytest.mark.integration` y registraron en `pyproject.toml`. Run por
  defecto: `pytest -q -m "not integration"`. Run completo (con Ollama
  real): `pytest -q`.
- **Latencia smoke = 6.75s** en T495 con modelo caliente (`keep_alive`
  efectivo, TTL ≈30 min confirmado vía `/api/ps`). Bien por debajo del
  budget de 25s.

## Hallazgos / sorpresas técnicas

- **Ollama API: `keep_alive` y `think` son top-level, NO van en `options`.**
  Si se anidan en `options` Ollama los ignora silenciosamente — falla
  invisible. El test `test_ollama_payload_endurecido` lo cubre parsing
  el body real del request (pytest-httpx no valida body por defecto).
- **NotebookLM responde rápido para preguntas puntuales.** La consulta
  al cuaderno de "Modelos de Lenguaje Pequeños" tomó ~6s y devolvió 9
  citas concretas. Confirmó la dirección del fix sin necesidad de
  experimentación adicional.
- **Tests de integración con skip-policy explícita > tests xfail estáticos.**
  El fixture `ollama_alive` decide skip vs run en runtime, lo que permite
  que CI sin Ollama no falle y dev local con Ollama corra el smoke real.

## Pendiente al cierre — TODOs

### TODO[ALTA] — cerrados en post-cierre

1. ✅ **Push autorizado.** Usuario dio luz verde; `main` y
   `v0.3-offline-tuned` arriba en `mncons/GobIA-auditor`. El primer
   `git push` reveló un alias viejo del remote (`gobia-auditor`
   lowercase) con redirect transparente desde GitHub; se actualizó a
   `https://github.com/mncons/GobIA-auditor.git` y se persistió en
   engram (topic `infra/git-remote`). Pushes posteriores limpios.

### TODO[MEDIA] — cerrados en post-cierre

2. ✅ **Compound Engineering: cuaderno NotebookLM creado.** Cuaderno
   `gobia-auditor_2026-05-08_router-offline-tuning`
   (id `0028a921-9a5a-4b1f-b4a9-a086dc32a9f4`) con resumen de sesión
   indexado como primera fuente.
3. ✅ **AGENTS.md líneas 32-34 actualizado** con ADR-010 en el listado
   vigente (commit `768ee35`). En el camino se commiteó también el
   refresh de policy + Apéndice A 53 cuadernos NLM + Apéndice B
   Compound Engineering que estaba pendiente desde antes (`26ef25e`).

### TODO[BAJA]

4. **Considerar exponer `OLLAMA_*` como env vars** en `src/config.py` si
   más adelante hace falta tunearlas sin recompilar (p.ej. demo en
   máquina con GPU donde `qwen3:8b` sí es viable).
5. **TODOs heredados del sprint 2026-05-07** que NO se atacaron hoy:
   OP-14 oferente único, `RuleEngine.evaluate_with_context`, parquet en
   `bulk_snapshot`, fixture sintético T-10, ADR-005 embeddings, ADR-006
   feriados.

## Smoke test — comandos verificados hoy

```bash
cd /home/thinkpad/projects/gobia-auditor
source .venv/bin/activate

# 1. Lint + suite normal (sin Ollama real)
ruff check .                                              # All checks passed
pytest -q -m "not integration"                            # 42 passed

# 2. Suite completa con Ollama real (qwen3:1.7b pulled)
ollama list                                               # qwen3:1.7b ✓
pytest -q -m integration                                  # 1 passed en 6.75s

# 3. Verificar TTL keep_alive
curl -s http://localhost:11434/api/ps | jq '.models[] | {name, expires_at}'
#   "name": "qwen3:1.7b", "expires_at": "...+30min"
```

