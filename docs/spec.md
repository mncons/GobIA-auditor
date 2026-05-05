# spec.md — GobIA Auditor

> **Qué** construimos y **por qué**, desde el punto de vista del usuario.
> Este documento NO habla de stack, frameworks ni implementación
> (eso vive en `plan.md`). Si una decisión técnica entra aquí, sácala.

---

## 1. Problema

La contratación pública colombiana publica diariamente miles de
contratos en SECOP II. La revisión manual por veedurías ciudadanas,
periodistas y entes de control no escala: las señales de opacidad
(concentración por proveedor, valores fuera de rango, vacíos
documentales, modificaciones sin acta) quedan sepultadas en el
volumen.

Lo que falta no es más narrativa periodística, sino un **mecanismo
auditable de priorización**: una lista corta de contratos a revisar,
ordenada por probabilidad cuantificable de opacidad, con cita
directa a la fuente pública.

## 2. Misión

GobIA Auditor monitorea el dataset Socrata `jbjy-vk9h` de SECOP II,
aplica un conjunto de señales estadísticas y jurídicas explicables,
y produce un **reporte revisable por humanos** con hallazgos
ordenados por score, cada uno citando el `id_contrato` y la URL
pública en `community.secop.gov.co`.

## 3. No-objetivos (scope explícito de lo que NO hacemos)

- No acusa de corrupción a nadie. Sólo cuantifica opacidad estadística.
- No publica hallazgos automáticamente: todo pasa por revisión humana.
- No es asistente jurídico ni emite dictamen.
- No procesa datos personales más allá de NIT y razón social pública.
- No reemplaza la veeduría humana; la habilita.
- No es un buscador de SECOP — es un **monitor con priorización**.

## 4. Audiencias

| Audiencia                | Qué necesita                                  |
|--------------------------|-----------------------------------------------|
| Veedor ciudadano         | Lista corta de contratos sospechosos del mes  |
| Periodista de datos      | Hallazgos citables, exportables, reproducibles|
| Auditor de ente control  | Trazabilidad: qué regla, qué umbral, qué fecha|
| Jurado de la hackathon   | Demo end-to-end defendible, sin alucinaciones |

## 5. User journeys

### 5.1 Veedor — "¿qué revisar este mes?"

Ana es veedora ciudadana en una alcaldía municipal.

1. Abre el reporte mensual generado por GobIA (Markdown publicado en
   un sitio estático tras revisión humana).
2. Ve los **top 20 hallazgos** del mes ordenados por score.
3. Para cada hallazgo lee: contrato, entidad, proveedor, **señales
   activadas** (e.g. *OP-01 concentración 72%*), justificación
   cuantificada, y URL al expediente en SECOP.
4. Hace clic en la URL, contrasta el expediente, y decide si abre
   solicitud de información formal a la entidad.
5. **Éxito** = Ana presenta una solicitud formal sustentada en datos
   públicos en menos de 30 minutos, sin haber tenido que descargar
   ni clasificar contratos a mano.

### 5.2 Periodista de datos — "¿qué patrón emergente hay?"

Carlos es periodista en un medio digital.

1. Consulta el reporte y nota agrupación de hallazgos OP-10 (objeto
   repetido al mismo NIT) en una entidad.
2. Solicita al equipo MNC el **dump de scores con trazabilidad**
   (qué regla, qué peso, qué timestamp, qué versión del modelo).
3. Verifica que cada hallazgo tiene URL fuente y reproduce los
   cálculos sobre el dataset público.
4. Publica reportaje citando el método y el repositorio público de
   GobIA Auditor como referencia.
5. **Éxito** = la nota es defendible ante derecho de réplica porque
   el método es público y reproducible.

### 5.3 Auditor de ente de control — "¿es este un sistema confiable?"

Patricia es funcionaria de un ente de control.

1. Recibe una denuncia ciudadana basada en un hallazgo de GobIA.
2. Necesita verificar **antes de abrir actuación** que el método es
   sólido y no acusatorio.
3. Lee `CONSTITUTION.md`, `docs/architecture.md` y
   `docs/opacity-signals.md` del repositorio público.
4. Confirma: hay umbrales declarados, hay trazabilidad por regla,
   hay aviso explícito de que el score no es probabilidad de
   corrupción, hay URL fuente en cada hallazgo.
5. **Éxito** = Patricia decide abrir la actuación con base en la
   denuncia + el expediente original, no en el score por sí solo.

### 5.4 Jurado de la hackathon — "¿esto está vivo o es vaporware?"

Un jurado de MinTIC.

1. Pide ver el repositorio público.
2. Clona y corre `pytest -q`: tests verdes en menos de 30 segundos.
3. Corre el flujo `ingest → analyze → report` sobre fixture
   sintético: ve hallazgos disparados por OP-01 y OP-02 con
   racionalización auditable.
4. Lee README, ADRs y CONSTITUTION: verifica que el equipo NO
   sobrevende capacidades del sistema.
5. **Éxito** = el jurado ve un MVP **honesto sobre su propio
   alcance**, con backbone para crecer y con guardarriles éticos
   declarados desde el día uno.

## 6. Hipótesis a validar tras la hackathon

- H1 — Las cinco familias de señales (OP-01..05) capturan ≥80% de
  los casos que un veedor humano marcaría manualmente.
- H2 — La capa de reglas determinísticas reduce ≥10× el costo de
  inferencia LLM frente a un baseline "sólo LLM".
- H3 — La tasa de falsos positivos en OP-01 con umbral 0.4 es ≤25%
  sobre datos reales de un mes completo.
- H4 — Veedurías y periodistas adoptan el reporte si está publicado
  en sitio estático con frecuencia mensual.

## 7. Definition of Success (hackathon)

- [ ] Repo público con README claro y sin claims falsos.
- [ ] Demo end-to-end sobre fixture sintético, ejecutable en <2 min.
- [ ] Al menos 2 señales reales (OP-01, OP-02) con tests automatizados.
- [ ] Reporte Markdown ejemplo con 5–10 hallazgos sintéticos.
- [ ] Documentación que un auditor externo pueda leer en 15 minutos.
- [ ] Cero hallazgos sin URL fuente.
- [ ] Cero atribuciones de intencionalidad en el lenguaje del reporte.
