# Ejemplo 02 — Oferente único en convocatoria abierta (señal conceptual)

> Esta señal no está implementada como regla automática en
> `src/detection/rules.py` aún (queda como `TODO[MEDIA]` para
> formalización con Jaime Páez post-hackathon). El ejemplo describe
> qué dato ataca y qué reporte produciría.

## Contexto

Un **proceso de selección abreviada por subasta inversa** publicado
por una entidad nacional recibe **una sola oferta válida**. Esto **no
es ilegal**: la Ley 1150 de 2007, art. 2 numeral 4, lit. a, prevé
expresamente la posibilidad de continuar el proceso aun con un solo
oferente (o adjudicar al único habilitado). Pero **es información
auditable** — si una entidad concentra una fracción anómala de
procesos con oferente único, merece revisión documental.

## Datos atacados

- `proceso_de_compra` (nivel proceso, no contrato).
- Tabla de ofertas / habilitados (no expuesta directamente en
  `jbjy-vk9h`; requiere consultar el dataset complementario
  `p7at-bg7v` o el portal del proceso vía `urlproceso.url`).
- Tasa base por modalidad y entidad para cuantificar "anomalía".

## Regla propuesta (no implementada)

`OP-14 OferenteUnicoFrecuente` — entidad cuya fracción mensual de
procesos con un solo oferente excede 2σ del promedio histórico de
entidades pares (mismo orden, modalidad). Severidad **media**.

## Input — POST `/contest` (anticipado, contestable por el contratista)

```bash
curl -X POST localhost:8000/contest \
  -H 'Content-Type: application/json' \
  -d '{
        "contract_id": "CO1.PCCNTR.DEMO-002",
        "reason": "El proceso fue declarado oferente único porque solo nuestra empresa cumple con la certificación ISO 14001 exigida en los estudios previos; la exigencia está documentada y es proporcional al objeto contratual.",
        "contestant_email": "contratos@demo-sas.com.co",
        "contestant_role": "contractor"
      }'
```

## Output esperado del motor (reporte Markdown)

```markdown
### CO1.PCCNTR.DEMO-002 — score 0.55

| Campo       | Valor                                                       |
|-------------|-------------------------------------------------------------|
| Entidad     | Entidad Nacional Demo                                       |
| Proveedor   | Demo SAS (NIT 900-111-222)                                  |
| Modalidad   | Selección abreviada — subasta inversa                       |
| Valor       | $1.250.000.000                                              |
| Señales     | OP-14 (oferente único frecuente — propuesta)                |
| URL fuente  | community.secop.gov.co/Public/Tendering/OpportunityDetail/… |

**Rationale.** La entidad reporta 6 procesos con oferente único en el
mes (2.4σ sobre la media de entidades pares). El motor sugiere
revisión documental de los estudios previos para confirmar la
proporcionalidad de las exigencias.
```

## Interpretación jurídica

- **Ley 1150 de 2007**, art. 2 numeral 4 lit. a — admite continuar
  el proceso con un único oferente habilitado.
- **Decreto 1082 de 2015**, art. 2.2.1.1.1.6.1 — los estudios y
  documentos previos justifican la modalidad y los requisitos
  habilitantes.
- **Riesgo a auditar:** si la exigencia habilitante (ISO, capacidad
  financiera, experiencia) **fue diseñada a la medida** del único
  oferente, podría configurar **direccionamiento** (delito tipificado
  art. 408 C.P. – Violación al régimen legal o constitucional de
  inhabilidades e incompatibilidades, en concurso eventual con cohecho).
- **Lo que el motor hace:** flagear el patrón estadístico y proveer
  el `urlproceso.url` para que el veedor descargue los estudios
  previos. **No imputa direccionamiento**.
