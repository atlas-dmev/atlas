# Plan — Visor de estrés térmico UTCI para México (v1)

> Rama: `feat/utci-viewer-v1`. Estilo *Thermal Trace* (Copernicus), scopeado a México.
> Decisiones del usuario: **cubo horario crudo** · **ingesta robusta multi-año/tipo** · **bbox continental + mar**.

> **Fase 2 (capas socioeconómicas INEGI, Censo 2020):** ver [PLAN-SOCIOECONOMICOS.md](../PLAN-SOCIOECONOMICOS.md) — hitos S0–S8, todos completados el 2026-09-02.

## 0. Hechos verificados del dato (no supuestos)

- Fuente: ERA5-HEAT, `data/UTCI-2022/ECMWF_utci_YYYYMMDD_v1.1_con.area-subset.33.-86.14.-119.nc`.
- **365 archivos diarios**, cada uno con `utci(time=24, lat=77, lon=133)` → **horario**.
- Grid **0.25°**: lat 14→33 (77), lon −119→−86 (133). bbox ya recortado a México en origen.
- `units` vacío en el NetCDF → se asume **Kelvin** (estándar ERA5-HEAT); se normaliza en ingesta (a verificar por rango de valores en M1).
- Volumen: 8 760 pasos/año × 77 × 133 ≈ **~360 MB float32/año** en Zarr. Local, sin tiling.

---

## 1. Arquitectura (diagrama de módulos)

Capas desacopladas: **ingesta** (offline) → **cubo Zarr** (artefacto) → **cómputo/índices** (puro, sin Shiny) → **UI Shiny** (reactiva). El núcleo de cómputo no importa nada de Shiny → testeable y reutilizable.

```
                 OFFLINE (scripts)                 RUNTIME (uv run app)
  ┌───────────────────────────┐        ┌──────────────────────────────────────┐
  │ data/raw/UTCI/2022/*.nc    │        │  Shiny UI (app/app.py)                │
  │        │                   │        │   ├─ panels.py  (date, índice, leyenda,│
  │        ▼                   │        │   │              plot serie temporal)  │
  │ scripts/ingest.py          │        │   └─ servers.py (map_server, ts_server)│
  │   NetCDF→Zarr, append time │        │            │            ▲              │
  └────────┼───────────────────┘        └────────────┼────────────┼─────────────┘
           ▼                                          ▼            │ click(lat,lon)
  ┌───────────────────────────┐        ┌──────────────────────────┴─────────────┐
  │ data/utci_mexico.zarr/     │◀───────│  src/atlas/  (núcleo, sin Shiny)        │
  │  utci(time,lat,lon)        │  lazy  │   catalog.py  open_cube(), fechas/vars  │
  │  + atributos/catálogo      │        │   indices.py  REGISTRO pluggable        │
  └───────────────────────────┘        │   compute.py  field_for(date,index),    │
                                        │               series_at(lat,lon)        │
                                        │   render.py   field→PNG (colormap+leyenda)│
                                        │   config.py   rutas, bbox, store        │
                                        └─────────────────────────────────────────┘
```

**Pieza clave (tu diferenciador): registro de índices pluggable** en `indices.py`.
Un índice es una función pura sobre el cubo horario. Hoy registramos `utci_daily_max`
y su categoría de estrés; mañana registras IMAC / grados-hora sin tocar la UI.

```python
@dataclass
class Index:
    key: str                                   # "utci_daily_max"
    label: str                                 # "UTCI máximo diario"
    units: str                                 # "°C"
    aggregate: Callable[[xr.DataArray, date], xr.DataArray]  # cubo horario -> campo 2D
    categorize: Callable | None                # valor -> clase de estrés (opcional)
    cmap: ColorSpec                            # colormap + leyenda

REGISTRY: dict[str, Index] = {}   # la UI se construye desde aquí
```

---

## 2. Estructura de carpetas

`atlas` es un **paquete local instalable** (layout `src/`) pensado para publicarse en
pip más adelante. Cubre **ingesta + cómputo + render** y expone **entry points de
consola**. La app Shiny consume el paquete.

```
atlas/
├─ pyproject.toml          # uv; build-system (hatchling); [project.scripts]; deps
├─ uv.lock
├─ README.md               # qué es + cómo: uv sync, atlas-ingest ..., uv run app
├─ .gitignore              # data/, .venv/, __pycache__/, *.zarr  ← protege el cubo
├─ docs/
│  └─ PLAN.md              # este documento
├─ data/                   # FUERA de git (no se empaqueta)
│  ├─ raw/UTCI/2022/*.nc   # NetCDF fuente (reorganizado por tipo/año)
│  └─ utci_mexico.zarr/    # cubo construido (artefacto)
├─ src/atlas/              # ── PAQUETE INSTALABLE ──
│  ├─ __init__.py          # versión, API pública
│  ├─ config.py            # rutas, bbox, ubicación del store
│  ├─ ingest.py            # NetCDF -> Zarr (append por time, idempotente, multi-año/tipo)
│  ├─ catalog.py           # open_cube() perezoso, fechas/variables disponibles
│  ├─ indices.py           # registro pluggable de índices
│  ├─ compute.py           # field_for(date, index) / series_at(lat, lon)
│  ├─ render.py            # campo 2D -> PNG + leyenda para ImageOverlay
│  └─ cli.py               # entry points: `atlas-ingest`, (futuro) `atlas-app`
├─ components/             # capa Shiny (UI; extiende el scaffold existente)
│  ├─ shared.py            # BASEMAPS + wiring del REGISTRY de índices del paquete
│  ├─ panels.py            # + input_date, selector de índice, leyenda, output plot
│  └─ servers.py           # map_server (ImageOverlay + click) + ts_server
├─ app/app.py              # ensambla UI + server (importa de atlas + components)
└─ tests/                  # pruebas del núcleo (ingesta idempotente, índices)
```

- **`[project.scripts]`**: `atlas-ingest = "atlas.cli:ingest"` para correr la ingesta como
  comando (`uv run atlas-ingest UTCI 2022`), instalable también vía pip a futuro.
- El scaffold actual (`app/app.py`, `components/*`) **se extiende**, no se reescribe.
- `components/` y `app/` quedan como capa de aplicación (Shiny) *fuera* del paquete pip;
  si más adelante quieres distribuir también la app, se moverían a `atlas.app`.

---

## 3. Librería de mapa: **ipyleaflet** (vía shinywidgets) + `ImageOverlay`

| Opción | Veredicto |
|---|---|
| **ipyleaflet** ✅ | Ya está en deps y en el scaffold. Click vía `m.on_interaction` → (lat,lon). Campo = 1 PNG en `ImageOverlay` sobre el bbox: 10k celdas pintan al instante. Integra con `shinywidgets`. |
| leafmap | Envuelve ipyleaflet/folium; añade dependencia para conveniencias que no necesitamos. |
| pydeck / maplibre | GPU, sobreingeniería para 10k celdas; plomería click→Shiny más enredada. |

**Decisión: ipyleaflet + ImageOverlay.** El campo 2D se rasteriza a PNG con un colormap
de estrés (matplotlib) y se superpone con `bounds=[(lat_min,lon_min),(lat_max,lon_max)]`.
Click → `on_interaction` actualiza un `reactive.Value`, se toma la celda *nearest* y se
grafica la serie horaria con `render.plot`.

---

## 4. Hitos incrementales (cada uno demostrable)

| Hito | Entrega | Cómo se demuestra |
|---|---|---|
| **M0 — Infra** | `.gitignore`, `uv add` deps, `pyproject.toml` con build-system + `src/atlas/` instalable + `[project.scripts]`, `config.py`, reorganizar `data/raw/UTCI/2022/`. | `uv run` arranca la app actual sin romper; `git status` no ve `data/`; `import atlas` funciona. |
| **M1 — Ingesta** | `atlas/ingest.py` + `atlas/cli.py`: 365 nc → `utci_mexico.zarr`, append por `time`, idempotente, parametrizado por `(tipo, año)`, valida solapamientos, normaliza unidades. | `uv run atlas-ingest UTCI 2022` y abrir el Zarr: 8 760 pasos. Re-correr no duplica. |
| **M2 — Cómputo + índices** | `indices.py` (registro + `utci_daily_max` + categoría de estrés), `compute.py` (`field_for`, `series_at`). | Script/notebook: campo de una fecha y serie de una celda, sin Shiny. |
| **M3 — Mapa** | `render.py` + `panels.input_date`/selector + `servers.map_server` pinta `ImageOverlay` con colormap + leyenda. | En la app: eliges fecha/índice → se pinta el campo de México. |
| **M4 — Click → serie** | `on_interaction` → nearest → `ts_server` con `render.plot` de UTCI horario. | En la app: clic en un punto → grafica su serie temporal. |
| **M5 — Pulido** | README con `uv run`, validaciones, sección "Fases futuras". | Clon limpio: `uv sync && uv run ...` reproduce todo. |

Commits pequeños por hito. Cada hito deja la app arrancable.

---

## 5. Supuestos y decisiones abiertas

**Decisiones confirmadas por el usuario:**
- **Empaquetado**: `src/atlas/` como **paquete local instalable**, a publicar en pip
  después; cubre mapa + ingesta. → build-system + `[project.scripts]`.
- **Idioma**: UI y categorías en **español**.
- **Categorías de estrés**: **tabla UTCI estándar de ECMWF** (10 clases, cortes en °C).

**Supuestos (procedo con ellos salvo que digas lo contrario):**
- UTCI en **Kelvin** → normalizo a **°C** en ingesta (verifico por rango en M1).
- Tabla ECMWF: <−40 *frío extremo* · −40..−27 *frío muy fuerte* · −27..−13 *frío fuerte* ·
  −13..0 *frío moderado* · 0..9 *frío ligero* · 9..26 *sin estrés* · 26..32 *calor moderado* ·
  32..38 *calor fuerte* · 38..46 *calor muy fuerte* · >46 *calor extremo*.
- Datos en **EPSG:4326** regular; ImageOverlay con bounds lat/lon (distorsión vertical
  leve y aceptable a 14–33° N; ver riesgo R2).
- `data/raw/UTCI/<año>/` como layout canónico; muevo lo descargado ahí en M0.
- Cubo perezoso, chunked en `time`; nunca se carga el año entero en memoria.

---

## 6. Riesgos y mitigación

| # | Riesgo | Mitigación |
|---|---|---|
| R1 | Unidades/escala de `utci` ambiguas (attr vacío). | Verificar rango en M1; normalizar a °C en un solo lugar (ingesta). |
| R2 | Reproyección 4326↔3857 distorsiona el ImageOverlay. | A esta escala/latitud es leve; si molesta, reproyectar con `rioxarray` a 3857 antes del PNG (fase futura, aislado en `render.py`). |
| R3 | `to_zarr` append: solapamientos/duplicados de tiempo. | Ingesta lee tiempos existentes, ordena por fecha, escribe solo lo nuevo (`append_dim='time'`); idempotente. |
| R4 | Click en ipyleaflet dentro de Shiny no propaga bien. | Spike temprano en M4 con `on_interaction` + `reactive.Value`; es patrón conocido en shinywidgets. |
| R5 | Memoria al agregar. | Lazy + chunk en `time`; `field_for` selecciona solo la fecha pedida antes de `.max()`. |
| R6 | `data/` (360 MB+) acaba en git. | `.gitignore` en M0 *antes* de cualquier `git add`. |

---

## Fuera de alcance v1 (documentado, NO construir)
Tiling/TiTiler/COG · anomalías vs clima 1991-2020 · escalas estacional/anual ·
capas INEGI/AGEB y vulnerabilidad · DuckLake/Parquet/Icechunk ·
sustitución por IMAC/grados-hora (pero el registro de índices ya deja la puerta abierta).
