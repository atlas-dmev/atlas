# Planes ejecutados

Archivo de los planes de trabajo ya completados, en orden cronológico. Cada
uno conserva sus hitos con resultados, mediciones y decisiones tal como se
cerraron; sirven como memoria del proyecto y como material de estudio
([../TEMARIO.md](../TEMARIO.md)). La forma de proceder está en
[../METHODOLOGY.md](../METHODOLOGY.md); las decisiones con evidencia, en
[../adr/](../adr/).

| # | plan | qué construyó | estado |
|---|---|---|---|
| 01 | [Visor de estrés térmico UTCI v1](01-visor-utci-v1.md) | arquitectura del visor, app Shiny + ipyleaflet, POC de ingesta (Zarr, luego eliminado) | completado |
| 02 | [UTCI → niveles de estrés → STAC → webapp](02-utci-niveles-stac.md) | horas/año por nivel, COGs, catálogo STAC, vista de niveles, limpieza post-POC | completado (M0–M5) |
| 03 | [Capas socioeconómicas INEGI (MEDI, Censo 2020)](03-capas-inegi-medi.md) | marco geoestadístico, productos AGEB/municipal, colección STAC `inegi`, panel derecho, cruce en el clic | completado (S0–S8) + adenda |
| 04 | [MEDI completo con el Cuestionario ampliado](04-medi-ampliado.md) | ampliado 2020 con precisión, regla climática UTCI, índice MEDI en 3 niveles, nivel Estado, dispersión | completado (T0–T7); ADR-0006 pendiente de confirmación del equipo |
| 05 | [AGEB rurales](05-ageb-rural.md) | ITER nacional por localidad + puntos del marco → 14 868 AGEB rurales, tabla puente por localidad, app con ámbito | completado (R0–R6), decisiones confirmadas |
| 04 | [MEDI completo con el Cuestionario ampliado](04-medi-ampliado.md) | ampliado 2020 con precisión, regla climática UTCI, índice MEDI en 3 niveles, nivel Estado, dispersión | completado (T0–T7); ADR-0006 pendiente de confirmación del equipo |
| 05 | [AGEB rurales](05-ageb-rural.md) | ITER nacional por localidad + puntos del marco → 14 868 AGEB rurales, tabla puente por localidad, app con ámbito | completado (R0–R6), decisiones confirmadas |

Un plan nuevo se escribe en la raíz del repo mientras está activo y se
archiva aquí al cerrarse. **Activo:** [PLAN-VISIBILIDAD.md](../../PLAN-VISIBILIDAD.md)
(visibilidad conjunta del UTCI y la capa socioeconómica).
