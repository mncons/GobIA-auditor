# Ejemplo 03 — Adición contractual >50% (OP-06 cuantitativa, Art. 40 Ley 80)

## Contexto

Un contrato de **interventoría** firmado en febrero 2026 por valor
inicial de **$2.500.000.000** acumula **dos otrosíes** durante la
ejecución: el primero por **$800 M** (32%), el segundo por **$600 M**
(24%). Total adicionado: **$1.400.000.000 = 56% del valor inicial**.

`fetch_contract` retorna el contrato y un endpoint complementario
(p.ej. `dataset complementario de modificaciones`) entrega:

```json
{
  "contract_id": "CO1.PCCNTR.DEMO-003",
  "initial_value": 2500000000,
  "additions": [800000000, 600000000]
}
```

## Función pura invocada

```python
from src.detection.rules import modification_excess

modification_excess(
    {"initial_value": 2_500_000_000, "additions": [800_000_000, 600_000_000]}
)
```

Resultado:

```json
{
  "initial_value": 2500000000.0,
  "addition_total": 1400000000.0,
  "addition_count": 2,
  "addition_pct": 0.56,
  "exceeds_50pct": true,
  "exceeds_count_threshold": false
}
```

## Input — POST `/contest`

```bash
curl -X POST localhost:8000/contest \
  -H 'Content-Type: application/json' \
  -d '{
        "contract_id": "CO1.PCCNTR.DEMO-003",
        "reason": "Las adiciones obedecen a hechos sobrevinientes documentados (cambio de alcance solicitado por la entidad y mayor cantidad de obra ejecutada por causas no imputables al contratista). Los soportes técnicos y actas de modificación están publicados en SECOP.",
        "contestant_email": "interventoria@demo-firm.co",
        "contestant_role": "contractor"
      }'
```

## Output esperado del motor (reporte Markdown)

```markdown
### CO1.PCCNTR.DEMO-003 — score 0.78

| Campo       | Valor                                                       |
|-------------|-------------------------------------------------------------|
| Entidad     | Entidad Nacional Demo                                       |
| Proveedor   | Interventoría Demo SAS                                      |
| Modalidad   | Concurso de méritos                                         |
| Valor       | $2.500.000.000 (+ $1.400.000.000 en otrosíes)               |
| Señales     | OP-06 (adición acumulada 56% > 50%)                         |
| URL fuente  | community.secop.gov.co/Public/Tendering/OpportunityDetail/… |

**Rationale.** Adición acumulada de $1.400 M (56% del valor inicial)
con 2 otrosíes registrados. Supera el umbral del Art. 40 parágrafo
de la Ley 80 de 1993. Requiere revisión de actas justificativas.
```

## Interpretación jurídica

- **Ley 80 de 1993**, art. 40, parágrafo — *"Los contratos no podrán
  adicionarse en más del cincuenta por ciento (50%) de su valor
  inicial, expresado éste en salarios mínimos legales mensuales"*.
- Cuando la adición supera el 50%, no es **automáticamente nula**:
  - La regla aplica salvo que el contrato esté regido por un régimen
    excepcional (Ley 1150 art. 2, numeral 2 lit. h, etc.).
  - Existen jurisprudencias del Consejo de Estado que matizan el
    cómputo cuando el contrato es de tracto sucesivo o cuando hay
    obras adicionales no previstas.
- **Lo que el motor hace:** alertar el patrón cuantitativo y
  proveer la cita normativa. **No declara nulidad ni cuantifica
  perjuicio fiscal** — eso es competencia de Contraloría
  General / Procuraduría / juez competente.
- **Acción recomendada para el veedor:** descargar las actas de
  modificación en `urlproceso.url` y verificar (a) justificación
  técnica, (b) cumplimiento del trámite contractual, (c) si el
  contrato está bajo régimen general o excepcional.
