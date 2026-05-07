# GobIA Auditor — Detección de Opacidad en SECOP II

Agente de IA que monitorea contratos públicos publicados en SECOP II y señala
patrones de **opacidad estadística** auditables — no acusa de corrupción, sólo
cuantifica anomalías y deja la decisión a un humano.

Reto **GobIA Auditor** de la **Hackathon Nacional Colombia 5.0** (MinTIC,
Universidad Distrital Francisco José de Caldas, TEVEANDINA), edición 2026.

---

## Equipo — Veedores Amplificados

- **Marlon Naranjo** *(Capitán, MNC Consultoría)* — Inteligencia de negocio y
  agentes de IA. Autor del patrón **MNC AgentOS** (engine-core MIT) y del
  precedente **FundingRadar** sobre datasets del Estado.
- **Gustavo Puerta** *(Dominio jurídico-contractual)* — Contratación pública,
  garantías, firma digital y régimen sancionatorio. Define qué califica como
  vacío documental jurídicamente relevante.
- **Jaime Cárdenas** *(Infraestructura)* — Linux, Kubernetes, Veeam y Ansible.
  Responsable de despliegue, persistencia y operación del agente.
- **Jaime Páez** *(Investigador Senior, Minciencias — grupo VIRTUS)* —
  Aprendizaje automático, recuperación aumentada y análisis de datos públicos.
  Diseña las señales estadísticas y su validación cuantitativa.

---

## Hipótesis — señales de opacidad

GobIA Auditor parte de seis familias de señales públicamente justificables:

1. **Concentración de adjudicaciones por proveedor** dentro de una entidad.
2. **Plazos atípicos** vs. la media del sector / modalidad de contratación.
3. **Valores fuera del rango intercuartílico** del sector y modalidad.
4. **Vacíos documentales** (garantías, pólizas, actas obligatorias).
5. **Modificaciones contractuales posteriores** sin acta justificativa.
6. **Patrones temporales sospechosos**: adjudicaciones en feriados o último
   día hábil del mes.

El catálogo expandido (10–12 señales) está en
[`docs/opacity-signals.md`](docs/opacity-signals.md).

---

## Arquitectura

```
+--------------+   +-----------+   +--------------+   +----------------+
|  SECOP II    |-->| Ingestor  |-->| Normalizador |-->|  Memory Store  |
| (datos.gov)  |   | (httpx)   |   | (Pydantic)   |   |    (Qdrant)    |
+--------------+   +-----------+   +--------------+   +----------------+
                                                              |
                                                              v
                                           +-------------------------------+
                                           |   Detection Engine            |
                                           |   reglas + LLM Router         |
                                           |   (Claude Opus 4.7 / Ollama)  |
                                           +-------------------------------+
                                                              |
                                                              v
                                                     +------------------+
                                                     |     Reporter     |
                                                     | Markdown + cita  |
                                                     | a community.secop|
                                                     +------------------+
```

Detalles, contratos entre componentes y ADRs en
[`docs/architecture.md`](docs/architecture.md).

---

## Stack

- **Python 3.11**
- **FastAPI** para la API interna (typing nativo y OpenAPI)
- **httpx** asíncrono para SECOP II
- **Qdrant** como memory store vectorial
- **PostgreSQL** para metadatos y trazabilidad de hallazgos
- **Anthropic SDK** con `claude-opus-4-7` como modelo principal
- **Ollama** local con `qwen3` como fallback (soberanía técnica + demo offline)
- **Docker Compose** para orquestación
- **pytest** + **ruff** en CI

---

## Sobre MNC AgentOS

GobIA Auditor es la **cuarta aplicación del patrón "monitor autónomo sobre
datasets del Estado"** que MNC ha venido desarrollando. El precedente directo
es **FundingRadar**, monitor sobre Minciencias, iNNpulsa y SENA. Este repo
aplica el mismo patrón a **SECOP II** y se alinea con `engine-core` del
monorepo MNC AgentOS:

- `channel-adapters` — esta vertical expone CLI y FastAPI; canal Telegram en
  fase posterior.
- `llm-router` — selección Opus 4.7 / Ollama con criterio de costo y
  determinismo (ver ADR-002 y ADR-003).
- `memory-store` — Qdrant compartido (ver ADR-001).
- `agent-scheduler` — pendiente; el monitoreo continuo se ejecuta hoy con
  cron simple y migrará al scheduler de engine-core.

---

## Estructura

```
gobia-auditor/
├── README.md
├── LICENSE
├── AGENTS.md
├── CONSTITUTION.md
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── pyproject.toml
├── .env.example
├── docs/
│   ├── architecture.md
│   ├── opacity-signals.md
│   ├── team.md
│   └── sprint-log-2026-05-04.md
├── src/
│   ├── config.py
│   ├── main.py
│   ├── api/                # FastAPI: /healthz + /contest (ADR-008)
│   ├── ingestion/
│   ├── detection/
│   ├── storage/            # qdrant_store + contest_store (SQLite)
│   └── reporting/
├── tests/
│   ├── test_smoke.py
│   └── fixtures/
└── .github/workflows/ci.yml
```

---

## Cómo correr

```bash
# 1. Clonar y entrar
git clone <repo-url> gobia-auditor && cd gobia-auditor

# 2. Variables de entorno
cp .env.example .env
# editar ANTHROPIC_API_KEY, OLLAMA_BASE_URL, etc.

# 3. Dependencias (entorno local de desarrollo)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 4. Tests de humo
pytest -q

# 5. CLI (skeleton)
python -m src.main ingest  --date-from 2026-01-01 --date-to 2026-01-31
python -m src.main analyze --strategy rules+llm
python -m src.main report  --format md --out reports/2026-01.md

# 6. Stack completo con Docker
docker compose up -d qdrant postgres
docker compose run --rm app python -m src.main ingest
```

> **Estado actual:** scaffold ejecutable. La ingesta real contra SECOP II y
> el routing efectivo del LLM son stubs documentados; las dos reglas
> estadísticas (concentración por proveedor e IQR de valor) sí son reales.
> Ver `docs/sprint-log-2026-05-04.md` para el plan overnight.

---

## API HTTP — endpoints disponibles

```bash
uvicorn src.api.main:app --port 8000
```

- `GET /healthz` — liveness check.
- `POST /contest` — registra una **impugnación** sobre un hallazgo
  (Pack 4 Responsiveness del 6-Pack of Care, Tang & Green Oxford 2025;
  ver ADR-008). El sistema **no modifica** el score automáticamente:
  un revisor humano resuelve cada caso en máximo 7 días hábiles
  (CONSTITUTION §10).
- `GET /contest/{id}` y `GET /contest?contract_id=...` — consulta de
  impugnaciones existentes.

Ejemplo:

```bash
curl -X POST localhost:8000/contest \
  -H 'Content-Type: application/json' \
  -d '{
        "contract_id": "CO1.PCCNTR.123456",
        "reason": "El score parece inflado por outlier sectorial sin contexto.",
        "contestant_email": "vee@dor.org",
        "contestant_role": "veedor"
      }'
```

---

## Modelo open-core

Este engine es **MIT y permanece MIT**. Cualquiera puede:
- Auto-hospedar para uso personal o comercial
- Forkearlo, modificarlo, redistribuirlo
- Construir verticales propios encima sin pagar nada a MNC

**Lo que MNC vende (no está aquí):**
- Verticales propietarios (AbiChat, Workoholic, FundingRadar) — código cerrado
- Hosting gestionado para clientes que no quieren operar infra
- Soporte humano, integraciones premium (WhatsApp Business API oficial,
  cámaras, wearables), paneles de administración, white-label institucional
- Datasets curados (ej. español colombiano de adulto mayor) bajo
  licencias separadas con consentimiento explícito de aportantes

**Compromiso explícito:**
- El engine MIT nunca se "downgradea" a closed-source. Si MNC desaparece,
  el engine sigue siendo libre (CC0 sería redundante con MIT).
- No se inyectan dependencias propietarias ocultas. Todas las deps son OSS.
- Las features que la comunidad contribuya al engine no se mueven a
  versión paga. Lo paga vive en repos privados separados, nunca en este.

Ver `CONTRIBUTING.md` para cómo contribuir y qué se acepta.

---

## Licencia

MIT. Ver [`LICENSE`](LICENSE).
