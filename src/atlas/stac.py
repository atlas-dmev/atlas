"""Acceso al catálogo STAC (``data/stac/``): descubrimiento de productos derivados.

Espejo de ``catalog`` pero para el STAC: la app pregunta aquí qué años/productos
hay disponibles, nunca con rutas sueltas. El STAC cataloga; los datos viven en
``data/raw/`` (UTCI) y ``data/derived/`` (INEGI).

Dos colecciones:

- ``utci``: horas/año por nivel de estrés (``utci-levels-<año>``).
- ``inegi``: indicadores MEDI del Censo 2020 (``medi-<nivel>-<año>`` con
  nivel ``ageb`` | ``mun`` | ``grid``), en GeoParquet/Parquet.
"""

from __future__ import annotations

import functools
import re
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import pystac
import xarray as xr

from atlas import config

STAC_DIR = config.DATA_DIR / "stac"

_LEVELS_ID = re.compile(r"^utci-levels-(\d{4})$")
_MEDI_ID = re.compile(r"^medi-(ageb|mun|grid)-(\d{4})$")

MEDI_LEVELS = ("ageb", "mun", "grid")


@functools.lru_cache(maxsize=1)
def open_catalog() -> pystac.Catalog:
    """Catálogo raíz (cacheado)."""
    path = STAC_DIR / "catalog.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No existe el catálogo STAC en {path}. "
            "Génerálo con notebooks/003_STAC_build.ipynb."
        )
    return pystac.Catalog.from_file(str(path))


def levels_items() -> dict[int, pystac.Item]:
    """{año: item} de los productos horas-por-nivel en la colección ``utci``."""
    col = open_catalog().get_child("utci")
    items: dict[int, pystac.Item] = {}
    for it in col.get_items():
        m = _LEVELS_ID.match(it.id)
        if m:
            items[int(m.group(1))] = it
    return dict(sorted(items.items()))


def available_years() -> list[int]:
    """Años con producto de niveles; puebla el selector de año de la UI."""
    return list(levels_items())


@functools.lru_cache(maxsize=4)
def open_levels(year: int) -> xr.Dataset:
    """Dataset de horas por nivel de un año, resuelto vía el asset del item."""
    item = levels_items().get(year)
    if item is None:
        raise KeyError(
            f"Sin producto utci-levels para {year}. Años disponibles: {available_years()}"
        )
    return xr.open_dataset(item.assets["data"].get_absolute_href())


def hours_field(year: int, level: int) -> xr.DataArray:
    """Campo 2D (lat, lon) de horas/año en el nivel de estrés dado."""
    return open_levels(year)["hours"].sel(level=level).load()


def hours_at(lat: float, lon: float, year: int) -> xr.DataArray:
    """Horas/año por nivel (dim ``level``) en la celda más cercana a (lat, lon)."""
    return open_levels(year)["hours"].sel(lat=lat, lon=lon, method="nearest").load()


# --------------------------------------------------------------------------
# Colección ``inegi`` (productos MEDI, Censo 2020)
# --------------------------------------------------------------------------


def medi_items() -> dict[tuple[str, int], pystac.Item]:
    """{(nivel, año): item} de los productos MEDI; vacío si no hay colección."""
    col = open_catalog().get_child("inegi")
    if col is None:
        return {}
    items: dict[tuple[str, int], pystac.Item] = {}
    for it in col.get_items():
        m = _MEDI_ID.match(it.id)
        if m:
            items[(m.group(1), int(m.group(2)))] = it
    return dict(sorted(items.items()))


def available_medi_years(level: str = "ageb") -> list[int]:
    """Años con producto MEDI del nivel dado; puebla el selector de la UI."""
    return sorted(y for (lv, y) in medi_items() if lv == level)


def medi_item(level: str, year: int) -> pystac.Item:
    item = medi_items().get((level, year))
    if item is None:
        raise KeyError(
            f"Sin producto medi-{level} para {year}. Disponibles: {list(medi_items())}"
        )
    return item


def medi_indicators(year: int) -> list[dict[str, Any]]:
    """Indicadores publicados en el item AGEB (``atlas:indicators``).

    Cada uno trae ``id``, ``label``, ``column`` (porcentaje), ``flag_column``,
    ``upper_bound_column`` (o None), ``weight_medi``, ``numerator`` y
    ``denominator``. La UI no debe hardcodear indicadores: los lee de aquí.
    """
    return list(medi_item("ageb", year).properties.get("atlas:indicators", []))


def medi_path(level: str, year: int) -> Path:
    """Ruta absoluta del parquet del producto (resuelta vía el asset ``data``)."""
    return Path(medi_item(level, year).assets["data"].get_absolute_href())


def read_medi(
    level: str,
    year: int,
    columns: list[str] | None = None,
    bbox: tuple[float, float, float, float] | None = None,
) -> gpd.GeoDataFrame | pd.DataFrame:
    """Lee un producto MEDI.

    - ``ageb`` y ``mun`` devuelven GeoDataFrame (EPSG:4326). ``bbox`` =
      (oeste, sur, este, norte) filtra por la columna de bbox del GeoParquet
      sin cargar el archivo entero (lo que necesita la capa AGEB por ventana).
    - ``grid`` devuelve DataFrame (sin geometría).
    """
    path = medi_path(level, year)
    if level == "grid":
        return pd.read_parquet(path, columns=columns)
    if columns is not None and "geometry" not in columns:
        columns = [*columns, "geometry"]
    return gpd.read_parquet(path, columns=columns, bbox=bbox)


@functools.lru_cache(maxsize=4)
def open_medi_grid(year: int) -> pd.DataFrame:
    """Tabla puente AGEB → celda UTCI (cacheada; ~1 MB)."""
    return read_medi("grid", year)


def medi_at(lat: float, lon: float, year: int) -> dict[str, Any]:
    """Resumen MEDI de la celda UTCI de 0.25° más cercana a (lat, lon).

    Suma numerador y denominador sobre las AGEB no censuradas de la celda.
    Devuelve ``n_ageb``, ``pobtot`` y, por indicador, ``<id>`` (porcentaje o
    None) y ``<id>_n`` (AGEB usadas).
    """
    res = config.GRID_RES_DEG
    lat_c = round(round(lat / res) * res, 2)
    lon_c = round(round(lon / res) * res, 2)
    g = open_medi_grid(year)
    sel = g[(g["lat_c"] == lat_c) & (g["lon_c"] == lon_c)]
    out: dict[str, Any] = {
        "lat_c": lat_c,
        "lon_c": lon_c,
        "n_ageb": int(len(sel)),
        "pobtot": int(sel["pobtot"].sum()) if len(sel) else 0,
    }
    for ind in medi_indicators(year):
        ok = sel[sel[ind["flag_column"]] == "ok"]
        den = float(ok[ind["denominator"]].sum()) if len(ok) else 0.0
        out[ind["id"]] = (
            round(float(ok[ind["numerator"]].sum()) / den * 100, 2) if den > 0 else None
        )
        out[ind["id"] + "_n"] = int(len(ok))
    return out
