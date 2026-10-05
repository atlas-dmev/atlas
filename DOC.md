# atlas — cómo está construida la webapp

Documento técnico para quien va a **mantener o extender** el atlas: cómo fluye
un dato desde la fuente (ERA5-HEAT, INEGI, ENCEVI) hasta el mapa, qué contrato
une al pipeline con la app y qué hay que tocar para **agregar datos nuevos**,
ya sean climáticos (ERA) o socio-territoriales.

Complementa, no repite:

- [README.md](README.md): puesta en marcha y resumen.
- [docs/DATOS.md](docs/DATOS.md): fuentes, definiciones y límites de cada dato.
- [docs/SUPOSICIONES.md](docs/SUPOSICIONES.md): supuestos metodológicos (para el equipo de investigación).
- [docs/adr/](docs/adr/): el porqué de cada decisión no trivial.

---

## 1. Vista general

```
 FUENTES                    PIPELINE (notebooks/)            CONTRATO              APP
 ───────                    ─────────────────────            ────────              ───
 ERA5-HEAT diarios ──► 001 ─► 002 ─► 003 ──────────┐
                                                   ├──► data/stac/ ──► src/atlas/ ──► components/ + app/app.py
 INEGI / ENCEVI ─────► 004 ─► 005 ─► 006 ─► 011    │    catalog.json    (stac, render,   (Shiny + ipyleaflet)
                        ─► 008 ─► 009 ─► 010 ─► 007┘    utci/ inegi/     choropleth,
                                                                         plots)
                          escriben en data/raw/ y data/derived/
```

Tres capas, cada una sólo conoce a la siguiente:

1. **Pipeline** (libretas Jupyter en `notebooks/`): descarga, limpia, calcula y
   escribe archivos en `data/raw/` y `data/derived/`; al final registra lo
   producido en el **catálogo STAC** (`data/stac/`).
2. **Paquete `atlas`** (`src/atlas/`, instalable, sin Shiny): lee el catálogo,
   abre los productos y los convierte en cosas pintables (PNG, GeoJSON,
   figuras matplotlib).
3. **App** (`components/` + `app/app.py`, Shiny): UI, estado reactivo y mapa.

### Principios que sostienen el diseño

| principio | consecuencia práctica |
|---|---|
| **El STAC es el contrato** entre pipeline y app | La app nunca construye rutas a mano: pregunta al catálogo qué años, niveles e indicadores existen. Agregar datos casi siempre = producir el archivo + registrarlo en el STAC. |
| **El STAC cataloga, no duplica** | Los assets apuntan por ruta relativa a `data/raw/` y `data/derived/`. Mover `data/` completo no rompe nada. |
| **Cada libreta es dueña de su colección** | 003 reemplaza sólo `utci`; 007 reemplaza sólo `inegi`. Se pueden regenerar por separado. |
| **La UI no hardcodea indicadores** | Etiquetas, columnas, unidades, banderas y pesos viajan en la propiedad `atlas:indicators` de cada item STAC. |
| **Datos fuera de Git** | `data/` está en `.gitignore`. Todo es reproducible desde las libretas; cada descarga deja `SOURCE.md` (URL, fecha, hash). |
| **Almacenar en 4326, medir en 6372** | Productos en EPSG:4326; áreas, centroides y simplificación en EPSG:6372 ([ADR-0003](docs/adr/0003-crs-4326-almacenar-6372-medir.md)). |

---

## 2. Organización de `data/`

`src/atlas/config.py` es el único lugar que resuelve dónde viven los datos
(`DATA_DIR`, sobreescribible con la variable de entorno `ATLAS_DATA_DIR`).

```
data/
├─ raw/                         # tal como se descarga (o casi)
│  ├─ UTCI/<año>/               # UTCI_Mexico_<año>.nc (horario), UTCI_levels_<año>.nc, *_cog.tif
│  └─ INEGI/
│     ├─ mg_2020/               # Marco Geoestadístico (zip + shapefiles 00a, 00mun, 00ent) + SOURCE.md
│     ├─ iter_2020/             # ageb_manzana/ (32 zips), iter_nacional/ (localidades)
│     ├─ censo_ampliado_2020/   # microdatos Viviendas_CA, 32 zips
│     ├─ encevi_2018/           # vivienda.csv, encevi.csv
│     └─ tabulados/             # cifras oficiales para verificar (p. ej. uso_combustible.xlsx)
├─ derived/
│  └─ INEGI/2020/               # GeoParquet/Parquet producidos por 005–011
└─ stac/
   ├─ catalog.json              # catálogo raíz "atlas"
   ├─ utci/                     # colección utci  (libreta 003)
   └─ inegi/                    # colección inegi (libreta 007)
```

Convención: `data/{raw,derived}/<TIPO>/<AÑO>/…` (ver `config.raw_dir()` y
`config.derived_dir()`). El UTCI vive entero en `raw/` (el NetCDF de niveles
se considera "casi crudo"); lo socioeconómico derivado vive en `derived/`.

---

## 3. Pipeline climático (ERA5-HEAT → UTCI)

| libreta | entrada | salida | qué hace |
|---|---|---|---|
| `001_UTCI_concatenate` | diarios `ECMWF_utci_YYYYMMDD_v1.1_con.nc` (NAS) | `UTCI_Mexico_<año>.nc` | Normaliza coords (`latitude→lat`, lon 0..360 → −180..180), recorta a México, concatena 8 760 h, comprime (float32, zlib). |
| `002_UTCI_levels` | `UTCI_Mexico_<año>.nc` | `UTCI_levels_<año>.nc` | Convierte K→°C si hace falta; `np.digitize` contra los 9 cortes ISB → nivel 0–9; cuenta horas por nivel: `hours(level, lat, lon)` + `valid_hours` (NaN = UTCI indefinido, no se clasifica). |
| `003_STAC_build` | todos los `data/raw/UTCI/*/UTCI_levels_*.nc` | `UTCI_levels_<año>_cog.tif`, colección `utci` | **Descubre los años por glob**, genera un COG de 10 bandas por año (banda *k* = nivel *k−1*), y reescribe la colección `utci` con dos items por año. |

Items resultantes:

- `utci-hourly-<año>` → asset `data`: NetCDF horario.
- `utci-levels-<año>` → assets `data` (NetCDF de niveles, **el que lee la app**) y
  `cog` (para tiling futuro). Propiedades `utci:levels`, `utci:levels_es`,
  `utci:bounds_degC`.

Detalles a tener en cuenta:

- La malla es regular de **0.25°** (`config.GRID_RES_DEG`) con centros en
  múltiplos de 0.25. Todo cruce con lo socioeconómico depende de esto.
- `002` y `003` escriben `lat` descendente (como ERA5); `render.py` hace
  `sortby("lat")` antes de rasterizar.
- `001` tiene `DATA_DIR` como placeholder (`/ruta/al/NAS-…`) y escribe
  `OUT_FILE` **relativo al directorio de trabajo** (es decir, en `notebooks/`):
  hay que ajustar la ruta y mover el resultado a `data/raw/UTCI/<año>/`.
- El tiempo está en UTC.

---

## 4. Pipeline socio-territorial (INEGI, ENCEVI)

### 4.1 Orden y dependencias

```
004 marco ─► 005 AGEB urbana ─► 006 municipio + tabla puente ─► 011 AGEB rural
                                                                    │
            008 ampliado (independiente: microdatos) ───────────────┤
            009 regla climática (lee la malla UTCI vía STAC) ───────┤
                                                                    ▼
                                                 010 confort + índice MEDI (ent, mun, ageb)
                                                                    │
                                                                    ▼
                                                 007 colección `inegi` en el STAC (siempre al final)
```

Orden completo: **004 → 005 → 006 → 011 → 008 → 009 → 010 → 007**.

### 4.2 Qué hace cada libreta

| libreta | produce (`data/derived/INEGI/2020/`) | puntos clave |
|---|---|---|
| `004_INEGI_MGN_download` | (raw) `mg_2020/` + `SOURCE.md` | Descarga reanudable, verifica tamaño y SHA-256, extrae `00a` (AGEB urbana y rural), `00mun`, `00ent`. El `.prj` no trae código EPSG: se asigna 6372 a mano al leer. |
| `005_MEDI_ageb` | `medi_ageb_2020.parquet` | Lee las filas AGEB (`MZA=="000"`, `AGEB!="0000"`) de los 32 archivos oficiales; arma `cvegeo` de 13; `*` → nulo + bandera `ok/censurado/sin_viviendas` ([ADR-0002](docs/adr/0002-asteriscos-censura.md)); calcula `p_*` sobre `VIVPARH_CV` ([ADR-0001](docs/adr/0001-fuente-oficial-inegi-y-denominador.md)); une polígonos (clave 13 urbana, luego 9 rural); centroides en 6372; escribe GeoParquet 4326 con `write_covering_bbox=True`. |
| `006_MEDI_mun` | `medi_mun_2020.parquet`, `medi_ageb_2020_grid.parquet` | Municipio = filas `LOC=="0000"` (totales urbano+rural; se verifica la población nacional). **Tabla puente**: cada AGEB → celda UTCI de su centroide (`lat_c`, `lon_c` redondeados a 0.25), con numeradores, denominador y banderas. |
| `011_ITER_rural` | añade AGEB rurales a `medi_ageb_2020.parquet`; añade filas `unidad="localidad"` a la tabla puente | Suma localidades del ITER nacional por AGEB rural (puntos `00lpr`) ([ADR-0008](docs/adr/0008-ageb-rural-suma-localidades.md)). Idempotente: filtra lo rural previo antes de volver a escribir. |
| `008_AMPLIADO_mun` | `ampliado_{ent,mun,loc50k}_2020.parquet` | Microdatos del Cuestionario ampliado: combustible, fogón sin chimenea, AC; proporción ponderada por factor de expansión con **error estándar** (Taylor, conglomerado) → `cv_*` y `calidad_*`. Verifica contra boletín y tabulados. |
| `009_CLIMA_confort` | `clima_{ageb,mun,ent}_2020.parquet`, `clima_umbrales_2020.parquet`, `encevi_ent_2018.parquet` | Horas de calor (niveles ≥ 7) y frío (≤ 3) **promediadas sobre todos los años del STAC `utci`**; las lleva a AGEB/municipio/estado vía la tabla puente; ajusta umbrales `H_CALOR`/`H_FRIO` contra ENCEVI ([ADR-0007](docs/adr/0007-regla-climatica-utci.md)). |
| `010_MEDI_index` | `medi_ent_2020.parquet` (nuevo) y **reescribe** `medi_mun` y `medi_ageb` | Une ampliado, clima y ENCEVI; calcula `p_sin_confort` y `medi = Σ wᵢ·pᵢ` con intervalo `medi_min/medi_max` por censura ([ADR-0006](docs/adr/0006-definicion-medi.md)). En AGEB, el ampliado se hereda de la localidad ≥ 50 k o del municipio (`origen_ampliado`). |
| `007_STAC_inegi` | colección `inegi` | Lee esquema y bbox de cada parquet sin cargarlo, define `INDICATORS` y escribe 4 items con extensión *table* ([ADR-0004](docs/adr/0004-geoparquet-y-stac-table.md)). |

### 4.3 Patrones que se repiten (y que conviene seguir)

- **Unidad mínima con numerador y denominador**, no sólo el porcentaje: así
  cualquier agregación posterior (celda UTCI, AGEB rural) es Σnum / Σden.
- **Censura explícita**: valor nulo + columna `flag_*`; nunca imputar.
- **Escala nativa vs heredada**: cuando un dato se mide en una escala mayor
  (ampliado → municipio/localidad; ENCEVI → estado) y se pinta en una menor,
  se hereda por clave y se declara en `scale_native`; la app lo avisa en
  naranja.
- **Precisión muestral** para encuestas: `cv_*` + `calidad_*`
  (`ok` ≤ 15 %, `aviso` ≤ 30 %, `poco_preciso`); la app dibuja borde rojo.
- **Verificación con `assert`** contra una cifra oficial en cada libreta.
- **Idempotencia**: descargas por tamaño remoto; libretas que reescriben un
  producto quitan antes lo que ellas mismas añadieron (011, 010).

### 4.4 La tabla puente: cómo se cruzan ERA e INEGI

`medi_ageb_2020_grid.parquet` (sin geometría, ~9 MB) es la pieza que une los
dos mundos. Una fila por AGEB urbana (`unidad="ageb"`) y una por localidad
rural (`unidad="localidad"`), con `lat_c`, `lon_c` (centro de la celda
0.25°), `pobtot`, `vivparh_cv`, numeradores `vph_*`, banderas, y los
componentes heredados e índice.

Se usa en dos sentidos:

- **clima → territorio** (libreta 009): `celdas UTCI ⋈ grid on (lat_c, lon_c)` →
  horas de calor/frío por AGEB, luego por municipio y estado.
- **territorio → celda** (app, `stac.medi_at`): al hacer clic, filtra las
  filas de la celda y agrega (Σnum/Σden sobre unidades `ok`; media ponderada
  por viviendas para heredados e índice).

Es asignación por centroide/punto, no por área. Depende sólo de la retícula de
0.25°, no del año UTCI.

---

## 5. El catálogo STAC como contrato

```
data/stac/catalog.json                     id "atlas"
├─ utci/collection.json
│  ├─ utci-hourly-<año>/…json              asset data → ../../../raw/UTCI/<año>/UTCI_Mexico_<año>.nc
│  └─ utci-levels-<año>/…json              assets data (nc), cog (tif)
└─ inegi/collection.json
   └─ medi-{ent,mun,ageb,grid}-<año>/…json asset data → ../../../derived/INEGI/<año>/medi_*.parquet
```

**Los ids son parte del contrato.** `src/atlas/stac.py` los reconoce con regex:

```python
_LEVELS_ID = re.compile(r"^utci-levels-(\d{4})$")
_MEDI_ID   = re.compile(r"^medi-(ent|mun|ageb|grid)-(\d{4})$")
```

Un item con otro id **existe en el catálogo pero la app no lo ve**.

### `atlas:indicators` (en cada item `medi-*`)

Lista de diccionarios; es lo que puebla el selector "Indicador" y lo que usan
la coropleta, la leyenda, el tooltip y el resumen por celda.

| campo | uso en la app |
|---|---|
| `id`, `label` | clave y texto del selector |
| `column` | columna a pintar (porcentaje o índice) |
| `unit` | `"%"` o `"pts"` en leyenda y tooltip |
| `flag_column` | `ok/censurado/sin_viviendas`; en `medi_at` sólo se suman las `ok` |
| `upper_bound_column` | cota superior mostrada cuando está censurado |
| `numerator`, `denominator` | si hay numerador, la celda se agrega como Σnum/Σden; si no, media de `column` ponderada por `denominator` |
| `cv_column`, `quality_column` | CV en el tooltip y borde rojo si `poco_preciso` |
| `scale_native` | texto "Escala del dato" (naranja si contiene "hered" o "ENCEVI") |
| `weight_medi`, `is_index`, `components` | peso mostrado en el resumen de celda; el índice va en negritas |

`grid` publica los indicadores de `ageb`. Los demás atributos del item
(`table:columns`, `atlas:climate_rule`, `atlas:source`, `atlas:notebook`) son
documentación para humanos y validadores.

---

## 6. El paquete `atlas` (`src/atlas/`)

| módulo | responsabilidad | funciones principales |
|---|---|---|
| `config.py` | rutas, bbox de México, resolución de malla | `DATA_DIR`, `GRID_RES_DEG`, `raw_dir()`, `derived_dir()` |
| `stac.py` | **único punto de acceso a datos** | `open_catalog()` (cacheado), `available_years()`, `hours_field(year, level)`, `hours_at(lat, lon, year)`, `available_medi_years()`, `medi_indicators(year, level)`, `read_medi(level, year, columns=, bbox=)`, `medi_at(lat, lon, year)` |
| `indices.py` | escala UTCI de 10 clases (etiquetas, rangos, colores) | `UTCI_STRESS`, `utci_category()` |
| `render.py` | campo 2D → PNG en data URI + bounds para `ImageOverlay` | `hours_overlay_for(year, level)`, `hours_legend_items()` |
| `choropleth.py` | producto vectorial → GeoJSON estilizado | `polygon_geojson(level, …)` (ent/mun, nacional, simplificado y cacheado), `ageb_geojson(year, ind, bbox, zoom)` (por ventana), `classes()` (cuantiles nacionales, clase cero aparte), `legend_items()` |
| `plots.py` | figura de distribución de horas por nivel en una celda | `level_distribution(lat, lon, year)` |

Notas de rendimiento:

- `read_medi(..., bbox=)` usa la columna *covering bbox* del GeoParquet: lee
  sólo las filas de la ventana (~0.03 s) sin abrir los 200 MB del AGEB.
- `polygon_frame`, `classes`, `_stats`, `open_levels`, `open_medi_grid` están
  cacheados con `lru_cache`: la primera vez cuesta, luego es instantáneo.
- A 0.25° el campo UTCI (~10 k celdas) cabe en un PNG pequeño; no hay tiling.

---

## 7. La app Shiny (`components/` + `app/app.py`)

### 7.1 Ensamblado (`app/app.py`)

Al **importar** el módulo (arranque del servidor) se consulta el STAC una vez:

```python
_ANIOS        = stac.available_years()            # selector "Año"
_ANIOS_MEDI   = stac.available_medi_years()       # selector "Censo"
_INDICADORES  = stac.medi_indicators(_ANIOS_MEDI[-1]) if _ANIOS_MEDI else []
```

Si no hay colección `inegi`, el panel derecho muestra un aviso y
`socio_server` no se monta: la app funciona sólo con UTCI.

Layout (`components/panels.py`): sidebar izquierda (mapa base, nivel, año,
leyenda), mapa al centro, sidebar derecha (capa socioeconómica) y un pie con
el gráfico de la celda y su resumen MEDI.

### 7.2 Flujo reactivo (`components/servers.py`)

```
input.basemap ──► base_map (calc: L.Map con panes utci z=350, socio z=450)
                      │
input.nivel, anio ──► _pintar_campo (effect) ── render.hours_overlay_for ──► ImageOverlay (pane utci)
                      │
clic en mapa ───────► clic (reactive.Value) ──► serie (plots.level_distribution)
                      │                      └► celda_medi (stac.medi_at)
                      │
m.bounds / m.zoom ──► vista (reactive.Value) ──► modo: ent | mun | ageb | ageb_lejos
                      │
socio_* inputs ─────► _pintar_socio (effect) ── choropleth.{polygon,ageb}_geojson ──► L.GeoJSON (pane socio)
                      └► socio_leyenda, socio_escala, socio_hover, socio_aviso
```

- Cambiar nivel/año/indicador **reemplaza sólo la capa** (se guarda la
  referencia en un dict `estado`); el mapa no se reconstruye y se conserva
  zoom/paneo. Sólo cambiar el mapa base recrea el `L.Map`.
- Los *panes* fijan el orden: el raster UTCI siempre debajo de la coropleta.
- AGEB: por debajo de `choropleth.AGEB_ZOOM_MIN` (10) se pinta el municipal
  con aviso; desde ahí, se recargan las AGEB de la ventana en cada movimiento
  (tope `AGEB_MAX_FEATURES` = 8 000).
- `_indicadores_por_nivel` actualiza el selector según el item del nivel
  elegido (cada item publica su propia lista).

---

## 8. Recetas: cómo agregar datos

### 8.1 Un año nuevo de UTCI (lo más común)

1. Conseguir los diarios ERA5-HEAT del año.
2. `001`: ajustar `DATA_DIR` y `YEAR`; mover el `.nc` resultante a
   `data/raw/UTCI/<año>/UTCI_Mexico_<año>.nc`.
3. `002`: `YEAR = <año>`.
4. `003`: sin cambios (descubre los años solo).
5. **Reiniciar la app.** El selector "Año" ya lo muestra.

> ⚠️ **Efecto colateral sobre lo socioeconómico.** La regla climática (009)
> promedia *todos* los años del STAC `utci`. Un año nuevo cambia `h_calor`,
> `h_frio`, posiblemente los umbrales `H_CALOR`/`H_FRIO` y, por tanto,
> `p_sin_confort` y el **MEDI**. Si se quiere que el índice refleje el nuevo
> periodo: correr **009 → 010 → 007**. Si no, documentar que el MEDI quedó
> con los años anteriores (`atlas:climate_rule` en el STAC dice cuáles).

### 8.2 Un producto climático nuevo (otra variable o índice ERA)

Ejemplos: grados-hora de calor, percentiles de UTCI, temperatura del aire de
ERA5, anomalías contra climatología.

1. **Libreta nueva** (`012_…`) que lea el horario (vía el item
   `utci-hourly-<año>` o un crudo nuevo en `data/raw/<TIPO>/<año>/`) y escriba
   un NetCDF `(lat, lon)` o `(var, lat, lon)` en la **misma malla de 0.25°**
   (si la malla es otra, la tabla puente no sirve y hay que rehacerla).
2. **Registrar en el STAC**. Dos opciones:
   - Ampliar `003` con un nuevo tipo de item en `utci` (p. ej.
     `utci-degreehours-<año>`), si se deriva del mismo UTCI.
   - Una colección nueva con su propia libreta dueña (p. ej. `era5`), siguiendo
     el patrón de 003: abrir el catálogo existente, `remove_child` de la suya,
     `add_child`, `normalize_hrefs`, `make_all_asset_hrefs_relative`, `save`.
3. **`stac.py`**: regex del id nuevo + funciones de acceso análogas a
   `levels_items` / `open_levels` / `hours_field` / `hours_at`.
4. **`render.py`**: hoy `hours_overlay` asume una rampa ligada a una
   categoría UTCI; para una variable continua, agregar una función con su
   colormap y `vmin/vmax` (los `field_bounds` y el volteo de filas se reutilizan).
5. **UI**: un selector de producto/variable en `sidebar_left`
   (`panels.py`) y, en `map_server`, que `_pintar_campo` elija la función
   según ese input. La leyenda (`leyenda`) y el gráfico de celda
   (`plots.py`) se adaptan igual.
6. **Si debe cruzarse con lo socioeconómico**: unir por `(lat_c, lon_c)`
   contra la tabla puente, como hace 009.

### 8.3 Un indicador socio-territorial nuevo en los niveles existentes

Ejemplo: % de viviendas sin agua entubada (variable `VPH_AGUAFV` del ITER).
El indicador debe existir, con el mismo nombre de columna, en **cada nivel**
donde se quiera mostrar.

| paso | archivo | cambio |
|---|---|---|
| 1 | `005_MEDI_ageb` | agregar la variable a `KEEP` y a `NUM`; calcular `p_<x>` y `flag_<x>` con la misma regla; añadirlos a `COLS` |
| 2 | `006_MEDI_mun` | lo mismo para municipio; en la tabla puente, añadir el **numerador** y la **bandera** |
| 3 | `011_ITER_rural` | añadir a `NUM`/`INDS` para que las AGEB rurales y las filas `localidad` de la tabla puente lo traigan |
| 4 | `010_MEDI_index` | estado: añadir la variable al `usecols` de las filas entidad. Si **entra al índice**: `W`, `COL`, `CENSURABLES` (y un ADR, porque cambia la definición del MEDI) |
| 5 | `007_STAC_inegi` | una entrada en `INDICATORS` con `_ind(id, label, column, peso, flag_column=…, numerator=…)` y su texto en `DESCRIPCIONES` |
| 6 | — | correr 005 → 006 → 011 → (008 → 009) → 010 → 007 y **reiniciar la app** |

No hace falta tocar código de la app: el selector, la coropleta, la leyenda,
el tooltip y el resumen por celda se alimentan de `atlas:indicators`.

Variantes:

- **Dato de encuesta** (muestra, no censo): seguir el patrón de 008
  (`estimar()` con factor de expansión) y publicar `cv_column` y
  `quality_column` en lugar de `flag_column`.
- **Dato que sólo existe en una escala mayor** (p. ej. CONEVAL municipal,
  tarifas CFE por región): producirlo en un parquet propio con su clave
  (`cvegeo` de 5, `cve_ent`, …), y en 010 **heredarlo** hacia los niveles
  menores por prefijo de clave (como el ampliado). En 007 declarar
  `scale_native` por nivel, con la palabra "heredado" para que la app lo
  marque. Sin `numerator`, el resumen por celda lo promediará ponderado por
  viviendas.
- **Indicador que no aplica a todos los niveles**: hoy `indicators_for(level)`
  devuelve todos los `INDICATORS` para cada nivel; habría que añadir un filtro
  (p. ej. un campo `levels`) para no publicarlo donde la columna no existe.

### 8.4 Una fuente o año censal nuevo (p. ej. Conteo 2025)

El código de la app ya admite varios años (`_MEDI_ID` captura el año, existe
el selector "Censo"). Lo que hay que cambiar está en el pipeline:

- Las libretas 004–011 tienen `2020` fijo en rutas, URLs, nombres de archivo y
  constantes de verificación (`POB_NACIONAL_2020`, conteos de AGEB). Hay que
  parametrizarlas por `YEAR` y usar `config.derived_dir("INEGI", YEAR)`.
- **`007` hoy borra la colección `inegi` entera y sólo escribe `YEAR`**: con
  dos años, regenerar uno borraría el otro. Antes de agregar un segundo año,
  cambiar 007 para que conserve los items de otros años (o itere sobre todos
  los años presentes en `data/derived/INEGI/`), como hace 003 con el UTCI.
- Si cambia el Marco Geoestadístico, la tabla puente se regenera con el nuevo
  centroide de cada unidad (la retícula UTCI no cambia).
- Comparabilidad entre censos (cambios de AGEB, de municipios, de
  cuestionario) es una decisión metodológica: documentarla en un ADR.

### 8.5 Un nivel territorial nuevo (p. ej. localidad, manzana, región)

Es el cambio que más toca código de la app:

1. Producto `medi_<nivel>_<año>.parquet` + item `medi-<nivel>-<año>` en 007.
2. `stac.py`: añadir el nivel a `_MEDI_ID` y a `MEDI_LEVELS`.
3. `choropleth.py`: añadirlo a `_PROPS` (columnas del tooltip) y decidir si
   se dibuja nacional (`POLYGON_LEVELS`) o por ventana (como AGEB).
4. `panels.py`: opción en el selector `socio_nivel`.
5. `servers.py`: `modo()`, `nivel_datos()`, el diccionario `unidad` de
   `socio_leyenda` y el título de `socio_hover`.

---

## 9. Trampas conocidas

- **Reiniciar la app tras regenerar datos.** El catálogo y varios productos
  se cachean (`lru_cache`) y los años se leen al importar `app.py`.
- **010 reescribe los productos de 005/006/011.** Si se reejecuta cualquiera
  de ésas, hay que volver a correr 010 → 007, o los parquet quedan sin MEDI.
- **Un UTCI nuevo cambia el MEDI** (vía 009), ver 8.1.
- **Ids STAC fuera del patrón** no aparecen en la app (ver §5).
- **Columnas del indicador**: `choropleth` ignora en silencio las columnas que
  no existen en el parquet (`_existing`), así que un error de nombre en 007 se
  ve como "todo gris", no como excepción. Verificar con la celda de ida y
  vuelta de 007 (compara `atlas:indicators` contra `table:columns`).
- **CRS del marco INEGI**: el `.prj` no trae EPSG; siempre
  `set_crs(6372, allow_override=True)` antes de reproyectar.
- **`ADR-0005` menciona zoom 11**; el valor vigente en el código es
  `AGEB_ZOOM_MIN = 10`.

---

## 10. Dónde cambiar cada cosa (índice rápido)

| quiero cambiar… | archivo |
|---|---|
| ruta de los datos | `ATLAS_DATA_DIR` o `src/atlas/config.py` |
| cortes / colores de la escala UTCI | `notebooks/002` (cortes) y `src/atlas/indices.py` (etiquetas, colores) |
| denominadores, recodificación | `005`, `006`, `011`, `008` |
| regla de censura | `005`, `011`, `010` |
| niveles y umbrales de la regla climática | `009` |
| pesos y fórmula del MEDI | `010` (+ `INDICATORS` en `007`) |
| qué indicadores ve la app, etiquetas, escala | `007` (`INDICATORS`) |
| clases, rampa, zoom AGEB, simplificación | `src/atlas/choropleth.py` |
| rampa del raster UTCI | `src/atlas/render.py` |
| layout y controles | `components/panels.py` |
| comportamiento del mapa | `components/servers.py` |
