# PLAN-SOCIOECONOMICOS — capas INEGI (MEDI) en el atlas

Objetivo: incorporar al atlas los dos indicadores MEDI de mayor peso a nivel
**AGEB urbana**, Censo 2020 (ITER), como capas socioeconómicas propias con la
misma disciplina que el UTCI: producto derivado reproducible → catálogo STAC →
la app descubre y pinta. Deja el camino abierto para el resto del MEDI y para
los cruces con el estrés térmico.

| Indicador MEDI | Peso | Fórmula (columnas ITER) | Nivel | Año |
|---|---|---|---|---|
| Sin electricidad | 0.24 | `VPH_S_ELEC / VIVPARH_CV` | AGEB urbana (+ municipio) | 2020 |
| Sin refrigerador | 0.21 | `(VIVPARH_CV − VPH_REFRI) / VIVPARH_CV` | AGEB urbana (+ municipio) | 2020 |

`VIVPARH_CV` = viviendas particulares habitadas **con características captadas**,
el denominador oficial de todos los `VPH_*` (ver hallazgos).

Fuera de alcance de esta fase (anotados para después): teléfono y radio/TV
(mismo flujo, solo cambia la columna), CONEVAL municipal 2010/2015/2020, capas
estatales de combustible/chimenea y ENCEVI 2018 por región climática.

## Insumos

| Insumo | Qué es | Dónde está / de dónde sale |
|---|---|---|
| `bd_MEDI_AGEB.csv` | Extracto del ITER Censo 2020 por AGEB urbana (64 313 filas). Codificación **latin-1**. Coincide con la fuente oficial salvo en Sonora, donde su `VIVPAR_HAB` es en realidad `TVIVPAR` (viviendas particulares habitadas o no), y **no trae `VIVPARH_CV`**; se usa sólo como verificación cruzada. | `data/raw/INEGI/iter_2020/` |
| Principales resultados por AGEB y manzana urbana, Censo 2020 (32 zips, uno por estado, ~300 MB) | Fuente oficial: filas a nivel entidad, municipio, localidad, AGEB y manzana con las 230 variables del ITER, incl. `VIVPARH_CV` y `VPH_C_ELEC`. Las filas municipio son totales completos (urbano + rural). | `https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/ageb_manzana/ageb_mza_urbana_<ee>_cpv2020_csv.zip` → `data/raw/INEGI/iter_2020/ageb_manzana/` |
| ITER 2020 nacional (36 MB) | Todas las localidades y los 2 469 municipios con las mismas variables; respaldo para el municipal si algún municipio no aparece en los 32 archivos urbanos. | `https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/iter/iter_00_cpv2020_csv.zip` |
| `descriptores_MEDI.xlsx` | Diseño MEDI: indicadores, pesos, fuente y escala. | `data/raw/INEGI/tabulados/` |
| Marco Geoestadístico 2020 integrado | Polígonos oficiales del Censo 2020: AGEB (`00a`: 63 982 urbanas + 17 469 rurales), municipios (`00mun`), entidades (`00ent`), localidades. Shapefiles, CRS Lambert cónica conforme México ITRF2008 (EPSG:6372; el `.prj` no trae el código, asignarlo al leer). | `https://www.inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/geografia/marcogeo/889463807469/mg_2020_integrado.zip` (257 MB, feb-2021; ficha `upc=889463807469`) |
| Descriptor ITER AGEB 2020 | Semántica de columnas y del asterisco. | `https://www.inegi.org.mx/app/scitel/doc/descriptor/fd_agebmza_urbana_cpv2020.pdf` |

El ITER 2020 y este Marco Geoestadístico son de la **misma edición censal**
(el marco es el que INEGI usó para publicar el Censo 2020), así que las claves
de 13 caracteres `ENT(2)+MUN(3)+LOC(4)+AGEB(4)` deben casar 1:1.

## Hallazgos del CSV que condicionan el diseño

- **La columna `CVE_AGEB` no es confiable**: 2 194 filas perdieron ceros a la
  izquierda en la parte AGEB (p. ej. `02001013945` en vez de `0200101390045`).
  Las columnas por separado sí están completas (`ENTIDAD` 2, `MUN` 3, `LOC` 4)
  salvo `AGEB`, que hay que rellenar a 4 con `zfill`. Con la clave reconstruida
  las 64 313 filas son únicas: **no hay AGEB duplicadas**.
- **Asteriscos** (`*`) = dato omitido por confidencialidad en AGEB con pocas
  viviendas (INEGI lo usa para valores 0, 1 o 2; confirmar en el descriptor).
  Conteo: `VIVPAR_HAB` 3 645, `VPH_S_ELEC` 19 550, `VPH_REFRI` 3 417.
  El indicador de electricidad es el más afectado (casi 1 de cada 3 AGEB).
- **El denominador correcto es `VIVPARH_CV`, no `VIVPAR_HAB`.** En el ITER
  oficial `VPH_REFRI > VIVPAR_HAB` en 161 de 480 AGEB de Aguascalientes (14 943
  en todo el extracto), porque los `VPH_*` se calculan sobre las viviendas con
  características captadas (`VIVPARH_CV ≥ VIVPAR_HAB`). `VPH_REFRI ≤ VIVPARH_CV`
  siempre. El extracto no trae `VIVPARH_CV`, por eso S2 reconstruye el producto
  desde los 32 archivos oficiales. Refrigerador se calcula por complemento porque
  INEGI publica "con", no "sin".
- **Asterisco = menos de 3 unidades** (0, 1 o 2), confirmado en el descriptor
  oficial; `POBTOT`, `VIVTOT` y `TVIVHAB` nunca se censuran. Con `VIVPARH_CV` como
  denominador la censura del denominador casi desaparece (1 de 480 en Ags).
- Solo hay AGEB **urbanas**; suman 100.3 M de personas. Lo rural queda cubierto
  únicamente vía el agregado municipal.

## Flujo de datos

```
data/raw/INEGI/mg_2020/mg_2020_integrado.zip          ← descarga (004)
   │  004_INEGI_MGN_download.ipynb (descarga, verifica, extrae 00a/00mun/00ent)
   ▼
data/raw/INEGI/mg_2020/conjunto_de_datos/{00a,00mun,00ent}.shp
data/raw/INEGI/iter_2020/ageb_manzana/*.zip            ← 32 archivos oficiales (005 los baja)
data/raw/INEGI/iter_2020/bd_MEDI_AGEB.csv              ← extracto provisto (verificación)
   │  005_MEDI_ageb.ipynb (descarga, filas AGEB, claves, asteriscos, indicadores,
   │                       join con el marco, centroides en 6372, escritura en 4326)
   │  006_MEDI_mun.ipynb  (filas municipio oficiales, join con 00mun, tabla puente
   │                       AGEB → celda UTCI)
   ▼
data/derived/INEGI/2020/medi_ageb_2020.parquet         ← GeoParquet AGEB
data/derived/INEGI/2020/medi_mun_2020.parquet          ← GeoParquet municipal
data/derived/INEGI/2020/medi_ageb_2020_grid.parquet    ← AGEB → celda UTCI (sin geometría)
   │  007_STAC_inegi.ipynb (colección + items + validación)
   ▼
data/stac/inegi/                                       ← la app lee de aquí
```

## Formato de los productos derivados

`medi_ageb_2020.parquet` (GeoParquet, EPSG:4326, una fila por AGEB urbana):

| columna | tipo | nota |
|---|---|---|
| `cvegeo` | str(13) | clave reconstruida; llave con el marco |
| `cve_ent`, `cve_mun`, `cve_loc`, `cve_ageb` | str | partes |
| `nom_ent`, `nom_mun` | str | para tooltips |
| `nom_loc`, `ambito_mgn` | str | localidad; si el polígono vino de la capa urbana o rural del marco |
| `pobtot`, `vivpar_hab`, `vivparh_cv`, `vph_c_elec`, `vph_s_elec`, `vph_refri`, `vph_sinrtv`, `vph_sinltc` | Int64 (nullable) | conteos crudos; `*` → nulo |
| `vph_sin_refri` | Int64 | `vivparh_cv − vph_refri` |
| `p_sin_elec`, `p_sin_refri` | float | porcentaje 0–100 sobre `vivparh_cv`; nulo si falta numerador o denominador |
| `p_sin_elec_sup` | float | cota superior cuando `vph_s_elec` está censurado: `min(2, vivparh_cv − vph_c_elec) / vivparh_cv` |
| `flag_elec`, `flag_refri` | str | `ok`, `censurado`, `sin_viviendas` |
| `cent_lon`, `cent_lat` | float | centroide calculado en EPSG:6372 y llevado a 4326 (insumo de la tabla puente) |
| `geometry` | polygon | reproyectada desde EPSG:6372 |

`medi_mun_2020.parquet`: misma estructura por municipio (`cvegeo` de 5),
tomada de las **filas municipio oficiales** (totales completos, urbano + rural,
sin censura relevante), no de la suma de AGEB. Más `n_ageb` para contexto.

`medi_ageb_2020_grid.parquet`: `cvegeo`, `lat_c`, `lon_c` (centro de la
celda ERA5 de 0.25° que contiene el centroide del AGEB) más los conteos
(`pobtot`, `vivparh_cv`, `vph_s_elec`, `vph_c_elec`, `vph_refri`,
`vph_sin_refri`) y banderas, para que el resumen de una celda no requiera
abrir el GeoParquet. Es la tabla puente para los cruces con el UTCI; se
calcula una vez y no depende del año UTCI.

## STAC

Nueva colección `inegi` bajo el catálogo raíz `atlas`, hermana de `utci`:

```
data/stac/inegi/
├─ collection.json                 # extent México, licencia INEGI (términos de libre uso), keywords
├─ medi-ageb-2020/medi-ageb-2020.json
├─ medi-mun-2020/medi-mun-2020.json
└─ medi-grid-2020/medi-grid-2020.json
```

- `datetime` de los items: fecha censal de referencia (2020-03-15); además
  `start/end_datetime` del levantamiento (2020-03-02 → 2020-03-27).
- Assets por ruta relativa a `data/derived/`, igual que UTCI cataloga sin duplicar.
- Extensión **table** de STAC para declarar las columnas y su descripción
  (así la app sabe qué indicadores trae un item sin hardcodearlos).
- Propiedades propias: `atlas:indicators` = lista de
  `{id, label, column, weight_medi, numerator, denominator}` para los dos
  indicadores; es lo que llena el selector del panel derecho.
- Patrón de id `medi-<nivel>-<año>`; `atlas/stac.py` gana `medi_items()` y
  `available_medi_years()` con la misma lógica de descubrimiento por regex que
  `levels_items()`.

## Integración en la app

Principio: el panel izquierdo sigue mandando sobre el UTCI; el **panel derecho**
(hoy placeholder `socioeconomic_panel`) controla la capa socioeconómica.

Controles del panel derecho:

1. Indicador (`Sin electricidad`, `Sin refrigerador`), poblado desde `atlas:indicators`.
2. Nivel (`Municipio`, `AGEB`).
3. Año (solo 2020 por ahora, pero descubierto en el STAC).
4. Opacidad y leyenda propia (clases por cuantiles o cortes fijos; el color no
   debe competir con la rampa del nivel UTCI: usar una rampa neutra, p. ej. viridis/grises).

Render, en dos escalas porque 64 k polígonos nacionales no caben en un `GeoJSON`
de ipyleaflet:

- **Municipio**: coropleta nacional con `ipyleaflet.GeoJSON` de los 2 469
  polígonos simplificados (tolerancia ~500 m; objetivo < 3 MB). Se dibuja siempre.
- **AGEB**: coropleta cargada **por ventana** (bbox del mapa) cuando el zoom es
  ≥ 11; lectura filtrada del GeoParquet por bbox (columna bbox de GeoParquet),
  simplificación a medio píxel, reemplazando la capa al mover el mapa. Si el
  zoom es menor se muestra el municipal y un aviso "acércate para ver AGEB".
- Alternativas anotadas: rasterizar la ventana a PNG (si el vector pesara), o
  mostrar sólo las AGEB del municipio pulsado (más simple, sin navegación
  continua). Ninguna hizo falta en la medición de S6.

Cruce con el UTCI (lo que justifica meter estas capas en este atlas):

- Al hacer clic en una celda, el pie de página muestra además del histograma
  de horas: viviendas, % sin electricidad y % sin refrigerador de las AGEB cuyo
  centroide cae en esa celda (vía `medi_ageb_2020_grid.parquet`, sin geometría,
  respuesta instantánea).
- Base para una vista posterior "horas en nivel X vs % sin refrigerador"
  (dispersión por AGEB o municipio), fuera de esta fase.

Módulos nuevos en `src/atlas/`:

- `socio.py`: abrir productos MEDI vía STAC, listar indicadores, filtrar por
  bbox, agregar por celda UTCI.
- `choropleth.py`: GeoDataFrame + columna → `GeoJSON` estilizado + items de
  leyenda (análogo a `render.py` para raster).
- `components/`: `socio_panel()` sustituye al placeholder; `socio_server()`
  junto a `map_server()` compartiendo el mismo `base_map()` y el clic.

Dependencias a agregar con `uv add`: `geopandas`, `pyogrio`, `shapely`,
`pyarrow`, `mapclassify` (clases de la leyenda). `openpyxl` solo como dev si se
leen los xlsx desde libretas.

## Hitos

- [x] **S0 — Reordenar datos y dependencias.** `data/inegi/` movido a
  `data/raw/INEGI/{iter_2020,tabulados,encevi_2018}/` (el descriptor MEDI
  renombrado a `descriptores_MEDI.xlsx`); creado `data/derived/`; agregados
  `geopandas`, `pyogrio`, `shapely`, `pyarrow`, `mapclassify` (y `openpyxl` como
  dev); `config.py` gana `DERIVED_DIR` y `derived_dir(tipo, anio)`.
  *Hallazgo:* `data/` **no** está ignorado por Git desde el commit `81d66a3`
  (`.gitignore` tiene `#data/`), y los 365 diarios de 2022 están versionados
  (193 MB). Los nuevos derivados quedarían versionados salvo que se decida lo
  contrario (ver decisión 6).
- [x] **S1 — Descarga del marco (004).** `004_INEGI_MGN_download.ipynb` baja
  `mg_2020_integrado.zip` (reanudable), comprueba tamaño y SHA-256, extrae
  `00a`, `00mun`, `00ent` y los catálogos txt/csv, verifica las capas y escribe
  `data/raw/INEGI/mg_2020/SOURCE.md`. *Hallazgos:* (1) el `.prj` es WKT ESRI
  sin código: `to_epsg()` da None aunque los parámetros son exactamente los de
  EPSG:6372; 005 debe asignarlo con `set_crs`. (2) `00a` trae 63 982 AGEB
  urbanas (clave 13) **y** 17 469 rurales (clave 9, `Ambito=Rural`); filtrar
  por `Ambito`. (3) Cruce con el ITER: 63 982 filas casan con una AGEB urbana
  por clave de 13 y las **331 restantes existen en el marco como AGEB
  rurales** (clave de 9 `ENT+MUN+AGEB`; 1.08 M de personas, 251 k viviendas,
  p. ej. Centro y Huimanguillo en Tabasco). Ninguna queda sin polígono. S2 une
  primero por clave de 13 y después por clave de 9 contra las rurales, y
  limpia una comilla en `AGEB` (`'0030`).
- [x] **S2 — Producto AGEB (005).** `005_MEDI_ageb.ipynb` baja los 32
  archivos oficiales (247 MB, idempotente), toma las filas AGEB (64 313),
  reconstruye claves, `*` → nulo con banderas, indicadores sobre `VIVPARH_CV`,
  verifica contra el extracto, une con `00a` (63 982 por clave 13 + 331 por
  clave 9, 0 sin polígono), centroides en 6372 y escribe
  `data/derived/INEGI/2020/medi_ageb_2020.parquet` (74.5 MB, 64 313 × 26,
  EPSG:4326, con bbox por fila). *Verificación:* porcentajes en [0, 100];
  fila a fila contra el extracto coinciden `POBTOT`, `VPH_S_ELEC`, `VPH_REFRI`,
  `VPH_SINRTV`, `VPH_SINLTC` al 100 % salvo una AGEB de BC
  (`0200100010030`, la fila con comilla trae valores de otra AGEB) y
  `VIVPAR_HAB` en Sonora (el extracto puso `TVIVPAR`); el extracto además
  omite 1 AGEB oficial. *Censura resultante:* `p_sin_elec` nulo en 22 053 AGEB
  (34 %; 16 806 censuradas + 5 247 sin viviendas con características),
  `p_sin_refri` nulo en 5 888 (9 %). Suma `VIVPARH_CV` = 28 452 496.
- [x] **S3 — Producto municipal y puente a la malla (006).**
  `006_MEDI_mun.ipynb` toma las filas municipio de los 32 archivos oficiales
  (2 469, población sumada = 126 014 024, sin necesidad del ITER nacional),
  aplica la misma regla de asteriscos e indicadores, une con `00mun` y escribe
  `medi_mun_2020.parquet` (57.5 MB, geometría a resolución completa; la
  simplificación para la app se decide en S5). Censura municipal: sólo
  `VPH_S_ELEC` en 103 municipios; refrigerador completo. Escribe además
  `medi_ageb_2020_grid.parquet` (1.1 MB, sin geometría) con la celda 0.25°
  de cada AGEB y los conteos para resumir un clic sin abrir el GeoParquet:
  64 313 AGEB caen dentro de la malla, ocupan 1 381 de 10 349 celdas (máx
  1 398 AGEB en la celda del centro de CDMX).
- [x] **S4 — STAC (007).** `007_STAC_inegi.ipynb` abre el catálogo
  existente, reemplaza la colección `inegi` y registra `medi-ageb-2020`,
  `medi-mun-2020` y `medi-grid-2020` con extensión table (columnas con tipo y
  descripción, `row_count`, `primary_geometry`), `atlas:indicators`,
  `atlas:level`, fuente y libreta de origen; licencia `other` con link a los
  Términos de Libre Uso de INEGI; validado con `pystac` (incluida la
  extensión) y con ida y vuelta. La libreta 003 ahora **reutiliza** el
  catálogo y sólo reemplaza `utci` (verificado: `inegi` sobrevive a un rerun
  de 003). `atlas/stac.py` gana `medi_items`, `available_medi_years`,
  `medi_indicators`, `medi_path`, `read_medi` (con `columns` y `bbox`),
  `open_medi_grid` y `medi_at`. README actualizado.
- [x] **S5 — Capa municipal en la app.** Nuevo `src/atlas/choropleth.py`
  (análogo de `render.py` para vectores): geometría municipal simplificada al
  vuelo y cacheada (500 m en EPSG:6372, precisión 1e-4°; ~1.2 s una vez,
  GeoJSON de 3.4 MB), clases por cuantiles nacionales fijos (6, viridis),
  nulos en gris. `components/panels.py`: `socio_panel()` sustituye al
  placeholder (mostrar/ocultar, indicador y año desde el STAC, opacidad,
  leyenda, tooltip por hover). `components/servers.py`: `socio_server()`
  monta la capa `GeoJSON` sobre el mismo `base_map` y la reemplaza al cambiar
  indicador/opacidad; el raster UTCI pasa a un pane propio (z=350) para que
  la coropleta quede siempre encima aunque se cambie nivel o año.
  *Verificación en Chromium headless (playwright):* raster y coropleta
  visibles a los 2.5 s de cargar la página (incluye arranque de Shiny);
  cambio de indicador en 0.3 s conservando zoom; cambio de nivel UTCI no
  tapa la coropleta; hover muestra municipio, estado, valor, población y
  viviendas; apagar/encender y opacidad funcionan.
- [x] **S6 — Capa AGEB por ventana.** Selector de nivel (municipio | AGEB
  urbana) en el panel derecho. En modo AGEB, `socio_server` observa `bounds`
  y `zoom` del mapa (ipyleaflet los emite al terminar cada movimiento, sin
  necesidad de *debounce*) y a partir de `AGEB_ZOOM_MIN = 11` lee sólo las
  AGEB de la ventana (`read_medi(..., bbox=)`, ~0.03 s), las simplifica a
  medio píxel del zoom actual en EPSG:6372 y las reemplaza como `GeoJSON`;
  por debajo del umbral muestra el municipal con aviso. Clases por cuantiles
  nacionales sobre el producto AGEB, con clase "0 %" aparte cuando más de 1/6
  de los valores son cero (electricidad). Tope de seguridad de 8 000 AGEB por
  ventana. *Medición (viewport 1500×900):* CDMX zoom 10 = 6 609 AGEB / 4.3 MB /
  0.5 s; zoom 11 = 4 289 / 2.9 MB / 0.3 s; zoom 12 = 2 262 / 1.6 MB / 0.1 s;
  Mérida zoom 11 = 991 / 1.3 MB. *Verificación en Chromium:* zoom a Mérida
  dibuja 488 AGEB al instante, arrastrar 300 px recarga la ventana (39 AGEB)
  en < 2.6 s, hover muestra AGEB, municipio, valor y población; cambiar
  indicador conserva la ventana; alejar vuelve al municipal. Se eligió
  **vector** (hover y nitidez) y no PNG. *Limitación:* `nom_loc` en las filas
  AGEB del ITER es "Total AGEB urbana", así que el tooltip no muestra localidad.
  *Alternativa anotada (no implementada):* mostrar las AGEB del municipio
  sobre el que se hace clic; más simple pero sin navegación continua.
- [x] **S7 — Cruce en el clic.** El pie de página tiene ahora dos columnas:
  el histograma de horas/nivel y `celda_medi`, el resumen MEDI de la celda
  pulsada vía `stac.medi_at` (tabla puente, sin abrir el GeoParquet): AGEB
  urbanas, población, y por indicador el porcentaje agregado (numerador y
  denominador sumados sobre las AGEB no censuradas) con el número de AGEB con
  dato y el peso MEDI. `map_server` devuelve `(base_map, clic)` y
  `socio_server` recibe el clic. *Verificación en Chromium:* CDMX
  (19.50, −99.25): 1 391 AGEB, 5.18 M hab., 0.02 % sin electricidad, 5.40 %
  sin refrigerador; Hermosillo (29.00, −111.00): 399 AGEB, 568 k hab., 0.30 %
  y 2.37 %; desierto de Sonora (30.50, −113.00): sin AGEB, mensaje explícito.
  Respuesta ~1.5 s incluyendo el histograma.
- [x] **S8 — Documentación y cierre.** README (pipeline, catálogo,
  arquitectura, estructura). Nuevo `docs/DATOS.md` (metodología de
  datos: fuentes, reglas, cruce con el UTCI, limitaciones). Cinco ADR con
  evidencia en `docs/adr/` (fuente y denominador, asteriscos, CRS, GeoParquet +
  STAC table, AGEB por ventana). Temario por ítems ampliado con C5, A11, A12,
  B11 y B12. `PLAN.md` y `docs/PLAN.md` enlazan a este plan;
  `docs/METHODOLOGY.md` apunta a los ADR. (Archivado después en `docs/planes/`.)

## Pasos que no estaban en la lista original y por qué

- **Reordenar `data/`** (S0): `data/inegi/` rompía la convención
  `data/raw/<TIPO>/<AÑO>/`; conviene arreglarlo antes de que las libretas
  fijen rutas.
- **Reconstrucción de claves y política de asteriscos** (S2): sin esto el join
  con el marco falla en 2 194 filas (más 331 que sólo existen como AGEB rural) y el indicador de electricidad queda
  indefinido en un tercio de las AGEB sin que nadie lo note.
- **Reproyección** (S2): el marco viene en EPSG:6372; la app y la malla UTCI
  trabajan en 4326.
- **Tabla puente AGEB → celda UTCI** (S3): es lo que convierte "una capa más"
  en un cruce con el estrés térmico, y es barato calcularlo junto al producto.
- **Estrategia de render en dos escalas** (S5–S6): la app hoy solo pinta un
  raster nacional de 10 k celdas; 62 k polígonos requieren decidir cómo se
  sirven antes de escribir UI.
- **Registro de procedencia** (S1): fecha de descarga, URL y hash del zip, y
  licencia INEGI en la colección STAC.

## Decisiones a confirmar

1. **Ubicación de derivados**: este plan propone `data/derived/INEGI/2020/`
   (el UTCI dejó sus derivados en `data/raw/` por la decisión 1 de `02-utci-niveles-stac.md`).
   Si prefieres mantener todo en `raw/`, el STAC funciona igual.
2. ~~Asteriscos en el agregado municipal~~ — resuelto: el municipal sale de
   las filas municipio oficiales, sin agregar AGEB. En la capa AGEB el
   censurado queda nulo y electricidad lleva cota superior `p_sin_elec_sup`.
3. ~~Umbral de zoom para AGEB y vector vs PNG~~ — resuelto en S6: zoom ≥ 11,
   vector. Bajar a 10 es cambiar `AGEB_ZOOM_MIN` (CDMX pasaría de 2.9 a 4.3 MB
   por ventana).
4. ~~Clases de la leyenda~~ — implementado en S5: cuantiles nacionales fijos
   (6 clases) calculados al cargar sobre el producto municipal; no hizo falta
   guardarlos en el STAC. Para AGEB (S6) se calcularán igual sobre el producto
   nacional AGEB.
5. **Colección STAC**: `inegi` (por fuente) vs `socioeconomico` (por tema, para
   alojar también CONEVAL). Propuesta: `inegi` ahora y una colección por fuente
   después; el tema se lleva en keywords.
6. ~~`data/` en Git~~ — resuelto (2026-09-02): `data/` y `*.zarr/` vuelven al
   `.gitignore`. Los 365 diarios de 2022 siguen en el índice hasta que se
   corra `git rm -r --cached data/` en un commit propio.

## Estado al cierre (2026-09-02)

Todos los hitos S0–S8 completados. Nada de esta fase está versionado aún:
libretas 004–007, `src/atlas/choropleth.py`, cambios en `stac.py`, `config.py`,
`components/`, `app/`, README, docs y este plan. `data/` vuelve a estar
ignorado; los 365 diarios de 2022 siguen en el índice hasta `git rm -r --cached data/`.

Para reproducir desde cero: `uv sync`, luego libretas 001→003 (UTCI) y
004→007 (INEGI), y `uv run shiny run app/app.py`.

## Adenda (2026-09-02): los cuatro indicadores del ITER

Tras el cierre se activaron los dos MEDI restantes que el ITER mide por AGEB,
**sin teléfono fijo ni celular** (`VPH_SINLTC`, 0.08) y **sin radio ni
televisor** (`VPH_SINRTV`, 0.07): porcentajes y banderas en 005 y 006, columnas
en la tabla puente, y declaración en 007. Sin cambios en la app. Censura AGEB:
teléfono nulo en 12 663 (20 %), radio/TV en 13 248 (21 %); municipal: radio/TV
censurado en 3 municipios, teléfono completo. Los tres componentes restantes
del MEDI (confort térmico, combustible, chimenea) no existen en el ITER por AGEB.
