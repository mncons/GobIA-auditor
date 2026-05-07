# Ejemplo 01 — Concentración de mercado en una entidad (OP-01 + OP-13)

> Sintético basado en patrones reales del dataset `jbjy-vk9h`. Fuentes
> SECOP II citadas son ilustrativas: **el motor solo emite hallazgos
> con `urlproceso.url` real del payload Socrata** (ver
> `src/ingestion/normalizer.py:_build_source_url`).

## Contexto

Una **entidad territorial** (denominada aquí `Alcaldía Demo`) firma 5
contratos de **mínima cuantía** en enero 2026. Cuatro de los cinco van
al **mismo proveedor** (NIT 900-000-000) y suman **$80 M** de los **$90 M**
totales adjudicados por la entidad en ese mes.

Los datos crudos llegan al motor desde:
`https://www.datos.gov.co/resource/jbjy-vk9h.json?$where=fecha_de_firma between '2026-01-01' and '2026-01-31' AND nit_entidad='890000000'`

## Reglas activadas

- **OP-01** *(top-share)* — el proveedor 900-000-000 representa
  **80%** de los contratos de la entidad (4/5).
- **OP-13** *(HHI valor)* — `Σ share² = 0.79² + 0.11² ≈ 0.63`,
  ampliamente sobre el threshold DOJ de 0.25.

## Input — POST `/contest` (impugnación tras revisar el reporte)

```bash
curl -X POST localhost:8000/contest \
  -H 'Content-Type: application/json' \
  -d '{
        "contract_id": "CO1.PCCNTR.DEMO-001",
        "reason": "El proveedor 900-000-000 corresponde a una asociación de pequeños productores locales reconocida por Decreto Municipal 015 de 2025; la concentración refleja política pública de compras locales, no captura.",
        "contestant_email": "alcaldia@demo.gov.co",
        "contestant_role": "entity"
      }'
```

## Output esperado (acuse de recibo)

```json
{
  "contest_id": 1,
  "status": "received",
  "review_eta_days": 7,
  "acknowledgment_text": "Recibimos tu impugnación. Este sistema NO decide; un humano la revisa en máximo 7 días hábiles. Te notificaremos al correo provisto. CONSTITUTION §10 — revisión humana obligatoria."
}
```

## Output esperado del motor (reporte Markdown)

```markdown
### CO1.PCCNTR.DEMO-001 — score 0.71

| Campo       | Valor                                                       |
|-------------|-------------------------------------------------------------|
| Entidad     | Alcaldía Demo                                               |
| Proveedor   | Asociación Local SAS (NIT 900-000-000)                      |
| Modalidad   | Mínima cuantía                                              |
| Valor       | $20.000.000                                                 |
| Señales     | OP-01, OP-13                                                |
| URL fuente  | community.secop.gov.co/Public/Tendering/OpportunityDetail/… |

**Rationale.** En 'Alcaldía Demo' el proveedor representa 80% de los
contratos del lote (4/5) · Mercado de 'Alcaldía Demo': HHI=0.63
(umbral 0.25). Concentrador líder 900-000-000 con 89% del valor
adjudicado.
```

## Interpretación jurídica

- **Decreto 1082 de 2015**, art. 2.2.1.1.2.1.3 — la mínima cuantía
  exige justificación de la selección y publicidad. Si la
  concentración tiene base en política pública (compras locales,
  Acuerdo de productividad), debe estar **documentada en los estudios
  previos**: la impugnación citada arriba apunta justamente a eso.
- **Ley 1150 de 2007**, art. 5 — selección objetiva. Concentración
  sostenida sin sustento documental puede contravenir la regla; con
  sustento (caso de productores locales) está cubierta.
- **Lo que el motor hace:** marca el patrón estadístico y emite la
  cita; **lo que NO hace:** afirmar irregularidad. La impugnación
  registrada vía `/contest` queda en cola para revisión humana.
