# Temario por ítems — Atlas v1 (catálogo de estudio/implementación)

> Versión **no temporal** del [temario](TEMARIO.md): una lista de ítems
> independientes que cada estudiante estudia, implementa y **somete a crítica
> contra la literatura**. No hay calendario; el orden sugerido es de fundamentos
> a avanzado, pero pueden escogerse según necesidad.
>
> **Cada ítem tiene la misma estructura:**
> - 📖 **Estudiar** — el concepto mínimo a dominar.
> - 🔨 **Implementar** — el entregable concreto.
> - 🔍 **¿Es la mejor opción?** — la decisión a cuestionar + alternativas a comparar con bibliografía.
>
> Producto esperado por cada ítem 🔍: un párrafo de decisión razonada (mini-ADR)
> con evidencia propia (benchmark/prueba) y al menos una referencia.

---

## Ítems comunes (ambas personas)

### C1 — Entorno y reproducibilidad con `uv`
- [ ] 📖 Gestión de proyectos Python con `uv` (sync, run, add, lock); por qué no `pip`/venv manual.
- [ ] 🔨 Clonar, `uv sync`, correr un script; agregar una dependencia y ver el `uv.lock`.
- [ ] 🔍 ¿`uv` o `poetry`/`pdm`/`conda`/`pip-tools`? Compara velocidad, lockfile, reproducibilidad. → docs de `uv`, comparativas de gestores.

### C2 — Git con commits pequeños y ramas
- [ ] 📖 Flujo de ramas, commits atómicos, mensajes claros.
- [ ] 🔨 Trabajar en una rama propia; abrir PR hacia la rama de integración.
- [ ] 🔍 ¿*trunk-based* o *git-flow* para un equipo de 2? → literatura de estrategias de branching.

### C3 — El contrato de interfaz (esquema del cubo)
- [ ] 📖 Por qué un contrato explícito permite trabajo en paralelo.
- [ ] 🔨 Definir juntos el esquema del Zarr (dims, coords, unidades, orden) y un `tests/test_contrato.py` que lo valide; crear un **fixture Zarr sintético** para que B no dependa de A.
- [ ] 🔍 ¿Validar con pruebas, o con un esquema declarativo (p. ej. `xarray` + `pandera`/`cf-checker`/JSON Schema)? → docs de validación de datos.

### C4 — UTCI y ERA5-HEAT (dominio)
- [ ] 📖 Qué integra el UTCI (aire, humedad, viento, radiación); la escala de estrés; qué es ERA5-HEAT y su resolución/cobertura.
- [ ] 🔨 Resumen de 1 página del dataset y la variable.
- [ ] 🔍 ¿UTCI es el índice adecuado para confort en edificaciones en México, o conviene IMAC/grados-hora? → Bröde et al. (2012); literatura de confort adaptativo (IMAC).

---

## Persona A — Datos & Store

> **Objetivo:** convertir ERA5-HEAT (UTCI) crudo en un cubo Zarr perezoso,
> escalable a años y variables, y justificar cada decisión de almacenamiento.

### A1 — Adquisición de datos (CDS API)
- [ ] 📖 La Climate Data Store API y `cdsapi`; autenticación; pedir un subset por bbox/fechas.
- [ ] 🔨 Script que descargue un mes de UTCI para el bbox de México de forma programática.
- [ ] 🔍 ¿Descarga vía `cdsapi`, o acceso directo a Zarr/STAC en la nube (ARCO-ERA5, Google/AWS)? ¿Conviene descargar o consumir remoto? → docs CDS, Pangeo/ARCO-ERA5, STAC.

### A2 — NetCDF + xarray (lectura)
- [ ] 📖 Modelo de datos de xarray (`Dataset`/`DataArray`, dims, coords, attrs); convenciones CF; lectura perezosa con Dask.
- [ ] 🔨 Abrir un archivo diario, inspeccionar todo, convertir Kelvin→°C, documentar atributos.
- [ ] 🔍 ¿xarray sobre `netCDF4`/`h5netcdf`, o `iris`/`cfgrib` u otra pila? ¿Qué *engine* conviene? → docs xarray, comparativa de engines.

### A3 — Series temporales sobre el cubo
- [ ] 📖 `resample` (máx/mín/media diaria), selección `nearest`, ciclo diurno, **UTC vs hora local**.
- [ ] 🔨 Computar UTCI máx diario (campo) y la serie horaria de una celda.
- [ ] 🔍 ¿Agregar al vuelo, o pre-agregar a diario en la ingesta? (costo cómputo vs almacenamiento vs flexibilidad para índices futuros). → docs xarray/pandas resample.

### A4 — Chunking
- [ ] 📖 Qué es un *chunk*, cómo el chunking decide qué se lee; alinear chunking con patrones de acceso.
- [ ] 🔨 **Benchmark**: medir "leer un día" vs "leer la serie de una celda" con 2–3 chunkings (p. ej. `time=24`, `time=168`, `time=full`).
- [ ] 🔍 ¿`time=24` (un día) es óptimo para *esta* app, o lo es otro? Defiende con tus números. → docs Zarr/Dask sobre chunking; guía Pangeo "choosing chunk sizes".

### A5 — Compresión y tipos
- [ ] 📖 Codecs (zstd, blosc, zlib), niveles, *shuffle*; `float32` vs cuantización/escala-offset.
- [ ] 🔨 Reescribir el cubo con 2 codecs/niveles y comparar tamaño y tiempo de lectura.
- [ ] 🔍 ¿zstd nivel 0 es la mejor relación, o conviene blosc/otro nivel? ¿Vale cuantizar? → docs `numcodecs`, benchmarks de compresión científica.

### A6 — Formato de almacenamiento (la decisión grande)
- [ ] 📖 Zarr (v3): grupo/array, layout en disco, metadatos; *append*; almacenamiento en nube.
- [ ] 🔨 Escribir y reabrir un cubo Zarr; inspeccionar la carpeta (`zarr.json`, chunks).
- [ ] 🔍 **¿Zarr es la herramienta correcta?** Compara contra NetCDF directo, HDF5, **TileDB**, **Parquet/Arrow**, **COG**, GRIB, **Icechunk** — frente a estos patrones de acceso y a la escala esperada. → CNG Foundation (formatos), specs Zarr v3, Icechunk, TileDB.

### A7 — Metadatos consolidados / catálogo
- [ ] 📖 `consolidated metadata` (y su estatus deprecado en Zarr v3); cómo se descubren fechas/variables.
- [ ] 🔨 Implementar `open_cube()` perezoso + listado de fechas/variables disponibles.
- [ ] 🔍 ¿Consolidar metadatos, o un catálogo externo (**STAC**, **intake**, **kerchunk**)? → docs intake/STAC/kerchunk.

### A8 — Pipeline de ingesta idempotente
- [ ] 📖 `open_mfdataset` (combinar muchos NetCDF), idempotencia, *append* por `time`, validación de solapamientos.
- [ ] 🔨 `atlas-ingest <tipo> <año>` que cree/extienda el cubo sin duplicar y rechace solapamientos parciales.
- [ ] 🔍 ¿Idempotencia por `time` y *append-only*, o **region writes**/Icechunk (transaccional) para insertar años en cualquier orden? → docs Zarr region writes, Icechunk.

### A9 — Multi-variable / multi-año (el hueco real)
- [ ] 📖 Cubo de varias variables compartiendo coords vs. *store por variable* con rangos temporales distintos.
- [ ] 🔨 Diseñar e implementar una de las dos opciones; ingerir una 2ª variable o un año fuera de orden.
- [ ] 🔍 ¿Un store compartido (con NaN al alinear) o uno por variable + catálogo? → literatura de *data cubes* / Pangeo.

### A10 — Robustez y pruebas
- [ ] 📖 `pytest`, fixtures, validación de días faltantes/huecos, logging.
- [ ] 🔨 Suite que pruebe idempotencia, normalización de unidades y huecos.
- [ ] 🔍 ¿Pruebas unitarias bastan, o conviene *data validation* declarativa (pandera/great-expectations)? → docs de esas librerías.

---

## Persona B — Visualización & App

> **Objetivo:** app que pinta el campo UTCI en un mapa de México y grafica la
> serie de una celda al clic, justificando cada decisión de visualización.

### B1 — Framework de app reactiva
- [ ] 📖 Shiny for Python: `input`/`output`, `reactive.calc`, `reactive.effect`, `@render.*`; flujo reactivo.
- [ ] 🔨 Mini-app reactiva (un control que actualiza una salida).
- [ ] 🔍 **¿Shiny, o Dash/Streamlit/Panel/JS puro?** Criterios: modelo reactivo, despliegue, curva, que ClimaLab ya use Shiny. → docs Shiny/Dash/Streamlit/Panel.

### B2 — Mapas web y CRS
- [ ] 📖 *Tiles*, basemaps, **CRS** (EPSG:4326 dato vs 3857 display); conceptos de Leaflet.
- [ ] 🔨 Mapa con basemap centrado en México dentro de Shiny (vía `shinywidgets`).
- [ ] 🔍 ¿Cuánta distorsión introduce pintar dato 4326 sobre mapa 3857 a lat 14–33° N? ¿Reproyectar con rioxarray vale la pena? → spatialreference.org, docs rioxarray.

### B3 — Librería de mapa
- [ ] 📖 `ipyleaflet` y su integración con `shinywidgets`; capas, eventos.
- [ ] 🔨 Renderizar una capa y manejar un evento básico.
- [ ] 🔍 **¿ipyleaflet, o leafmap/folium/pydeck/maplibre/lonboard?** Reimplementa UNA feature en otra y compara. → docs de cada una; curso de leafmap.

### B4 — Rasterización del campo
- [ ] 📖 Pasar un arreglo 2D (lat, lon) a imagen RGBA → PNG; orientación (norte arriba), NaN transparente; `ImageOverlay` con *bounds*.
- [ ] 🔨 Pintar un campo del fixture como `ImageOverlay` sobre México.
- [ ] 🔍 **¿ImageOverlay (cliente) o tiling servidor (TiTiler/titiler-xarray)?** ¿A qué tamaño de malla deja de escalar el enfoque cliente? → docs TiTiler, spec COG.

### B5 — Discretización vs interpolación
- [ ] 📖 Por qué el navegador interpola imágenes al escalar; `image-rendering: pixelated`; resolución nativa del PNG.
- [ ] 🔨 Lograr que cada celda de 0.25° se vea como bloque nítido (sin degradado).
- [ ] 🔍 ¿PNG pixelado, o pintar la malla como capa vectorial (GeoJSON/polígonos)? Trade-off claridad vs desempeño. → docs Leaflet de capas raster/vector.

### B6 — Colormap y categorías de estrés
- [ ] 📖 Colormap discreto (ListedColormap + BoundaryNorm) vs continuo; *perceptual uniformity*; *colorblind-safe*; la escala UTCI de 10 clases.
- [ ] 🔨 Colorear el campo por categoría de estrés + leyenda.
- [ ] 🔍 ¿La paleta es perceptualmente uniforme y *colorblind-safe*? ¿Conviene Crameri/ColorBrewer/viridis? → Crameri *Scientific colour maps*, ColorBrewer, docs matplotlib.

### B7 — Reactividad del campo (fecha/índice)
- [ ] 📖 Actualizar una capa sin reconstruir el mapa (preservar zoom/paneo); `reactive.effect`.
- [ ] 🔨 Selectores de fecha e índice que repinten el overlay manteniendo la vista.
- [ ] 🔍 ¿Mutar la capa vía `effect`, o reconstruir el widget? Costo/UX. → docs Shiny reactividad, shinywidgets.

### B8 — Interacción: clic → serie temporal
- [ ] 📖 `on_interaction` de ipyleaflet; pasar el evento a un `reactive.Value`; celda *nearest*; graficar con etiquetas en **UTC**.
- [ ] 🔨 Clic en el mapa → serie horaria de esa celda con bandas de estrés.
- [ ] 🔍 ¿Graficar con matplotlib (`@render.plot`), o Plotly/Altair interactivos? Trade-offs. → docs Shiny outputs, Plotly/Altair.

### B9 — Arquitectura: índice pluggable y separación UI/núcleo
- [ ] 📖 Por qué el cómputo no debe depender de Shiny; un registro de índices como punto de extensión.
- [ ] 🔨 Registrar un 2º índice (p. ej. UTCI mínimo/media diaria) y verlo en la UI **sin tocar** la app.
- [ ] 🔍 ¿Registro/*plugin* o configuración declarativa (entry points/YAML)? → patrones de plugins en Python (`importlib.metadata` entry points).

### B10 — Empaquetado y arranque
- [ ] 📖 Estructura `src/` instalable, separar paquete (`atlas`) de capa de app (`components`/`app`); entry points.
- [ ] 🔨 Que `uv run shiny run app/app.py` arranque limpio; opcional un comando `atlas-app`.
- [ ] 🔍 ¿`src/` layout + hatchling, o flat layout/otra build backend? → guía de empaquetado de Python (PyPA).

---

## Ítems de la fase 2 — capas socioeconómicas INEGI (ambas personas)

> Referencia: [planes/03-capas-inegi-medi.md](planes/03-capas-inegi-medi.md),
> [DATOS.md](DATOS.md) y los ADR 0001–0005 en [adr/](adr/).

### C5 — Censo 2020 e INEGI (dominio)
- [ ] 📖 Qué es el ITER, la AGEB (urbana vs rural), el Marco Geoestadístico; qué significa el asterisco; `VIVPAR_HAB` vs `VIVPARH_CV`.
- [ ] 🔨 Reproducir con un estado (p. ej. Aguascalientes) que `VPH_REFRI > VIVPAR_HAB` en muchas AGEB y que nunca supera `VIVPARH_CV`.
- [ ] 🔍 ¿Imputar, acotar o dejar nulo lo censurado? → ADR-0002; literatura de supresión por umbral en estadística oficial.

### A11 — Formatos vectoriales y catálogo (GeoParquet + STAC *table*)
- [ ] 📖 Parquet por columnas y row groups; GeoParquet 1.1 y la columna `bbox`; extensión *table* de STAC.
- [ ] 🔨 Leer sólo dos columnas y una ventana del GeoParquet de AGEB y medir el tiempo; registrar un item STAC nuevo y validarlo con `pystac`.
- [ ] 🔍 ¿GeoParquet, GeoPackage, PMTiles o DuckDB para este tamaño y este uso? → ADR-0004; especificaciones respectivas.

### A12 — CRS, claves y unión de tablas con geometría
- [ ] 📖 Proyección conforme vs equivalente; por qué el `.prj` de INEGI no trae código EPSG; claves geoestadísticas de 13 y de 9.
- [ ] 🔨 Unir el ITER con `00a` reproduciendo el *fallback* de clave de 9 para las 331 AGEB rurales; calcular centroides en 6372 y comparar con calcularlos en 4326.
- [ ] 🔍 ¿Reproyectar el atlas o los vectores? → ADR-0003; RFC 7946.

### B11 — Coropletas: clases, color y orden de dibujo
- [ ] 📖 Esquemas de clasificación (cuantiles, Jenks, cortes fijos) y cuándo una clase "cero" es necesaria; rampas que no compiten con otra capa; panes de Leaflet y `zIndex`.
- [ ] 🔨 Cambiar el esquema de clases del municipal y justificar el efecto en el mapa; mover el raster UTCI de pane y observar qué tapa a qué.
- [ ] 🔍 ¿Cuantiles nacionales fijos o de la ventana visible? → decisión 4 del plan; Brewer & Pickle (2002) sobre clasificación en coropletas.

### B12 — Capas por ventana y reactividad del mapa
- [ ] 📖 Eventos `moveend`/`zoomend`; traits `bounds`/`zoom` de ipyleaflet; simplificación ligada al píxel del zoom.
- [ ] 🔨 Bajar `AGEB_ZOOM_MIN` a 10, medir tamaño y tiempo en CDMX, y decidir con datos; implementar la alternativa "AGEB del municipio pulsado" como spike.
- [ ] 🔍 ¿Vector por ventana, PNG por ventana o vector tiles? → ADR-0005.

### A13 — Muestras complejas: factor de expansión y varianza por conglomerados
- [ ] 📖 Diseño estratificado por conglomerados (`ESTRATO`, `UPM`, `FACTOR`); estimador de razón; linealización de Taylor y conglomerado último; coeficiente de variación y reglas de publicación de INEGI.
- [ ] 🔨 Reproducir para un estado la estimación municipal de "sin aire acondicionado" del ampliado (libreta 008) y comparar el CV con el de una fórmula de muestreo aleatorio simple.
- [ ] 🔍 ¿Taylor, jackknife o bootstrap de réplicas para este diseño? → Lohr, *Sampling: Design and Analysis*; documentación de `samplics`/`survey` (R).

### B13 — Índices compuestos y su visualización honesta
- [ ] 📖 Suma ponderada vs conteo tipo Alkire-Foster; intervalos por censura; escalas mezcladas (componentes heredados) y cómo señalarlas en leyenda y tooltip.
- [ ] 🔨 Cambiar un peso del MEDI en la libreta 010, reejecutar 007 y medir cuántos municipios cambian de clase; añadir al tooltip la descomposición del índice por componente.
- [ ] 🔍 ¿Debe el atlas mostrar `medi_min`–`medi_max` como incertidumbre visual (p. ej. trama) o basta la nota? → Alkire & Foster (2011); literatura de visualización de incertidumbre en coropletas (MacEachren et al.).

---

## Cómo evaluar cada ítem
Un ítem está **completo** cuando: (1) el entregable 🔨 funciona y está commiteado;
(2) existe el mini-ADR 🔍 con evidencia propia + ≥1 referencia; (3) cumple el
contrato C3 si toca el cubo. La integración final exige que la app de B corra
sobre el cubo real de A.
