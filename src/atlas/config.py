"""Configuración central: rutas, bounding box de México y ubicación del store.

Un único lugar para resolver dónde viven los datos. La raíz del repo se deriva
relativa a este archivo, pero puede sobreescribirse con la variable de entorno
``ATLAS_DATA_DIR`` (útil cuando el paquete se instale vía pip y los datos vivan
fuera del árbol de fuentes).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# Raíz del repositorio: src/atlas/config.py -> repo/
REPO_ROOT = Path(__file__).resolve().parents[2]

# Directorio de datos (no versionado). Sobreescribible por entorno.
DATA_DIR = Path(os.environ.get("ATLAS_DATA_DIR", REPO_ROOT / "data"))

# Datos fuente tal como se descargan, organizados por tipo: data/raw/<TIPO>/...
#   UTCI:  data/raw/UTCI/<AÑO>/*.nc
#   INEGI: data/raw/INEGI/{iter_2020,tabulados,encevi_2018,mg_2020}/
RAW_DIR = DATA_DIR / "raw"

# Productos derivados por el pipeline (libretas), organizados igual que raw:
# data/derived/<TIPO>/<AÑO>/... (p. ej. GeoParquet MEDI en derived/INEGI/2020/).
# El STAC cataloga tanto raw como derived por ruta relativa.
DERIVED_DIR = DATA_DIR / "derived"


@dataclass(frozen=True)
class BBox:
    """Bounding box geográfico (grados decimales, EPSG:4326)."""

    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float


# México continental + mar adyacente, tal como viene recortado el ERA5-HEAT.
MEXICO_BBOX = BBox(lon_min=-119.0, lon_max=-86.0, lat_min=14.0, lat_max=33.0)

# Resolución del grid ERA5-HEAT.
GRID_RES_DEG = 0.25


def raw_dir(tipo: str, anio: int) -> Path:
    """Directorio de datos fuente para un (tipo, año)."""
    return RAW_DIR / tipo / str(anio)


def derived_dir(tipo: str, anio: int) -> Path:
    """Directorio de productos derivados para un (tipo, año)."""
    return DERIVED_DIR / tipo / str(anio)
