# Datos del atlas — fuentes, procesamiento, productos y límites

> Metodología **de datos** de todas las capas: el estrés térmico (UTCI,
> ERA5-HEAT) y las carencias energéticas (Censo 2020, ENCEVI, diseño MEDI).
> Es la referencia que un usuario del atlas necesita para interpretar lo que
> ve. Los planes con hitos están en [planes/](planes/); las decisiones con
> evidencia, en [adr/](adr/); la guía de supuestos, escalas y límites para el
> equipo de investigación, en [SUPOSICIONES.md](SUPOSICIONES.md). Estado al
> 2026-09-03.

## 0. Mapa de fuentes → productos

| fuente | qué aporta | libreta | producto |
|---|---|---|---|
| ERA5-HEAT (Copernicus C3S) | UTCI horario 0.25° | 001, 002, 003 | `data/raw/UTCI/<año>/UTCI_Mexico_<año>.nc`, `UTCI_levels_<año>.nc`, COG; STAC `utci` |
| Marco Geoestadístico 2020 (INEGI) | polígonos de estados, municipios, AGEB urbanas y rurales; puntos de localidades rurales | 004 | `data/raw/INEGI/mg_2020/` |
| ITER 2020 por AGEB y manzana urbana (INEGI, 32 archivos) | 4 componentes del MEDI por AGEB urbana; totales por municipio y estado | 005, 006, 010 | `medi_ageb_2020.parquet` (filas urbanas), `medi_mun_2020.parquet`, `medi_ent_2020.parquet` |
| ITER 2020 nacional por localidad (INEGI) | los mismos 4 componentes por localidad → AGEB rurales | 011 | `medi_ageb_2020.parquet` (filas rurales), `medi_ageb_2020_grid.parquet` (filas por localidad) |
| Cuestionario ampliado 2020, microdatos (INEGI, 32 archivos) | combustible, fogón sin chimenea, aire acondicionado por municipio, estado y localidad ≥ 50 k, con error muestral | 008 | `ampliado_{ent,mun,loc50k}_2020.parquet` |
| ENCEVI 2018 (INEGI) | calefacción y AC por estado y región climática | 009 | `encevi_ent_2018.parquet` |
| Regla climática (derivada del UTCI) | necesidad de AC / calefacción por unidad | 009 | `clima_{ageb,mun,ent}_2020.parquet`, `clima_umbrales_2020.parquet` |
| Índice MEDI (derivado) | suma ponderada de las 7 carencias en 3 niveles | 010 | columnas `medi*` en los tres productos; STAC `inegi` (007) |

Orden de ejecución: 001 → 002 → 003 (UTCI) y 004 → 005 → 006 → 011 → 008 →
009 → 010 → 007 (socioeconómico). Todo con `uv`; `data/` fuera de Git; cada
descarga deja un `SOURCE.md` con URL, fecha y hash.

## 1. Estrés térmico: UTCI de ERA5-HEAT

- **Qué es.** El UTCI (*Universal Thermal Climate Index*) es una temperatura
  equivalente que integra aire, humedad, viento y radiación. ERA5-HEAT es el
  producto de Copernicus que lo calcula a partir del reanálisis ERA5, cada
  hora, en una malla de 0.25° (~27 km).
- **Crudo (001).** Los archivos diarios se recortan a México (lon −119 a −86,
  lat 14 a 33.5) y se concatenan por año en un NetCDF horario (8 760 h). El
  archivo trae el UTCI en kelvin; se convierte a °C al clasificar. Los
  diarios de 2022 vienen recortados a 33 °N (77 filas) y los de 2023 a
  33.5 °N (79 filas): cuando se combinan años se usa la malla común. El
  tiempo está en **UTC**, no en hora local.
- **Horas por nivel (002).** Cada hora se clasifica en la escala ISB de 10
  niveles (frío extremo < −40 °C … calor extremo > 46 °C; calor fuerte =
  32–38 °C) y se cuentan las horas del año por nivel y celda:
  `hours(level, lat, lon)`. Donde el UTCI es indefinido (viento fuera del
  rango de validez de la fórmula, sobre todo mar y jets de Tehuantepec) la
  hora no se clasifica; `valid_hours` documenta cuántas horas válidas tuvo
  cada celda (mínimo 8 401 en 2023; 2 971 de 10 349 celdas tienen menos de
  8 760). En tierra el efecto es marginal.
- **Catálogo (003).** Items `utci-hourly-<año>` y `utci-levels-<año>` en la
  colección `utci`, con un COG multibanda (banda k = nivel k−1). La app
  descubre los años en el STAC.
- **Qué no es.** Un reanálisis no capta la isla de calor urbana ni el
  interior de las viviendas; describe la celda, no la calle.

## 2. Marco Geoestadístico 2020

Polígonos oficiales de la misma edición que el Censo 2020 (zip integrado,
257 MB; libreta 004): `00ent` (32), `00mun` (2 469), `00a` (63 982 AGEB
urbanas con clave de 13 y 17 469 rurales con clave de 9) y `00lpr`
(295 779 localidades rurales puntuales, cada una con la clave de su AGEB
rural). El `.prj` es WKT ESRI sin código EPSG; los parámetros son los de
**EPSG:6372** (Lambert cónica conforme, ITRF2008) y se asignan al leer.
Centroides y simplificación se calculan en 6372; los productos se escriben en
EPSG:4326 ([ADR-0003](adr/0003-crs-4326-almacenar-6372-medir.md)).

## 3. ITER por AGEB urbana: los cuatro componentes censales del MEDI

Los archivos oficiales *Principales resultados por AGEB y manzana urbana*
(uno por estado; libreta 005) traen conteos del cuestionario básico para el
**universo** de viviendas. De ahí salen, como porcentaje de viviendas:

| indicador | definición | peso MEDI |
|---|---|---|
| Sin electricidad | `VPH_S_ELEC / VIVPARH_CV` | 0.24 |
| Sin refrigerador | `(VIVPARH_CV − VPH_REFRI) / VIVPARH_CV` | 0.21 |
| Sin teléfono fijo ni celular | `VPH_SINLTC / VIVPARH_CV` | 0.08 |
| Sin radio ni televisor | `VPH_SINRTV / VIVPARH_CV` | 0.07 |

- **Denominador.** `VIVPARH_CV` = viviendas particulares habitadas *con
  características captadas*, el universo oficial de los `VPH_*`. Usar
  `VIVPAR_HAB`, como hacía el extracto entregado al equipo, produce
  porcentajes negativos ([ADR-0001](adr/0001-fuente-oficial-inegi-y-denominador.md)).
- **Claves.** `cvegeo` de 13 = `ENT(2)+MUN(3)+LOC(4)+AGEB(4)`, reconstruida
  con ceros a la izquierda; la columna concatenada del extracto los pierde en
  2 194 filas y trae una comilla espuria.
- **Unión con el marco.** 63 982 AGEB casan por clave de 13; 331 existen en
  el marco como rurales (contienen una localidad urbana) y se unen por clave
  de 9 (`ambito_mgn = rural`); ninguna queda sin polígono.
- **Asteriscos.** `*` = menos de 3 unidades. Se guardan como nulo con bandera
  (`ok | censurado | sin_viviendas`); el porcentaje es nulo si falta numerador
  o denominador. Electricidad lleva `p_sin_elec_sup`, cota superior
  `min(2, VIVPARH_CV − VPH_C_ELEC) / VIVPARH_CV` ([ADR-0002](adr/0002-asteriscos-censura.md)).
  Censura por AGEB urbana: electricidad nula en 22 053 (34 %), teléfono en
  12 663 (20 %), radio/TV en 13 248 (21 %), refrigerador en 5 888 (9 %).
- **Municipio y estado** (libretas 006 y 010) usan las filas municipio y
  entidad de los mismos archivos: totales completos, urbano + rural (la
  población suma 126 014 024); censura marginal (electricidad nula en 103
  municipios, radio/TV en 3).
- El extracto `bd_MEDI_AGEB.csv` sólo sirve de verificación cruzada: coincide
  con la fuente oficial salvo Sonora (otra columna), una fila de Baja
  California y una AGEB faltante.

## 4. ITER nacional por localidad: las AGEB rurales

[ADR-0008](adr/0008-ageb-rural-suma-localidades.md), libreta 011. El ITER
nacional publica una fila por localidad con las mismas variables. Cada
localidad rural se une por clave al punto del marco, que trae su AGEB rural;
numerador y denominador se suman por AGEB con las mismas definiciones de la
sección 3. 184 190 localidades rurales (25.7 M de personas) en 14 868 AGEB.

- Las 82 012 localidades de 1–2 viviendas (415 mil personas) sólo publican
  población; cuentan en `pobtot` pero no en el denominador (`n_loc_sin_dato`).
  En el ITER por localidad la censura es por localidad completa, no por
  indicador: toda AGEB rural con denominador tiene sus cuatro numeradores.
- 1 995 AGEB rurales tienen localidades pero ninguna con características
  captadas (`sin_viviendas`); 2 601 polígonos rurales no tienen localidad
  habitada y no aparecen.
- Las 331 AGEB mixtas conservan su fila urbana; ninguna localidad urbana se
  suma a una AGEB rural.
- Combustible, chimenea y AC se heredan del municipio (sección 5); el índice
  se calcula igual que en las urbanas.

## 5. Cuestionario ampliado 2020: combustible, chimenea y aire acondicionado

Muestra probabilística de 4 016 627 viviendas (factores que suman 34.99 M),
válida para nacional, estado, cada municipio y localidades de 50 000 o más
habitantes. Microdatos de la tabla `Viviendas_CA`, 32 zips (489 MB) con
`SOURCE.md`; libreta 008.

| indicador | definición | peso MEDI |
|---|---|---|
| Combustible ≠ gas/electricidad | `p_lena`: leña, carbón u *otro*, sobre las viviendas **que cocinan** con respuesta | 0.13 |
| Fogón sin chimenea | `p_fogon_sin_chim`: cocinan con leña/carbón sin tubo o chimenea, sobre las que cocinan | 0.13 |
| Sin aire acondicionado | `p_sin_ac`: insumo del confort térmico (sección 7) | — |

- **Estimación:** proporción ponderada por `FACTOR`; error estándar por
  linealización de Taylor con conglomerado último (`ESTRATO`, `UPM`; los
  estratos van anidados en municipio y localidad ≥ 50 k). CV publicado con la
  regla INEGI: ≤ 15 % ok, 15–30 % aviso, > 30 % poco preciso (borde rojo
  punteado en el mapa). Precisión municipal: AC ok en 99 % de los municipios;
  combustible ok 60 %, aviso 29 %, poco preciso 11 %; chimenea 52 / 30 / 18 %.
  Los estratos con una sola UPM aportan varianza cero: el CV está subestimado
  en los municipios más pequeños.
- **Verificación:** leña nacional 12.49 % (boletín 12.5 %), panel solar 0.81 %
  (0.8 %); los 32 estados coinciden con `uso_combustible.xlsx` (máximo 0.4
  puntos, Campeche, por los no especificados) y `cocina_c_chimenea.xlsx`
  (exacto). AC del Censo vs ENCEVI 2018 por estado: correlación 0.97.
- **Sin dato:** Seybaplaya (04012), Honduras de la Sierra (07125) y el
  municipio 29048 vienen completos en cobertura 3 del Censo (sin información
  de ocupantes); quedan nulos, igual que sus AGEB y su MEDI.
- **Herencia a la AGEB:** si la AGEB pertenece a una localidad de 50 k o más
  (31 248 AGEB urbanas, 67 % de la población urbana) toma la estimación de
  esa localidad; si no, la del municipio (`origen_ampliado`; todas las
  rurales). Es el mismo número repetido en todas las AGEB de la unidad: en el
  mapa se ven escalones y el panel lo avisa como "heredado".
- Extras conservados (no MEDI): sin electricidad según el ampliado, focos
  ahorradores, boiler, calentador solar, panel solar.

## 6. ENCEVI 2018: calefacción y regiones climáticas

Encuesta de consumo de energéticos en viviendas (28 953 viviendas con factor
`factor_sem`), diseñada para el nivel nacional y tres regiones climáticas
(1 cálida extrema: BC, BCS, Coahuila, Chihuahua, Durango, Nuevo León, Sinaloa,
Sonora, Tamaulipas; 2 templada; 3 tropical: Campeche, Chiapas, Guerrero,
Oaxaca, Quintana Roo, Tabasco, Veracruz, Yucatán). Por estado (~900
viviendas) sólo con cautela. Aporta `p_sin_calef` por estado y región (única
fuente de calefacción: el Censo no la pregunta), `p_sin_ac` de contraste, y
las regiones como referencia para calibrar la regla climática. Producto
`encevi_ent_2018.parquet`, libreta 009.

## 7. Regla climática y confort térmico

Definida con la malla UTCI ([ADR-0007](adr/0007-regla-climatica-utci.md),
libreta 009): una unidad **necesita AC** si su celda acumula ≥ 902 h/año en
niveles de calor fuerte o más (UTCI > 32 °C) y **calefacción** si acumula
≥ 626 h/año bajo 0 °C (promedio de los años del STAC; con sólo AGEB urbanas
eran 912 y 625). Los umbrales se calibraron a nivel estatal contra las
regiones ENCEVI (95 % de coincidencia ponderada por población) y contra los
estados con ≥ 8 % de viviendas con calefactor (88 %). Cada AGEB urbana toma
su celda; cada AGEB rural promedia las celdas de sus localidades por
población; municipio y estado ponderan por población. Necesitan AC 47.8 % de
las AGEB; calefacción 10.7 %; ambas 3.8 %; ninguna 45.3 %.

`p_sin_confort` (peso 0.14) = `p_sin_ac` donde sólo se necesita AC,
`p_sin_calef` donde sólo calefacción, la media donde ambas, 0 donde ninguna.
Limitación: la calefacción del noreste (Nuevo León, Coahuila, Tamaulipas)
responde a frentes fríos cortos que no acumulan 626 h bajo cero y no entra.

## 8. El índice MEDI

`medi = Σ wᵢ·pᵢ` en escala 0–100 ([ADR-0006](adr/0006-definicion-medi.md),
propuesto hasta que el equipo lo confirme), con los pesos de
`descriptores_MEDI.xlsx` (0.24, 0.21, 0.14, 0.13, 0.13, 0.08, 0.07), sin
renormalizar; nulo si falta un componente. Es una **intensidad promedio de
carencia**, no un porcentaje de hogares pobres (eso exigiría microdatos por
hogar de las siete carencias). Para los componentes censurados se publica el
intervalo `medi_min`–`medi_max` (censurados en 0 y en 2 viviendas): 0.38
puntos en promedio por AGEB. Resultados 2020: estados de 1.7 (CDMX) a 36.4
(Chiapas; Oaxaca 34.4, Guerrero 30.1); municipios de 0.4 a 66.6 (2 466 de
2 469); AGEB hasta 95 (71 917 de 79 181). Por AGEB combina cuatro
componentes propios y tres heredados; la leyenda lo advierte. Libreta 010.

## 9. El cruce con la malla UTCI (tabla puente)

`medi_ageb_2020_grid.parquet` tiene una fila por AGEB urbana (celda de su
centroide) y una por localidad rural (celda de su punto), con población,
denominadores, numeradores, banderas, componentes heredados e índice:
248 503 filas; 2 929 celdas con población. Al hacer clic en una celda, el
pie de página suma numerador y denominador de las unidades **no censuradas**
de esa celda para los componentes del ITER, pondera por viviendas los
heredados y el índice, y reporta unidades urbanas y rurales por separado. Es
una asignación por centroide o punto, no por área.

## 10. Cómo se pinta

- Clases por **cuantiles nacionales** (6), fijas por nivel e indicador (para
  AGEB, urbanas y rurales juntas), para que dos regiones sean comparables. Si
  más de un sexto de los valores son cero, la primera clase es exactamente
  "0". El índice se muestra en puntos, el resto en porcentaje.
- Gris = sin dato; la leyenda dice cuántas unidades. Borde rojo punteado =
  estimación del ampliado con CV > 30 %. Rurales = 45 % de la opacidad y
  trazo punteado.
- Estado y municipio se dibujan completos con geometría simplificada (500 m);
  AGEB **por ventana** a partir de zoom 10, simplificadas a medio píxel
  ([ADR-0005](adr/0005-ageb-por-ventana-vector.md)). El raster UTCI vive en un
  pane inferior; la coropleta queda siempre encima.
- El panel indica la escala en que se midió cada dato ("Escala del dato") y
  el tooltip muestra bandera, cota superior, CV y, en AGEB, ámbito, número de
  localidades y origen del ampliado.

## 11. Productos y catálogo

`data/derived/INEGI/2020/`, catalogados en `data/stac/inegi/` con la
extensión *table* y la propiedad `atlas:indicators` ([ADR-0004](adr/0004-geoparquet-y-stac-table.md)):

| archivo | filas | tamaño | contenido |
|---|---|---|---|
| `medi_ent_2020.parquet` | 32 | 12 MB | 7 componentes nativos + MEDI, geometría `00ent` |
| `medi_mun_2020.parquet` | 2 469 | 58 MB | 4 del ITER + 3 del ampliado (con CV) + confort + MEDI, geometría `00mun` |
| `medi_ageb_2020.parquet` | 79 181 | 203 MB | 64 313 urbanas + 14 868 rurales; 4 propios + 3 heredados + confort + MEDI |
| `medi_ageb_2020_grid.parquet` | 248 503 | 9 MB | tabla puente por AGEB urbana y localidad rural → celda UTCI |
| `ampliado_{ent,mun,loc50k}_2020.parquet` | 32 / 2 469 / 232 | < 1 MB | tasas, CV, calidad, n del ampliado |
| `clima_{ageb,mun,ent}_2020.parquet`, `clima_umbrales_2020.parquet` | — | < 1 MB | horas de calor/frío y necesidad climática; umbrales |
| `encevi_ent_2018.parquet` | 32 | < 1 MB | calefacción y AC de ENCEVI por estado y región |

Items STAC: `medi-ent-2020`, `medi-mun-2020`, `medi-ageb-2020`, `medi-grid-2020`
(fecha de referencia 15 de marzo de 2020; licencia: Términos de Libre Uso de
INEGI). UTCI: `utci-hourly-<año>` y `utci-levels-<año>` (licencia Copernicus).

## 12. Limitaciones conocidas

- **Temporalidad:** Censo marzo 2020, ENCEVI 2018, UTCI 2022–2023, hora UTC.
  Las capas socioeconómicas son una foto; no describen cambio social.
- **Escalas mezcladas:** por AGEB, combustible, chimenea, AC y calefacción son
  heredados (localidad ≥ 50 k, municipio o estado); el índice por AGEB tiene
  escalones. No inferir de un valor heredado la situación de una AGEB.
- **Censura:** alta en electricidad, teléfono y radio/TV por AGEB urbana;
  localidades de 1–2 viviendas excluidas de los indicadores rurales; 5 247 AGEB
  urbanas y 1 995 rurales sin viviendas con características.
- **Precisión del ampliado:** CV alto en municipios pequeños para combustible
  y chimenea; subestimado donde un estrato tiene una sola UPM.
- **Regla de frío:** no capta la calefacción del noreste.
- **Malla de 27 km:** municipios vecinos comparten celda; no hay isla de calor
  ni microclima; celdas marinas con horas válidas incompletas.
- **Polígonos rurales grandes:** el color uniforme exagera; mitigado con
  opacidad y tooltip.
- `NOM_LOC` en las filas AGEB del ITER es "Total AGEB urbana": el tooltip no
  muestra localidad en AGEB urbanas.
- **Peso de los productos:** el AGEB pesa 203 MB; la app lo lee por ventana.
- **Pendientes del equipo:** confirmar que el MEDI es suma ponderada, las
  siglas y la referencia de sus pesos, y la regla de frío
  ([SUPOSICIONES.md](SUPOSICIONES.md), §14).

## 13. Qué sigue (fuera de esta fase)

Capa bivariada clima × carencia y mejoras de visibilidad
([../PLAN-VISIBILIDAD.md](../PLAN-VISIBILIDAD.md)); versión Alkire-Foster del
índice con los microdatos del ampliado (municipio); estimación en áreas
pequeñas para bajar AC y combustible a AGEB; sumar las localidades rurales de
las 331 AGEB mixtas; una capa de localidades rurales como puntos; CONEVAL
municipal 2010/2015/2020 como serie temporal; regla de frío por rachas.
