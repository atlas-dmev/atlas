# Datos INEGI en el atlas — qué son, cómo se procesan y qué limitaciones tienen

> Metodología **de datos** de las capas socioeconómicas (Censo 2020, diseño
> MEDI). El plan e hitos están en [planes/03-capas-inegi-medi.md](planes/03-capas-inegi-medi.md);
> las decisiones con evidencia, en [adr/](adr/). Este documento es la
> referencia que un usuario del atlas necesita para interpretar lo que ve.
> Para el equipo de investigación hay además una guía de supuestos, escalas y
> límites en [SUPOSICIONES.md](SUPOSICIONES.md).

## 1. Qué se muestra

Los cuatro indicadores del diseño MEDI (índice de carencia energética del
hogar) que el Censo mide en el universo, como **porcentaje de viviendas**:

| indicador | definición | peso MEDI | fuente |
|---|---|---|---|
| Sin electricidad | `VPH_S_ELEC / VIVPARH_CV` | 0.24 | Censo 2020, ITER por AGEB, municipio y estado |
| Sin refrigerador | `(VIVPARH_CV − VPH_REFRI) / VIVPARH_CV` | 0.21 | Censo 2020, ITER por AGEB y municipio |
| Sin teléfono fijo ni celular | `VPH_SINLTC / VIVPARH_CV` | 0.08 | Censo 2020, ITER por AGEB y municipio |
| Sin radio ni televisor | `VPH_SINRTV / VIVPARH_CV` | 0.07 | Censo 2020, ITER por AGEB y municipio |

Los otros tres componentes del MEDI vienen del **Cuestionario ampliado 2020**
(muestra probabilística, válida por municipio y localidad ≥ 50 k) y de la
ENCEVI 2018, y se heredan hacia la AGEB (sección 8):

| indicador | definición | peso MEDI | fuente |
|---|---|---|---|
| Combustible ≠ gas/electricidad | `p_lena`: leña, carbón u otro, sobre las viviendas que cocinan | 0.13 | Ampliado, pregunta 8 |
| Fogón sin chimenea | `p_fogon_sin_chim`: cocinan con leña/carbón sin chimenea, sobre las que cocinan | 0.13 | Ampliado, pregunta 9 |
| Sin confort térmico | `p_sin_confort`: sin AC donde hace calor / sin calefacción donde hace frío (regla UTCI) | 0.14 | AC: ampliado p. 15; calefacción: ENCEVI 2018; clima: UTCI |
| **Índice MEDI** | `medi` = Σ wᵢ·pᵢ (0–100), con `medi_min`/`medi_max` por censura | 1.00 | todo lo anterior |

`VIVPARH_CV` = *viviendas particulares habitadas con características captadas*.
Es el universo sobre el que INEGI calcula todos los `VPH_*`; usar `VIVPAR_HAB`
produce porcentajes negativos ([ADR-0001](adr/0001-fuente-oficial-inegi-y-denominador.md)).

Dos niveles:

- **Municipio** (2 469): totales oficiales del municipio, urbano + rural. La
  población suma 126 014 024, la nacional de 2020.
- **AGEB urbana** (64 313): localidades de 2 500 habitantes o más (o
  cabeceras municipales), del ITER por AGEB.
- **AGEB rural** (14 868 con datos, de 17 469 en el marco): construidas
  sumando por clave las localidades rurales del ITER nacional (sección 12).

## 2. Fuentes y procedencia

| insumo | dónde | libreta |
|---|---|---|
| Marco Geoestadístico 2020 integrado (`00a` AGEB, `00mun`, `00ent`) | `data/raw/INEGI/mg_2020/` + `SOURCE.md` (URL, fecha, SHA-256) | 004 |
| Principales resultados por AGEB y manzana urbana, 32 zips | `data/raw/INEGI/iter_2020/ageb_manzana/` | 005 |
| Extracto `bd_MEDI_AGEB.csv` (verificación cruzada) | `data/raw/INEGI/iter_2020/` | 005 |

Licencia: Términos de Libre Uso de la Información del INEGI.

## 3. Reglas de procesamiento

1. **Claves.** `cvegeo` de 13 = `ENT(2)+MUN(3)+LOC(4)+AGEB(4)`, reconstruida
   desde las partes con relleno de ceros; la columna concatenada del extracto
   pierde ceros en 2 194 filas. Se limpia una comilla espuria (`'0030`).
2. **Unión con el marco.** Primero por clave de 13 contra las AGEB urbanas del
   marco (63 982); las 331 restantes existen como AGEB *rurales* (clave de 9,
   sin localidad) y se unen así (`ambito_mgn = rural`). Ninguna queda sin polígono.
3. **Asteriscos.** `*` = menos de 3 unidades. Se guardan como nulo con bandera
   (`ok | censurado | sin_viviendas`); el porcentaje es nulo si falta numerador
   o denominador. Electricidad lleva `p_sin_elec_sup`, cota superior
   `min(2, VIVPARH_CV − VPH_C_ELEC) / VIVPARH_CV` ([ADR-0002](adr/0002-asteriscos-censura.md)).
4. **CRS.** El marco viene en Lambert (EPSG:6372, sin código en el `.prj`).
   Centroides y simplificación se calculan en 6372; los productos se escriben
   en EPSG:4326 ([ADR-0003](adr/0003-crs-4326-almacenar-6372-medir.md)).
5. **Productos** en `data/derived/INEGI/2020/`, catalogados en `data/stac/inegi/`
   ([ADR-0004](adr/0004-geoparquet-y-stac-table.md)): `medi_ageb_2020.parquet`,
   `medi_mun_2020.parquet`, `medi_ageb_2020_grid.parquet` (tabla puente).

## 4. El cruce con el UTCI

Cada AGEB se asigna a la celda de 0.25° de la malla ERA5 que contiene su
centroide (`lat_c`, `lon_c`, centros en múltiplos de 0.25°). Al hacer clic en
una celda, el pie de página suma numerador y denominador de las AGEB **no
censuradas** de esa celda y reporta cuántas se usaron. Es una asignación por
centroide, no por área: una AGEB grande que cruza dos celdas cuenta entera en
una. A 0.25° (~27 km) el efecto es marginal para AGEB urbanas (< 1 km típicas).

## 5. Cómo se pinta

- Clases por **cuantiles nacionales** (6), fijas por nivel e indicador, para
  que dos ciudades sean comparables. Si más de un sexto de los valores son
  cero (electricidad por AGEB), la primera clase es exactamente "0 %".
- Gris = sin dato (censurado o sin viviendas con características); la leyenda
  dice cuántos.
- AGEB **por ventana** a partir de zoom 11, simplificadas a medio píxel
  ([ADR-0005](adr/0005-ageb-por-ventana-vector.md)).

## 6. Limitaciones conocidas

- Censura: `p_sin_elec` nulo en 22 053 AGEB (34 %); `p_sin_telef` en 12 663
  (20 %); `p_sin_rtv` en 13 248 (21 %); `p_sin_refri` en 5 888 (9 %). En
  municipios: electricidad nula en 103, radio/TV en 3, teléfono y refrigerador
  completos.
- `NOM_LOC` en las filas AGEB del ITER es "Total AGEB urbana": no hay nombre de
  localidad en el tooltip.
- Sólo AGEB urbanas: los huecos entre ciudades no son "sin carencia", son "sin
  AGEB".
- Temporalidad: Censo 2020 (referencia 15 de marzo de 2020) frente a UTCI anual
  2022–2023. Las capas son estáticas hasta el próximo censo.
- El extracto `bd_MEDI_AGEB.csv` tiene errores propios (Sonora, una fila de BC,
  una AGEB faltante); no se usa para el producto.

## 8. Cuestionario ampliado, precisión y herencia

- **Fuente:** microdatos de la tabla `Viviendas_CA` (4 016 627 viviendas en
  muestra, factores que suman 34.99 M), 32 zips en
  `data/raw/INEGI/censo_ampliado_2020/` con `SOURCE.md`. Libreta 008.
- **Estimación:** proporción ponderada por `FACTOR`; error estándar por
  linealización de Taylor con conglomerado último (`ESTRATO`, `UPM`); CV
  publicado con la regla INEGI: ≤ 15 % ok, 15–30 % aviso, > 30 % poco preciso
  (borde rojo punteado en el mapa). Precisión municipal: AC ok en 99 % de los
  municipios; combustible ok 60 %, aviso 29 %, poco preciso 11 %; chimenea
  52 / 30 / 18 %.
- **Verificación:** leña nacional 12.49 % (boletín 12.5 %), panel solar 0.81 %
  (0.8 %); los 32 estados coinciden con los tabulados `uso_combustible.xlsx`
  (diferencia máxima 0.4 puntos, Campeche, por el tratamiento de los no
  especificados) y `cocina_c_chimenea.xlsx` (exacto). AC del Censo vs ENCEVI
  2018 por estado: correlación 0.97.
- **Sin dato:** Seybaplaya (04012), Honduras de la Sierra (07125) y el
  municipio 29048 vienen completos en cobertura 3 del Censo (sin información
  de ocupantes); quedan nulos, igual que sus 19 AGEB y su MEDI.
- **Herencia a la AGEB:** si la AGEB pertenece a una localidad de 50 k o más
  (31 248 AGEB, 49 %, 67 % de la población urbana) toma la estimación de esa
  localidad; si no, la del municipio (`origen_ampliado`). Es el mismo número
  repetido en todas las AGEB de la unidad: en el mapa se ven escalones y el
  panel lo avisa como "heredado".

## 9. Regla climática y confort térmico

Definida con la malla UTCI del atlas ([ADR-0007](adr/0007-regla-climatica-utci.md),
libreta 009): una unidad necesita AC si su celda acumula ≥ 912 h/año en
niveles de calor fuerte o más (UTCI > 32 °C) y calefacción si acumula
≥ 625 h/año bajo 0 °C (promedio de los años del STAC). Los umbrales se
calibraron contra las regiones ENCEVI (95 % de coincidencia estatal) y el uso
de calefactor (88 %). Necesitan AC 46 % de las AGEB; calefacción 10 %; ambas 3 %.
Limitación: la calefacción del noreste (Nuevo León, Coahuila, Tamaulipas)
responde a frentes fríos cortos y no entra con esta regla.

## 10. El índice MEDI

`medi = Σ wᵢ·pᵢ` en escala 0–100 ([ADR-0006](adr/0006-definicion-medi.md)),
sin renormalizar pesos. Para los componentes censurados (asterisco INEGI) se
publica el intervalo `medi_min` (censurados en 0) – `medi_max` (censurados en
su cota de 2 viviendas): en AGEB el intervalo mide 0.46 puntos en promedio y
sólo 5.2 % de las AGEB cambiarían de clase entre un extremo y otro. Resultados
2020: estados de 1.7 (CDMX) a 36.4 (Chiapas), seguido de Oaxaca 34.4 y
Guerrero 30.1; municipios de 0.4 a 66.3; AGEB hasta 90. Por AGEB el índice
combina cuatro componentes propios y tres heredados; la leyenda lo advierte.

## 12. AGEB rurales

[ADR-0008](adr/0008-ageb-rural-suma-localidades.md), libreta 011. Cada
localidad rural del ITER nacional (una fila con las 230 variables) se une por
clave al punto del marco (`00lpr`), que trae la AGEB rural a la que pertenece;
numerador y denominador se suman por AGEB con las mismas definiciones que lo
urbano. 184 190 localidades rurales (25.7 M de personas) en 14 868 AGEB.

- Las 82 012 localidades de 1–2 viviendas (415 mil personas) sólo publican
  población; cuentan en `pobtot` pero no en el denominador (`n_loc_sin_dato`).
- 1 995 AGEB rurales tienen localidades pero ninguna con características
  captadas (`sin_viviendas`); 2 601 polígonos rurales no tienen localidad
  habitada y no aparecen.
- Las 331 AGEB mixtas (urbanas en el ITER, rurales en el marco) conservan su
  fila urbana; ninguna localidad urbana se suma a una AGEB rural.
- Combustible, chimenea y AC se heredan del municipio; el índice se calcula
  igual que en las urbanas.
- La **tabla puente** tiene ahora una fila por AGEB urbana y una por localidad
  rural (`unidad`), cada una con su celda UTCI: 2 929 celdas con población
  (antes 1 381). El resumen por celda reporta urbano y rural por separado.
- En el mapa las rurales van con menos opacidad y trazo punteado, porque un
  polígono de cientos de km² con color uniforme exagera; el tooltip dice
  cuántas localidades tiene y cuántas quedaron sin indicadores. La capa AGEB
  se activa desde zoom 10.

## 13. Qué sigue (fuera de esta fase)

Versión Alkire-Foster del índice con los microdatos del ampliado (municipio),
estimación en áreas pequeñas para bajar AC y combustible a AGEB, sumar las localidades rurales de las 331 AGEB mixtas, CONEVAL
municipal 2010/2015/2020 como serie temporal, y una regla de frío por rachas
que capture la calefacción del noreste.
