# Catálogo inicial de señales de opacidad

> Cada señal es **opacidad estadística**, no acusación de corrupción. Es
> condición necesaria que el hallazgo cite el `id_contrato` y la URL en
> `community.secop.gov.co`. Severidad estimada (baja / media / alta) es
> indicativa para priorización; no es ranking de gravedad jurídica.

| ID    | Nombre                                | Severidad |
|-------|---------------------------------------|-----------|
| OP-01 | Concentración por proveedor           | media     |
| OP-02 | Valor fuera de IQR sectorial          | media     |
| OP-03 | Plazo atípico vs. modalidad           | media     |
| OP-04 | Adjudicación en feriado               | alta      |
| OP-05 | Adjudicación en último día hábil      | media     |
| OP-06 | Modificación contractual sin acta     | alta      |
| OP-07 | Garantía sin firma digital válida     | alta      |
| OP-08 | Póliza con vigencia inconsistente     | alta      |
| OP-09 | Vacío documental obligatorio          | alta      |
| OP-10 | Repetición de objeto a mismo NIT      | media     |
| OP-11 | Fragmentación bajo umbral de modalidad| alta      |
| OP-12 | Sector vs. CIIU del contratista       | baja      |
| OP-13 | HHI de mercado por entidad            | alta      |

---

## OP-01 — Concentración por proveedor

**Descripción.** Una entidad adjudica al mismo proveedor más del *p* % de
sus contratos en un período rolling (e.g. 30/90 días).

**Hipótesis.** Concentración alta puede indicar dependencia operativa
genuina o, eventualmente, captura institucional. La señal sólo señala el
fenómeno; el contraste lo hace el veedor humano.

**Fuente del dato.** `nit_del_proveedor_adjudicado`, `nombre_entidad`,
`fecha_de_firma`.

**Severidad estimada.** Media.

---

## OP-02 — Valor fuera del rango intercuartílico sectorial

**Descripción.** El `valor_del_contrato` cae fuera de `[Q1 - 1.5·IQR,
Q3 + 1.5·IQR]` para el conjunto sector × modalidad × ventana temporal.

**Hipótesis.** Outliers de precio merecen revisión documental.

**Fuente del dato.** `valor_del_contrato`, `modalidad_de_contratacion`,
`rama` / `entidad_rama`, `fecha_de_firma`.

**Severidad estimada.** Media.

---

## OP-03 — Plazo atípico vs. modalidad

**Descripción.** El plazo de ejecución (`fecha_de_fin - fecha_de_inicio`)
está fuera del IQR para la modalidad correspondiente.

**Hipótesis.** Plazos atípicamente cortos pueden indicar premura
sospechosa; atípicamente largos, dilución.

**Fuente del dato.** `fecha_de_inicio_del_contrato`,
`fecha_de_fin_del_contrato`, `modalidad_de_contratacion`.

**Severidad estimada.** Media.

---

## OP-04 — Adjudicación en feriado

**Descripción.** `fecha_de_firma` cae en domingo o feriado nacional
colombiano.

**Hipótesis.** Adjudicaciones en feriados son raras; merecen revisión
del expediente.

**Fuente del dato.** `fecha_de_firma` cruzada con calendario de feriados
oficial.

**Severidad estimada.** Alta (tasa base muy baja → señal informativa
alta cuando dispara).

---

## OP-05 — Adjudicación en último día hábil del mes

**Descripción.** `fecha_de_firma` coincide con el último día hábil del
mes y la entidad muestra patrón recurrente.

**Hipótesis.** Pueden corresponder a cierres presupuestales legítimos o
a empuje artificial de ejecución; se reporta sólo cuando excede tasa base.

**Fuente del dato.** `fecha_de_firma` por entidad, agrupado mensualmente.

**Severidad estimada.** Media.

---

## OP-06 — Modificación contractual sin acta justificativa

**Descripción.** Existen modificaciones (otrosíes) registradas sin acta
justificativa anexa o con anexo vacío.

**Hipótesis.** Toda modificación legalmente requiere justificación
escrita (aporte jurídico de Gustavo Puerta).

**Fuente del dato.** Tabla de modificaciones y documentos anexos
asociados al contrato.

**Severidad estimada.** Alta.

---

## OP-07 — Garantía sin firma digital válida

**Descripción.** La garantía única o pólizas asociadas no presentan
firma digital con cadena de confianza válida en el período exigido.

**Hipótesis.** La firma digital de garantías es exigida por la
normatividad; su ausencia o invalidez es opacidad documental
inmediatamente verificable.

**Fuente del dato.** Anexos de garantía firmados; validación
fuera-de-banda contra ECDC reconocida.

**Severidad estimada.** Alta. *Aporte jurídico: Gustavo Puerta.*

---

## OP-08 — Póliza con vigencia inconsistente con plazo contractual

**Descripción.** Vigencia de la póliza no cubre la totalidad del plazo
contractual + período de liquidación exigido por modalidad.

**Hipótesis.** Inconsistencia de cobertura es vacío material que expone
al patrimonio público.

**Fuente del dato.** Datos de pólizas anexadas vs. fechas del contrato.

**Severidad estimada.** Alta. *Aporte jurídico: Gustavo Puerta.*

---

## OP-09 — Vacío documental obligatorio

**Descripción.** Ausencia de documentos exigidos por la modalidad
(estudios previos, análisis del sector, certificación de
disponibilidad presupuestal, etc.).

**Hipótesis.** Toda modalidad tiene un *checklist* documental mínimo
auditable.

**Fuente del dato.** Inventario de documentos en la URL pública del
contrato vs. checklist por modalidad.

**Severidad estimada.** Alta.

---

## OP-10 — Repetición de objeto contractual al mismo NIT

**Descripción.** Múltiples contratos a un mismo NIT con objeto
contractual semánticamente equivalente en ventana corta.

**Hipótesis.** Repetición puede ocultar fraccionamiento o ser
contratación seriada legítima; el LLM evalúa la similitud semántica del
objeto y la regla evalúa la frecuencia.

**Fuente del dato.** `objeto_del_contrato`, `nit_del_proveedor_adjudicado`,
`fecha_de_firma`.

**Severidad estimada.** Media.

---

## OP-11 — Fragmentación bajo umbral de modalidad

**Descripción.** Varios contratos individuales con la misma entidad y
contratista cuyos valores, agregados, superan el umbral que requeriría
una modalidad de contratación más exigente.

**Hipótesis.** Es un patrón clásico de elusión de licitación; aparece en
la OCDS Red Flags Guide.

**Fuente del dato.** `valor_del_contrato`, `modalidad_de_contratacion`,
`nit_del_proveedor_adjudicado`, ventana temporal.

**Severidad estimada.** Alta.

---

## OP-12 — Sector contratado vs. CIIU del contratista

**Descripción.** El objeto contractual no se corresponde con la actividad
económica registrada del contratista (CIIU principal).

**Hipótesis.** Disonancia entre objeto y actividad del contratista
merece revisión; puede ser legítima (subcontratación) o señal de
testaferrato.

**Fuente del dato.** Objeto contractual y CIIU del proveedor (RUES).

**Severidad estimada.** Baja (alta tasa de falsos positivos esperada).

---

## OP-13 — HHI de mercado por entidad

**Descripción.** Índice Herfindahl-Hirschman calculado como
`Σ (share_i)²` donde `share_i` es la fracción del valor adjudicado
total de la entidad capturada por el proveedor *i*. Threshold default
**0.25** (convención DOJ U.S. para "highly concentrated market").

**Hipótesis.** Complementa OP-01 (top-share por número de contratos)
con la perspectiva de **valor**: una entidad puede repartir
**número** de contratos a varios proveedores pero concentrar el
**dinero** en uno. HHI captura esa dinámica.

**Fuente del dato.** `valor_del_contrato`, `nit_del_proveedor_adjudicado`,
`nombre_entidad`. Se evalúan lotes con ≥3 contratos por entidad.

**Severidad estimada.** Alta. *Función pura:* `hhi_concentration` en
`src/detection/rules.py`. *Inspiración:* OCDS Red Flags Guide §3.2,
Klemperer (2002), DOJ Horizontal Merger Guidelines.
