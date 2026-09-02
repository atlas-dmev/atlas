# atlas — visor de estrés térmico UTCI para México

Visor interactivo del índice **UTCI** (*Universal Thermal Climate Index*, la
temperatura "de sensación" que integra aire, humedad, viento y radiación) sobre
México, a partir del dataset **ERA5-HEAT** de Copernicus. Inspirado en la
arquitectura de [Thermal Trace](https://thermaltrace.climate.copernicus.eu),
scopeado a México y pensado como base del *Atlas Nacional de Vulnerabilidad
Energética* (IER-UNAM).

La app deja elegir un **nivel de estrés térmico** (escala UTCI de 10 clases) y
un **año** (descubierto en el catálogo STAC), pinta el mapa nacional de
**horas/año** en ese nivel y, al hacer **clic** en una celda, grafica la
distribución de horas por nivel de esa celda. El panel derecho superpone
**indicadores socioeconómicos del Censo 2020** (INEGI, diseño MEDI: viviendas
sin electricidad y sin refrigerador) por municipio o por AGEB urbana, y el clic
resume además esas carencias para las AGEB de la celda (cruce UTCI × INEGI).

![Campo de UTCI máximo diario sobre México](docs/preview.png)

## Requisitos

- [`uv`](https://docs.astral.sh/uv/) (gestión de Python y dependencias).
- Python ≥ 3.13 (lo provee `uv`).

> El proyecto se gestiona **exclusivamente con `uv`**. No uses `pip` ni venvs manuales.

## Puesta en marcha

```bash
# 1. Instalar dependencias (crea el entorno y compila el paquete `atlas`)
uv sync

# 2. (si no existen los productos) correr las libretas del pipeline
#    notebooks/001 → 002 → 003 (ver "Pipeline de datos")

# 3. Arrancar la app
uv run shiny run app/app.py
# abre http://127.0.0.1:8000
```

## Pipeline de datos

Los datos viven **fuera de Git** (`data/`, ignorado). El pipeline son
libretas reproducibles en `notebooks/`: tres para el UTCI y cuatro para las
capas socioeconómicas INEGI (ver [PLAN-SOCIOECONOMICOS.md](PLAN-SOCIOECONOMICOS.md)).

### UTCI

```
diarios ERA5-HEAT (NAS o data/raw/UTCI/<año>/)
   │  001_UTCI_concatenate.ipynb   (recorte a México + concatenación anual)
   ▼
data/raw/UTCI/<año>/UTCI_Mexico_<año>.nc          ← crudo horario (8760 h)
   │  002_UTCI_levels.ipynb        (horas/año por nivel de estrés, 10 clases ISB)
   ▼
data/raw/UTCI/<año>/UTCI_levels_<año>.nc          ← hours(level, lat, lon) + valid_hours
   │  003_STAC_build.ipynb         (COG multibanda por año + catálogo)
   ▼
data/stac/                                        ← catálogo STAC (la app lee de aquí)
```

### INEGI (indicadores MEDI, Censo 2020)

```
INEGI datos abiertos (Marco Geoestadístico 2020; AGEB y manzana urbana, 32 estados)
   │  004_INEGI_MGN_download.ipynb  (marco: 00a AGEB, 00mun, 00ent + SOURCE.md)
   │  005_MEDI_ageb.ipynb           (32 archivos oficiales → indicadores por AGEB + polígonos)
   ▼
data/derived/INEGI/2020/medi_ageb_2020.parquet    ← GeoParquet AGEB (EPSG:4326)
   │  006_MEDI_mun.ipynb            (filas municipio oficiales + puente AGEB → celda UTCI)
   ▼
data/derived/INEGI/2020/medi_mun_2020.parquet     ← GeoParquet municipal
data/derived/INEGI/2020/medi_ageb_2020_grid.parquet ← tabla puente (sin geometría)
   │  007_STAC_inegi.ipynb          (colección inegi en el mismo catálogo)
   ▼
data/stac/inegi/
```

Indicadores (porcentaje de viviendas sobre `VIVPARH_CV`, el denominador oficial
de INEGI): **sin electricidad** (peso MEDI 0.24) y **sin refrigerador** (0.21).
Los asteriscos de INEGI (indicador con menos de 3 unidades) se guardan como
nulos con banderas; electricidad lleva además una cota superior.

### Catálogo

```
data/stac/
├─ catalog.json                    # catálogo raíz "atlas"
├─ utci/
│  ├─ collection.json              # colección utci (extent, licencia, keywords)
│  └─ utci-{hourly,levels}-<año>/  # items por producto y año
│                                  # assets → ../raw/... (nc y COG, rutas relativas)
└─ inegi/
   ├─ collection.json              # colección inegi (Censo 2020, licencia INEGI)
   └─ medi-{ageb,mun,grid}-<año>/  # items con extensión table + atlas:indicators
                                   # assets → ../derived/... (parquet, rutas relativas)
```

- El STAC **cataloga, no duplica**: los assets apuntan por ruta relativa a
  `data/raw/` y `data/derived/`. Cada libreta es dueña de su colección: 003
  reemplaza `utci` y 007 reemplaza `inegi` sin tocar la otra.
- Los items `utci-levels-*` llevan además un asset **COG** multibanda
  (banda *k* = nivel *k−1*), listo para tiling futuro.
- El crudo trae NaN donde el UTCI es indefinido (viento fuera del rango de
  validez de la fórmula, p. ej. los jets de Tehuantepec); `valid_hours`
  documenta cuántas horas clasificables tuvo cada celda.
- El tiempo está en **UTC**.

## Arquitectura

Capas desacopladas; el núcleo de datos no depende de Shiny.

```
data/stac/  ← catálogo (años/productos disponibles)
   │  atlas/stac.py     (open_catalog, available_years, hours_field, hours_at,
   │                     medi_items, medi_indicators, read_medi, medi_at)
   ▼
atlas/indices.py   escala UTCI (categorías, colores)
atlas/render.py    horas/año → PNG (rampa del nivel) + leyenda
atlas/plots.py     distribución de horas por nivel de una celda
   │
   ▼
components/  (Shiny: panels, servers, shared)  +  app/app.py
```

- **`src/atlas/`** es un **paquete instalable** (layout `src/`, listo para pip).
- **`components/` + `app/`** son la capa de aplicación (Shiny) que consume el paquete.
- **Mapa**: `ipyleaflet` (vía `shinywidgets`) con `ImageOverlay`. A 0.25° el campo
  entero (~10k celdas) se rasteriza a un PNG y se pinta al instante; no hace falta
  tiling (los COGs quedan listos por si algún día sí).
- **Capa socioeconómica** (panel derecho): `atlas/choropleth.py` convierte los
  productos MEDI en `GeoJSON` estilizado por cuantiles nacionales. Municipios:
  nacional, geometría simplificada al vuelo y cacheada. AGEB urbanas: **por
  ventana**, sólo las que caen en la vista a partir de zoom 11 (filtro por bbox
  del GeoParquet + simplificación a medio píxel), recargadas al mover el mapa.
  El raster UTCI vive en un pane inferior para que la coropleta quede siempre encima.
- **Agregar un año** = correr las libretas 001–003 para ese año; el selector de
  año de la app lo descubre solo vía el STAC.
- **Capas INEGI**: `stac.read_medi(nivel, año, columns=, bbox=)` lee los
  GeoParquet (por ventana en el caso AGEB) y `stac.medi_at(lat, lon, año)`
  resume la celda UTCI de 0.25° con la tabla puente, sin abrir el archivo grande.

## Estructura del repo

```
src/atlas/       paquete instalable (config, stac, indices, render, choropleth, plots)
components/      capa Shiny (shared, panels, servers)
app/app.py       ensamblado de la app
notebooks/       pipeline reproducible (001 concatenar, 002 niveles, 003 STAC,
                 004 marco INEGI, 005 MEDI AGEB, 006 MEDI municipal, 007 STAC inegi)
PLAN.md          plan e hitos del visor UTCI
PLAN-SOCIOECONOMICOS.md  plan e hitos de las capas INEGI
docs/            metodología, temarios, DATOS-INEGI.md (datos del Censo) y adr/ (decisiones)
data/            datos (fuera de Git): raw/, derived/, stac/
```

## Fases futuras (fuera de alcance v1)

Anotadas, **no** construidas todavía:

- Tiling dinámico / TiTiler sobre los COGs (innecesario a esta resolución).
- Anomalías vs climatología 1991-2020; escalas estacional y anual.
- Vista de dispersión "horas en nivel X vs % sin refrigerador" por AGEB o
  municipio (el cruce por celda ya está en el pie de página; hito S8 pendiente
  sólo de documentación).
- Índices propios de confort adaptativo (IMAC, grados-hora) como nuevos
  productos del STAC — el diferenciador de la investigación.
- Hora local de México (hoy todo se etiqueta en UTC).
- Entry point `atlas-app` para arrancar la app como comando.
