# PLAN — UTCI nacional → niveles de estrés → STAC → webapp

Objetivo: partir del UTCI crudo nacional (2023), derivar las horas anuales por
nivel de estrés térmico en cada punto de malla, catalogarlo en un STAC dentro
de `data/`, y que la webapp lea del STAC para graficar el nivel que el usuario
elija de una lista, para todo el país.

> **Fase 2 (capas socioeconómicas INEGI, Censo 2020):** ver [PLAN-SOCIOECONOMICOS.md](PLAN-SOCIOECONOMICOS.md) — hitos S0–S8, todos completados el 2026-09-02.

## Flujo de datos

```
data/raw/UTCI/2023/UTCI_Mexico_2023.nc        # crudo concatenado (ya existe, 8760 h)
        │  notebook 002_UTCI_levels
        ▼
data/raw/UTCI/2023/UTCI_levels_2023.nc        # horas/año por nivel y por punto
        │  notebook/script de catalogación
        ▼
data/stac/                                     # catálogo STAC (derivados, NO raw)
        │  pystac / HTTP
        ▼
webapp (app/app.py)                            # lista de niveles → mapa nacional
```

## Niveles de estrés UTCI (clasificación estándar ISB)

| # | Nivel                      | Rango UTCI (°C) |
|---|----------------------------|-----------------|
| 0 | Estrés por frío extremo    | < −40           |
| 1 | Estrés por frío muy fuerte | −40 a −27       |
| 2 | Estrés por frío fuerte     | −27 a −13       |
| 3 | Estrés por frío moderado   | −13 a 0         |
| 4 | Estrés por frío ligero     | 0 a 9           |
| 5 | Sin estrés térmico         | 9 a 26          |
| 6 | Estrés por calor moderado  | 26 a 32         |
| 7 | Estrés por calor fuerte    | 32 a 38         |
| 8 | Estrés por calor muy fuerte| 38 a 46         |
| 9 | Estrés por calor extremo   | > 46            |

En México los niveles 0–2 serán casi siempre 0 horas; se calculan igual para
que el esquema sirva a cualquier región/año.

## Formato de `UTCI_levels_2023.nc`

NetCDF con:

- dims: `level` (10) × `lat` × `lon`
- variable `hours(level, lat, lon)` — horas del año en ese nivel (int32; la
  suma sobre `level` = 8760 en cada punto)
- coord `level` con atributos `long_name` por nivel (los nombres de la tabla)
  y los umbrales en atributos globales
- misma malla lat/lon que el crudo

Un solo archivo autodescriptivo: fácil de abrir con xarray y de exponer como
asset STAC. Si la webapp luego necesita tiles, se generan COGs por nivel a
partir de este mismo archivo (paso opcional, ver M4).

## Estructura STAC en `data/stac/`

```
data/stac/
  catalog.json                          # catálogo raíz del atlas
  utci/
    collection.json                     # colección "utci" (extent México, licencia, etc.)
    utci-levels-2023/
      utci-levels-2023.json             # item con datetime 2023, bbox nacional
                                        # asset → ../../raw/UTCI/2023/UTCI_levels_2023.nc
```

- Los items apuntan a los archivos por ruta relativa; el STAC solo cataloga,
  no duplica datos.
- El crudo (`UTCI_Mexico_2023.nc`) puede catalogarse también como item
  "utci-hourly-2023" en la misma colección, para que el STAC sea el índice de
  todo, crudo incluido.
- Herramienta: `pystac` (agregar con `uv add pystac`).

## Hitos

- [x] **M0** — Crudo nacional 2023: `notebooks/001_UTCI_concatenate.ipynb` →
  `data/raw/UTCI/2023/UTCI_Mexico_2023.nc`
- [x] **M1** — `notebooks/002_UTCI_levels.ipynb`: clasificar cada hora en su
  nivel, contar horas/año por punto, guardar `UTCI_levels_2023.nc` en
  `data/raw/UTCI/2023/`. Verificación: suma sobre niveles = 8760 en todo punto;
  mapa rápido de un nivel como sanity check.
  *Hallazgo:* el crudo trae NaN donde el UTCI es indefinido (viento fuera del
  rango de validez, p.ej. jets de Tehuantepec sobre océano); 2,971 de 10,349
  puntos suman < 8760 h (mínimo 8,401). Se agregó `valid_hours(lat, lon)` al
  archivo para documentarlo.
- [x] **M2** — `notebooks/003_STAC_build.ipynb`: crea `data/stac/` con
  catálogo raíz `atlas`, colección `utci` e items `utci-hourly-2023` y
  `utci-levels-2023` (assets → rutas relativas a `data/raw/`). Validado contra
  los esquemas STAC con `pystac` y probada la ida y vuelta (releer catálogo →
  abrir asset con xarray).
- [x] **M3** — Webapp: nueva vista "Horas anuales por nivel" con dos listas a
  la izquierda: nivel de estrés (10) y año (poblado desde el STAC vía
  `atlas.stac.available_years()`). Mapa nacional de horas del nivel elegido
  (render pixelado, rampa hacia el color del nivel, 0 h transparente), leyenda
  con rangos de horas, y al hacer clic en una celda, barras con las horas/año
  en cada nivel. La vista "UTCI diario" original sigue intacta (selector de
  vista). Módulo nuevo: `src/atlas/stac.py`.
- [x] **M4** — COG multibanda por año (10 bandas, banda k = nivel k−1),
  generado en `003_STAC_build.ipynb` y agregado como asset `cog` de cada item
  `utci-levels-*`. Verificado banda a banda contra el NetCDF.
- [x] **M5** — 2022 procesado (concatenado + niveles desde los diarios de
  `data/raw/UTCI/2022/`, que vienen recortados a 33°N: malla 77×131) y
  catalogado; la libreta 003 ahora es multi-año (descubre los años en
  `data/raw/UTCI/*/`). El selector de año de la app mostró 2022
  automáticamente. *Nota:* 2022 sí registra horas de frío extremo
  (mín −40.6 °C).
- [x] **Limpieza post-POC** — Eliminados el cubo Zarr (`data/utci_mexico.zarr`),
  la vista diaria de la app y los módulos que la servían (`catalog.py`,
  `compute.py`, `ingest.py`, `cli.py`, demos `scripts/demo_m*.py`, comando
  `atlas-ingest`, dependencia `zarr`). La app quedó con una sola vista:
  nivel + año desde el STAC. README reescrito al flujo STAC.

## Decisiones a confirmar

1. `UTCI_levels_2023.nc` queda en `data/raw/` como pediste, aunque es un dato
   derivado; la alternativa sería `data/derived/UTCI/2023/` y dejar raw solo
   para lo intocable. El STAC funciona igual con cualquiera de las dos.
2. Umbrales en °C ⇒ el cálculo convierte de Kelvin al clasificar (el crudo
   queda en K).
3. ¿La webapp lee el `.nc` directo vía el STAC (simple, nacional a 0.25° es
   ligero) o quieres COGs desde ya? El plan asume `.nc` directo y deja COGs
   para M4.
