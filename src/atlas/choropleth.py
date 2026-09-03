"""Coropletas de los productos MEDI (INEGI) para el mapa (``ipyleaflet.GeoJSON``).

Análogo a ``render.py`` para el raster UTCI: convierte un producto vectorial
del STAC en un GeoJSON estilizado por clases (cuantiles nacionales, fijos
para un (nivel, año, indicador)) más los items de su leyenda.

Decisiones:

- Estados y municipios se **simplifican al vuelo** una sola vez (500 m en
  EPSG:6372, precisión 1e-4°) y se cachean: ~3 MB de GeoJSON municipal, ~1 s.
- La capa AGEB se sirve **por ventana**: sólo las AGEB cuyo bbox cae en la
  vista del mapa (filtro sobre la columna bbox del GeoParquet, ~0.03 s) y a
  partir de ``AGEB_ZOOM_MIN``; se simplifican a medio píxel del zoom actual.
  Las clases (cuantiles) se calculan una vez sobre el producto nacional AGEB
  para que los colores sean comparables entre ciudades.
- Rampa neutra (viridis) para no competir con la rampa del nivel UTCI.
- Valores nulos (censurados o sin viviendas) se pintan en gris claro y se
  cuentan en la leyenda; el tooltip muestra la bandera y, en electricidad,
  la cota superior; para los indicadores del Cuestionario ampliado muestra el
  coeficiente de variación y su calidad (regla INEGI).
"""

from __future__ import annotations

import functools
import math
from typing import Any

import geopandas as gpd
import mapclassify
import numpy as np
import pandas as pd
import shapely
from matplotlib import colormaps
from matplotlib.colors import to_hex

from atlas import stac

CMAP = "viridis"
N_CLASSES = 6
MISSING_COLOR = "#bdbdbd"
SIMPLIFY_TOL_M = 500.0          # estados y municipios (una vez, nacional)
COORD_PRECISION = 1e-4          # estados y municipios
AGEB_ZOOM_MIN = 10              # por debajo se muestra el municipal (medido: CDMX 4.3 MB, Oaxaca rural 1.1 MB por ventana)
AGEB_COORD_PRECISION = 1e-5     # ~1 m
AGEB_MAX_FEATURES = 8000        # tope de seguridad por ventana
_EPSG_METRIC = 6372
_M_PER_DEG_EQ = 111_320.0

POLYGON_LEVELS = ("ent", "mun")  # niveles que se dibujan completos (nacional)

# Columnas que viajan en las propiedades de cada feature (tooltip + estilo).
_PROPS = {
    "ent": ["cvegeo", "nom_ent", "pobtot", "vivparh_cv"],
    "mun": ["cvegeo", "nom_ent", "nom_mun", "pobtot", "vivparh_cv"],
    "ageb": ["cvegeo", "nom_ent", "nom_mun", "nom_loc", "pobtot", "vivparh_cv", "origen_ampliado",
             "ambito", "n_localidades", "n_loc_sin_dato"],
}
RURAL_OPACITY = 0.45            # fracción de la opacidad del slider para AGEB rurales (polígonos grandes)


def _indicator(year: int, indicator_id: str, level: str) -> dict[str, Any]:
    for ind in stac.medi_indicators(year, level):
        if ind["id"] == indicator_id:
            return ind
    raise KeyError(f"Indicador {indicator_id!r} no publicado para {level} {year}")


def _indicator_columns(year: int, level: str) -> list[str]:
    cols: list[str] = []
    for ind in stac.medi_indicators(year, level):
        for key in ("column", "flag_column", "upper_bound_column", "cv_column", "quality_column"):
            if ind.get(key):
                cols.append(ind[key])
    return list(dict.fromkeys(cols))


def _extra_columns(ind: dict[str, Any]) -> list[str]:
    return [ind[k] for k in ("flag_column", "upper_bound_column", "cv_column", "quality_column") if ind.get(k)]


@functools.lru_cache(maxsize=8)
def _available_columns(level: str, year: int) -> frozenset[str]:
    """Columnas presentes en el parquet del producto (para no pedir las que aún no existen)."""
    import pyarrow.parquet as pq

    return frozenset(pq.ParquetFile(stac.medi_path(level, year)).schema_arrow.names)


def _existing(level: str, year: int, cols: list[str]) -> list[str]:
    ok = _available_columns(level, year)
    return [c for c in dict.fromkeys(cols) if c in ok]


@functools.lru_cache(maxsize=4)
def polygon_frame(level: str, year: int) -> gpd.GeoDataFrame:
    """Estados o municipios con geometría simplificada (cacheado por nivel y año)."""
    assert level in POLYGON_LEVELS, level
    cols = _existing(level, year, _PROPS[level] + _indicator_columns(year, level))
    g = stac.read_medi(level, year, columns=cols)
    s = g.to_crs(_EPSG_METRIC)
    s["geometry"] = s.geometry.simplify(SIMPLIFY_TOL_M, preserve_topology=True)
    s = s.to_crs(4326)
    geoms = shapely.make_valid(shapely.set_precision(s.geometry.values, COORD_PRECISION))
    # Redondear los flotantes para que el JSON no arrastre dígitos espurios.
    decimales = int(round(-math.log10(COORD_PRECISION)))
    s["geometry"] = shapely.transform(geoms, lambda c: np.round(c, decimales))
    return s.set_index("cvegeo", drop=False)


def municipal_frame(year: int) -> gpd.GeoDataFrame:
    return polygon_frame("mun", year)


def _quantile_scheme(vals: np.ndarray, k: int = N_CLASSES) -> tuple[list[float], list[str]]:
    """Cortes por cuantiles con clase aparte para el cero.

    Indicadores como "sin electricidad" tienen mayoría de ceros: los
    cuantiles colapsan. Si más de 1/k de los valores son 0, la primera clase
    es exactamente 0 y el resto se reparte por cuantiles entre los positivos.
    """
    vals = vals[~np.isnan(vals)]
    if len(vals) == 0:
        return [0.0], [MISSING_COLOR]
    zeros = float((vals == 0).mean())
    bins: list[float] = []
    if zeros > 1.0 / k:
        bins.append(0.0)
        pos = vals[vals > 0]
        kk = min(k - 1, max(1, len(np.unique(pos))))
        if len(pos):
            bins += [float(b) for b in mapclassify.Quantiles(pos, k=kk).bins]
    else:
        kk = min(k, max(1, len(np.unique(vals))))
        bins = [float(b) for b in mapclassify.Quantiles(vals, k=kk).bins]
    cmap = colormaps[CMAP]
    n = len(bins)
    colors = [to_hex(cmap((i + 0.5) / n)) for i in range(n)]
    return bins, colors


@functools.lru_cache(maxsize=32)
def classes(year: int, indicator_id: str, level: str = "mun") -> tuple[list[float], list[str]]:
    """(cortes superiores de cada clase, colores hex) por cuantiles nacionales del nivel."""
    col = _indicator(year, indicator_id, level)["column"]
    if level in POLYGON_LEVELS:
        vals = polygon_frame(level, year)[col].to_numpy(dtype="float64")
    else:
        vals = pd.read_parquet(stac.medi_path(level, year), columns=[col])[col].to_numpy(dtype="float64")
    return _quantile_scheme(vals)


@functools.lru_cache(maxsize=32)
def _stats(year: int, indicator_id: str, level: str) -> tuple[float, int]:
    """(mínimo, n_nulos) del indicador en el producto nacional del nivel."""
    col = _indicator(year, indicator_id, level)["column"]
    if level in POLYGON_LEVELS:
        v = polygon_frame(level, year)[col]
    else:
        v = pd.read_parquet(stac.medi_path(level, year), columns=[col])[col]
    return float(np.nanmin(v.to_numpy(dtype="float64"))), int(v.isna().sum())


def color_for(value: float | None, bins: list[float], colors: list[str]) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return MISSING_COLOR
    for b, c in zip(bins, colors):
        if value <= b:
            return c
    return colors[-1]


def _nan_none(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def _features(frame: gpd.GeoDataFrame, ind: dict[str, Any], bins: list[float], colors: list[str],
              opacity: float, props_cols: list[str]) -> list[dict[str, Any]]:
    """Features GeoJSON con ``style`` por feature (lo respeta ipyleaflet.GeoJSON)."""
    col = ind["column"]
    extras = [c for c in _extra_columns(ind) if c in frame.columns]
    props_cols = [c for c in props_cols if c in frame.columns]
    # mapping() da tuplas de floats ya redondeados: JSON corto (to_geojson de
    # GEOS escribe 16 dígitos y duplica el tamaño).
    geoms = [shapely.geometry.mapping(g) for g in frame.geometry.values]
    rows = frame[list(dict.fromkeys(props_cols + [col] + extras))].to_dict("records")
    features = []
    for row, geom in zip(rows, geoms):
        value = _nan_none(row[col])
        props: dict[str, Any] = {k: _nan_none(row[k]) if k in ("n_localidades", "n_loc_sin_dato") else row[k]
                                 for k in props_cols if k not in ("pobtot", "vivparh_cv")}
        props["pobtot"] = int(row["pobtot"])
        viv = _nan_none(row.get("vivparh_cv"))
        props["vivparh_cv"] = int(viv) if viv is not None else None
        props["valor"] = value
        props["flag"] = row.get(ind["flag_column"]) if ind.get("flag_column") else None
        props["cota_sup"] = _nan_none(row.get(ind["upper_bound_column"])) if ind.get("upper_bound_column") else None
        props["cv"] = _nan_none(row.get(ind["cv_column"])) if ind.get("cv_column") else None
        props["calidad"] = row.get(ind["quality_column"]) if ind.get("quality_column") else None
        poco_preciso = props["calidad"] == "poco_preciso"
        rural = props.get("ambito") == "rural"
        op = opacity * (RURAL_OPACITY if rural else 1.0)
        props["style"] = {
            "fillColor": color_for(value, bins, colors),
            "fillOpacity": op if value is not None else op * 0.5,
            "color": "#555555" if not poco_preciso else "#b30000",
            "weight": 0.4 if not poco_preciso else 0.9,
            "opacity": 0.6,
            "dashArray": "3 2" if (poco_preciso or rural) else None,
        }
        # JSON no admite NaN: cualquier float NaN (p. ej. nom_loc de una AGEB rural) → null
        props = {k: (None if isinstance(v, float) and math.isnan(v) else v) for k, v in props.items()}
        features.append({"type": "Feature", "id": row["cvegeo"], "properties": props, "geometry": geom})
    return features


def polygon_geojson(level: str, year: int, indicator_id: str, opacity: float = 0.65) -> dict[str, Any]:
    """FeatureCollection nacional (estados o municipios) para un indicador."""
    ind = _indicator(year, indicator_id, level)
    bins, colors = classes(year, indicator_id, level)
    frame = polygon_frame(level, year)
    return {"type": "FeatureCollection", "features": _features(frame, ind, bins, colors, opacity, _PROPS[level])}


def municipal_geojson(year: int, indicator_id: str, opacity: float = 0.65) -> dict[str, Any]:
    return polygon_geojson("mun", year, indicator_id, opacity)


# --------------------------------------------------------------------------
# AGEB por ventana
# --------------------------------------------------------------------------


def ageb_classes(year: int, indicator_id: str) -> tuple[list[float], list[str]]:
    return classes(year, indicator_id, "ageb")


def simplify_tolerance_m(zoom: int, lat: float, px: float = 0.5) -> float:
    """Metros por ``px`` píxeles en el zoom dado (Web Mercator) a la latitud ``lat``."""
    deg_per_px = 360.0 / (256 * 2**zoom)
    return deg_per_px * _M_PER_DEG_EQ * math.cos(math.radians(lat)) * px


def ageb_geojson(
    year: int,
    indicator_id: str,
    bbox: tuple[float, float, float, float],
    zoom: int,
    opacity: float = 0.65,
) -> tuple[dict[str, Any], int]:
    """(FeatureCollection de las AGEB dentro de ``bbox``, n_total_en_ventana).

    ``bbox`` = (oeste, sur, este, norte) en grados. Si la ventana tiene más
    de ``AGEB_MAX_FEATURES`` AGEB se devuelven sólo las primeras (el
    llamador decide avisar); la geometría se simplifica a medio píxel.
    """
    ind = _indicator(year, indicator_id, "ageb")
    bins, colors = classes(year, indicator_id, "ageb")
    cols = _existing("ageb", year, _PROPS["ageb"] + [ind["column"]] + _extra_columns(ind))
    g = stac.read_medi("ageb", year, columns=cols, bbox=bbox)
    n_total = len(g)
    if n_total == 0:
        return {"type": "FeatureCollection", "features": []}, 0
    if n_total > AGEB_MAX_FEATURES:
        g = g.iloc[:AGEB_MAX_FEATURES]
    lat_c = (bbox[1] + bbox[3]) / 2.0
    tol = simplify_tolerance_m(zoom, lat_c)
    s = g.to_crs(_EPSG_METRIC)
    s["geometry"] = s.geometry.simplify(tol, preserve_topology=True)
    s = s.to_crs(4326)
    geoms = shapely.make_valid(shapely.set_precision(s.geometry.values, AGEB_COORD_PRECISION))
    decimales = int(round(-math.log10(AGEB_COORD_PRECISION)))
    s["geometry"] = shapely.transform(geoms, lambda c: np.round(c, decimales))
    s = s[~s.geometry.is_empty]
    return {"type": "FeatureCollection", "features": _features(s, ind, bins, colors, opacity, _PROPS["ageb"])}, n_total


# --------------------------------------------------------------------------
# Leyenda
# --------------------------------------------------------------------------


def class_labels(bins: list[float], lo: float, unit: str = "%") -> list[str]:
    """Etiquetas de clase; una primera clase con corte 0 se etiqueta "0"."""
    labels: list[str] = []
    zero_class = bool(bins) and bins[0] == 0.0
    u = f" {unit}" if unit else ""
    for i, b in enumerate(bins):
        if i == 0 and zero_class:
            labels.append(f"0{u}")
        elif i == 1 and zero_class:
            labels.append(f"> 0 – {b:.1f}{u}")
        else:
            labels.append(f"{lo:.1f} – {b:.1f}{u}")
        lo = b
    return labels


def legend_items(year: int, indicator_id: str, level: str = "mun") -> tuple[list[tuple[str, str]], int]:
    """([(etiqueta, color)], n_nulos) para la leyenda del panel; ``level`` = ent | mun | ageb."""
    ind = _indicator(year, indicator_id, level)
    bins, colors = classes(year, indicator_id, level)
    lo, n_missing = _stats(year, indicator_id, level)
    return list(zip(class_labels(bins, lo, ind.get("unit", "%")), colors)), n_missing
