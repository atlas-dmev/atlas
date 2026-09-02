# ADR-0004 — Productos vectoriales en GeoParquet catalogados en STAC con la extensión *table*
Estado: aceptado (2026-09-02)
Contexto:        Los productos MEDI son tablas con geometría (64 313 AGEB, 2 469 municipios) y una tabla puente sin geometría. El atlas ya cataloga sus rasters en un STAC local y la app descubre años/productos desde ahí.
Opciones:        (a) shapefile/GeoPackage; (b) GeoJSON nacional; (c) GeoParquet (+ columna bbox) y Parquet, registrados como items STAC con extensión *table*; (d) base de datos espacial (PostGIS/DuckDB spatial).
Criterios:       lectura por columnas y por ventana sin cargar todo; un solo formato para con/sin geometría; descubrimiento por la app sin rutas fijas; sin servicios adicionales.
Evidencia:       Spike (S4): lectura por bbox del GeoParquet de 74 MB en 0.06 s (3 003 AGEB del centro de CDMX), municipal sin geometría en 0.05 s, tabla puente en 10 ms; validación `pystac` de la extensión table. Referencias: especificación GeoParquet 1.1 (columna `covering.bbox`); STAC *table* extension v1.2.0; Apache Parquet (proyección de columnas y row groups).
Decisión:        (c). Colección `inegi` con items `medi-<nivel>-<año>`, columnas tipadas y descritas en `table:columns`, e indicadores publicados en `atlas:indicators` para que la UI no los hardcodee.
Consecuencias:   +misma disciplina que el UTCI (el STAC cataloga, no duplica); +la capa AGEB por ventana es posible sin servidor; −GeoParquet no es legible por GIS de escritorio antiguos (QGIS ≥ 3.28 sí).
Revisión:        si los productos crecen a decenas de millones de filas o se sirven remotamente, considerar PMTiles/vector tiles o DuckDB.
