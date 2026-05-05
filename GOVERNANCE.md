# GOVERNANCE.md — GobIA Auditor

> Una página. Si crece, audita y borra.
> Inspirado en el modelo open-core descrito en
> opencoreventures.com, adaptado al contexto de **MNC Consultoría**.

---

## 1. Licencia permanente

Este repositorio se publica bajo **licencia MIT** y **permanecerá MIT
de forma irrevocable**. No habrá relicensing. No habrá conmutación a
SSPL, BUSL, "source-available" ni ninguna otra licencia restrictiva
en el futuro.

Cualquier copia descargada hoy tiene MIT garantizada para siempre por
los términos del propio MIT; este documento sólo lo reafirma para
evitar ambigüedades comerciales.

## 2. Separación open-core / propietario

MNC Consultoría opera un modelo **open-core con frontera explícita**:

| Plano        | Vive en                                        | Licencia   |
|--------------|------------------------------------------------|------------|
| Engine + patrón de agente | repos públicos como **éste** y `mnc-agent-os` | **MIT**    |
| Verticales propietarios   | repos privados separados (AbiChat, Workoholic, FundingRadar)  | propietaria|
| Hosting / soporte / integraciones premium | producto comercial de MNC | comercial  |
| Datasets curados con consentimiento de aportantes | almacenes separados | licencias propias |

La frontera es física (repos distintos), no contractual: el engine no
contiene `if PRO_LICENSE` ni gating runtime. Cualquier persona u
organización puede operar este engine sin relación comercial con MNC.

## 3. Contribuciones

- Las contribuciones a este repo se aceptan **bajo MIT**, vía Pull
  Request, con DCO sign-off (`Signed-off-by:` en el commit) que
  declara que el contribuidor tiene derecho a aportar el código.
- Las contribuciones de la comunidad **nunca se moverán** a un repo
  cerrado de MNC. Si una idea aportada inspira una feature
  propietaria, esa feature se reescribe internamente y vive en repo
  privado: el código aportado sigue íntegro y MIT en este repo.
- No se exige cesión de copyright a MNC. El contribuidor mantiene su
  copyright, otorgando licencia MIT a la comunidad y a MNC en igualdad.
- Para el alcance de qué cambios se aceptan ver `CONTRIBUTING.md`
  (pendiente de redactar — TODO post-hackathon).

## 4. No relicensing — declaración explícita

MNC Consultoría se compromete a:

1. **No** cambiar la licencia de este repo a una más restrictiva.
2. **No** introducir cláusulas de uso comercial restringido en
   versiones futuras.
3. **No** mover features que ya estén en un release MIT a un repo
   cerrado pagado (la dirección permitida es la inversa: features
   internas que migran a MIT y se publican aquí).
4. **No** insertar dependencias propietarias ocultas. Toda dependencia
   debe estar en `requirements.txt`, ser OSS y auditable.

## 5. Marcas

"MNC Consultoría", "MNC AgentOS", "GobIA Auditor", "FundingRadar",
"AbiChat" y "Workoholic" son **marcas de MNC Consultoría**. La
licencia MIT cubre el código, **no** las marcas: forks pueden usar el
código pero deben renombrar su distribución para evitar confusión con
los productos comerciales de MNC.

## 6. Toma de decisiones

- **Capitán del proyecto:** Marlon Naranjo (`info@mnconsultoria.org`).
  Tiene la última palabra sobre scope del engine.
- **Equipo Veedores Amplificados** durante hackathon: ver
  `docs/team.md`.
- Decisiones arquitectónicas se documentan como **ADRs** numerados en
  `docs/architecture.md`. Toda decisión que cambie scope o
  dependencias requiere ADR.
- Conflictos no resueltos por consenso técnico se escalan al capitán,
  cuya decisión queda registrada como ADR.

## 7. Si MNC desaparece

Si MNC Consultoría dejara de existir o de mantener este repo:

- La licencia MIT permanece. Cualquier persona puede forkear y
  continuar el desarrollo bajo su propio nombre.
- Se desaconseja seguir usando la marca "GobIA Auditor" o
  "MNC AgentOS" en forks activos: renómbrese para evitar confusión.
- Los verticales propietarios y datasets curados **no** entran en este
  régimen — su disposición depende de los acuerdos comerciales con
  los respectivos clientes y aportantes.

## 8. Versión y revisión

**Versión actual:** v0.1
**Última revisión:** 2026-05-05
**Próxima revisión obligatoria:** 2026-08-05 (≤90 días).
**Aprobado por:** Marlon Naranjo (capitán, MNC Consultoría).
