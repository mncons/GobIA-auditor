# Arquitectura — GobIA Auditor

> Documento vivo. Cualquier desviación del diseño aquí descrito debe abrir
> un ADR nuevo (numeración secuencial) o actualizar uno existente.

---

## 1. Vista de componentes

```
+-------------------+
| SECOP II (Socrata)|   datos.gov.co/resource/jbjy-vk9h.json
+---------+---------+
          |  HTTPS GET con paginación
          v
+-------------------+
|     Ingestor      |   src/ingestion/secop_client.py  (httpx async)
+---------+---------+
          | dict crudo
          v
+-------------------+
|   Normalizador    |   src/ingestion/normalizer.py    (Pydantic)
+---------+---------+
          | Contract validado
          +----------------+
          |                |
          v                v
+-------------------+   +--------------------------------------------+
|   Memory Store    |   |              Detection Engine              |
|     (Qdrant)      |   |                                            |
| upsert/search     |   |  +-----------------+   +----------------+  |
+-------------------+   |  |  RuleEngine     |   |   LLM Router   |  |
                        |  |  (rules.py)     |   |  (Anthropic    |  |
                        |  |  - concentr.    |   |   primario,    |  |
                        |  |  - IQR valor    |   |   Ollama       |  |
                        |  |  - temporal     |   |   fallback)    |  |
                        |  +--------+--------+   +-------+--------+  |
                        |           |                    |           |
                        |           +---------+----------+           |
                        |                     v                      |
                        |              OpacityScore                  |
                        +-------------------+------------------------+
                                            |
                                            v
                                  +---------------------+
                                  |      Reporter       |   src/reporting/report.py
                                  |  Markdown + cita    |
                                  |  community.secop    |
                                  +---------------------+
```

---

## 2. Contratos entre componentes

### 2.1 `Contract` (salida del Normalizador)

Schema mínimo (`src/ingestion/normalizer.py`):

| Campo            | Tipo            | Origen SECOP                          |
|------------------|-----------------|---------------------------------------|
| `id`             | `str`           | `id_contrato` / `referencia_contrato` |
| `entity`         | `str`           | `nombre_entidad`                      |
| `contractor`     | `str`           | `proveedor_adjudicado`                |
| `contractor_id`  | `str \| None`   | `nit_del_proveedor_adjudicado`        |
| `value`          | `Decimal`       | `valor_del_contrato`                  |
| `signed_date`    | `date \| None`  | `fecha_de_firma`                      |
| `start_date`     | `date \| None`  | `fecha_de_inicio_del_contrato`        |
| `end_date`       | `date \| None`  | `fecha_de_fin_del_contrato`           |
| `modality`       | `str`           | `modalidad_de_contratacion`           |
| `sector`         | `str`           | `rama` / `entidad_rama`               |
| `source_url`     | `str`           | construido a partir de `id`           |

### 2.2 `OpacityScore` (salida del Detection Engine)

```python
class OpacityScore(BaseModel):
    contract_id: str
    score: float          # 0.0 .. 1.0
    signals: list[str]    # ids de las señales activadas
    rationale: str        # explicación humana, citable
    source_url: str       # URL pública en community.secop.gov.co
```

`score` no es probabilidad de corrupción. Es una **medida agregada de
opacidad estadística** según las reglas activadas.

---

## 3. Flujos

### 3.1 Ingesta diaria

1. `secop_client.get_contracts(date_from, date_to)` consulta el endpoint
   Socrata con paginación `$limit` / `$offset`.
2. Cada item se valida vía `Contract.model_validate(...)`.
3. Se hace `qdrant_store.upsert(contracts)` indexando un embedding del
   objeto del contrato + metadatos para búsqueda posterior.

### 3.2 Análisis batch

1. `RuleEngine.evaluate(contracts)` produce señales determinísticas.
2. Para los contratos que disparan ≥1 regla, `llm_router.analyze_contract`
   añade contexto cualitativo (resumen, hipótesis adicionales, citas).
3. Se persiste `OpacityScore` en Postgres con timestamp y versión del
   modelo, para trazabilidad.

### 3.3 Reporte

`reporting.report.generate(scores)` produce Markdown con:
- Resumen ejecutivo (top-N por score).
- Por cada hallazgo: id contrato, entidad, proveedor, señales activadas,
  valor estadístico (no narrativa), URL fuente en `community.secop.gov.co`.

---

## 4. Decisiones arquitectónicas (ADRs)

### ADR-001 — Qdrant como memory store, no pgvector

**Contexto.** Necesitamos búsqueda semántica sobre objetos contractuales
para detectar agrupamientos y comparar contratos similares.

**Decisión.** Usar **Qdrant** dedicado.

**Alternativas.** pgvector embebido en Postgres simplificaría la
infraestructura pero dejaría la vertical fuera del patrón engine-core de
MNC AgentOS (que ya estandarizó Qdrant en `memory-store`).

**Consecuencias.** Un servicio extra en compose. A cambio, reuso directo
de patrones de engine-core y migración futura a un Qdrant compartido entre
verticales sin refactor.

---

### ADR-002 — Claude Opus 4.7 con fallback Ollama

**Contexto.** El agente necesita razonamiento sobre lenguaje contractual y
debe poder funcionar offline para demo de jurado y para soberanía técnica
en entornos de la Veeduría sin acceso a API externas.

**Decisión.** `claude-opus-4-7` como modelo principal vía Anthropic SDK,
con fallback a `qwen3` vía Ollama local.

**Alternativas.** Sólo Claude (más simple, sin offline). Sólo local
(latencia y calidad menores en razonamiento jurídico). Híbrido pierde
simplicidad pero gana resiliencia y soberanía.

**Consecuencias.** El `LLMRouter` debe normalizar la salida de ambos
proveedores al mismo `OpacityScore`. Costo controlado: cada llamada al
LLM requiere disparo previo de al menos una regla.

---

### ADR-003 — Detección híbrida: reglas + LLM, no sólo LLM

**Contexto.** Los hallazgos serán revisados por veedores y eventualmente
por entes de control. Necesitan ser **defendibles cuantitativamente**.

**Decisión.** Capa de **reglas determinísticas** (concentración, IQR de
valor, anomalías temporales, vacíos documentales) que activa señales
discretas; el LLM enriquece con narrativa y contexto, pero **no** decide
por sí solo si algo es opaco.

**Alternativas.** Sólo LLM (caro, no auditable, alucina). Sólo reglas
(rígido, no captura matices). Híbrido es estado del arte en analítica de
contratación pública (cf. OCDS Red Flags Guide).

**Consecuencias.** El `score` se compone de: peso de cada regla activada
(determinista) + ajuste cualitativo del LLM (acotado). Cada contribución
es auditable por separado.

---

### ADR-004 — FastAPI, no Flask

**Contexto.** Necesitamos una API interna para que la CLI, el reporter y
eventuales canales (Telegram en fase 2) consuman el detection engine
de forma uniforme.

**Decisión.** **FastAPI**.

**Alternativas.** Flask (sin typing nativo, OpenAPI sólo con extensiones,
async añadido por terceros).

**Consecuencias.** Esquemas Pydantic se reutilizan entre normalización y
contratos de API sin duplicar código. Documentación OpenAPI se publica
automáticamente para auditores externos.

---

### ADR-007 — Combinación lineal regla + LLM, sin pesos aprendidos

**Contexto.** El `score` de opacidad surge de mezclar señales
determinísticas (reglas) y un ajuste cualitativo del LLM. Hay dos
caminos: pesos aprendidos sobre un dataset etiquetado, o pesos fijos
declarados.

**Decisión.** **Combinación lineal con pesos fijos**:
`score = 0.7 · rule_score + 0.3 · llm_severity_avg`. Cada componente
es trazable por separado en el `OpacityScore.rationale`.

**Alternativas.** Modelos aprendidos (XGBoost, regresión logística)
darían mejor calibración estadística pero requieren etiquetas (¿qué
veedor las produce?), introducen riesgo de data leakage y no son
defendibles ante un jurado o ente de control sin un dataset público
auditado. La auditabilidad cuantitativa pesa más que la calibración.

**Consecuencias.** Si en una sesión Anthropic está caído y el fallback
Ollama también, el motor entrega `rule_score` puro y marca
`llm_severity_avg = None` con `model_used = "rules-only"`. La cita
legal del rationale no depende del LLM.

---

### ADR-008 — Endpoint `/contest` (Pack 4 Responsiveness, 6-Pack of Care)

**Contexto.** El 6-Pack of Care (Tang & Green, Oxford 2025) define
seis dimensiones para sistemas IA de impacto público; el Pack 4
Responsiveness exige un canal explícito por el cual la persona
auditada (contratista, entidad, ciudadanía) pueda objetar la decisión
del sistema. Sin este canal el agente queda como caja negra, lo que
contradice CONSTITUTION §10 (revisión humana obligatoria) y la
regla "no acusar corrupción".

**Decisión.** Exponer un endpoint `POST /contest` que recibe
`{contract_id, reason, contestant_email, contestant_role}` y persiste
la impugnación en SQLite. **El endpoint NO modifica automáticamente
el score**: deja la impugnación en estado `received` con un SLA
declarado de 7 días, durante los cuales un revisor humano (Marlon o
Gustavo) decide `resolved_kept` o `resolved_changed` y registra
`resolution_notes`.

**Alternativas.** (a) Sin canal de impugnación → falla Pack 4.
(b) Score auto-decrece con cada impugnación → vector de gaming
trivial. (c) Buzón externo (form Google) → no auditable, no integrado
al flujo de auditoría.

**Consecuencias.** Se introduce el primer servicio HTTP en el repo
(`src/api/`), que abre puerta a futuros endpoints (`/scores`,
`/explain`). Retención SQLite local 90 días con anonimato opcional
(role `citizen` puede dejar email vacío). El acuse de recibo cita
explícitamente la frase "este sistema no decide; un humano revisa
toda impugnación en máximo 7 días hábiles".

---

### ADR-009 — Streamlit como dashboard de auditoría no-decisorio

**Contexto.** El reto de Día 2 (8-9 may 2026, Hackathon Nacional
Colombia 5.0) exige pitch de 5 min con demo en vivo. Un reporte
Markdown estático no transmite el flujo interactivo del sistema. A
la vez, AGENTS.md prohibía cualquier frontend para evitar deslizar
el alcance hacia una "app de auditoría ciudadana" cuando lo que se
entrega es un motor MIT.

**Decisión.** Habilitar **un solo dashboard Streamlit
(`streamlit_app.py`)** acotado a tres funciones: ver hallazgos sobre
un `contract_id`, ver metadata del modelo usado (Anthropic/Ollama,
latencia, costo), y ofrecer el form de impugnación que llama a
`/contest`. **El dashboard nunca cambia el score; los inputs del
usuario solo pueden consultar o impugnar.**

**Alternativas.** (a) Sin dashboard → demo D2 más débil. (b) SPA
React/Next → fuera del scope del entregable MIT, mantenimiento mayor,
desalinea el patrón engine-core. (c) Notebook Jupyter → no
demostrable a jurado no técnico.

**Consecuencias.** Se actualiza AGENTS.md para reemplazar la
prohibición genérica de "No frontend" por la regla más fina "ningún
UI puede modificar score automáticamente; los dashboards son solo
lectura + canales de impugnación". El dashboard reusa
`RuleEngine.evaluate` directamente sin pasar por API, lo que mantiene
el demo funcional aun si el servicio FastAPI está caído.

---

## 5. Ámbitos fuera de alcance (explícitos)

- **No** procesa documentos PDF anexos al contrato (fase posterior).
- **No** consulta sistemas privados de inteligencia financiera.
- **No** publica hallazgos automáticamente a redes o medios — todo
  hallazgo pasa por revisión humana antes de salir del sistema
  (ver `CONSTITUTION.md`).
- **No** procesa datos personales más allá de NIT y razón social pública.
