"""Rasterización del campo de horas/año a PNG para el mapa (ImageOverlay).

Colorea con una rampa secuencial hacia el color del nivel de estrés y devuelve
un *data URI* PNG listo para ``ipyleaflet.ImageOverlay``, junto con los
``bounds`` geográficos (extendidos media celda para alinear con los bordes,
no los centros).
"""

from __future__ import annotations

import base64
import io

import numpy as np
import xarray as xr
from matplotlib.colors import LinearSegmentedColormap, to_rgb
from PIL import Image

from atlas import config, indices, stac
from atlas.indices import StressCategory

_HOURS_LEGEND_BINS = 5


def field_bounds(field: xr.DataArray) -> tuple[tuple[float, float], tuple[float, float]]:
    """Bounds ((sur, oeste), (norte, este)) extendidos media celda."""
    h = config.GRID_RES_DEG / 2.0
    return (
        (float(field["lat"].min()) - h, float(field["lon"].min()) - h),
        (float(field["lat"].max()) + h, float(field["lon"].max()) + h),
    )


def _hours_cmap(category: StressCategory) -> LinearSegmentedColormap:
    """Rampa secuencial blanco -> color de la categoría -> oscurecido.

    Mantiene la identidad visual del nivel (mismo color que la escala UTCI)
    y da contraste en la cola alta aunque la categoría sea clara.
    """
    r, g, b = to_rgb(category.color)
    dark = (r * 0.45, g * 0.45, b * 0.45)
    return LinearSegmentedColormap.from_list(
        f"hours_{category.idx}", ["#ffffff", category.color, dark]
    )


def _hours_vmax(field: xr.DataArray) -> int:
    """Techo de la escala: máximo del campo redondeado a la centena superior."""
    vmax = float(field.max())
    return max(100, int(np.ceil(vmax / 100.0)) * 100)


def hours_overlay(
    field: xr.DataArray,
    category: StressCategory,
) -> tuple[str, tuple[tuple[float, float], tuple[float, float]]]:
    """(data_uri_png, bounds) para un campo de horas/año de un nivel.

    Escala 0..vmax con la rampa del nivel; celdas con 0 horas (o sin dato)
    quedan transparentes para que solo pinte donde el nivel ocurre.
    """
    field = field.sortby("lat")  # el NetCDF de niveles trae lat descendente
    cmap = _hours_cmap(category)
    vmax = _hours_vmax(field)
    data = np.asarray(field.values, dtype="float64")
    rgba = (cmap(np.clip(data / vmax, 0.0, 1.0)) * 255).astype(np.uint8)
    rgba[np.isnan(data) | (data == 0), 3] = 0
    # lat asciende tras el sortby; una imagen tiene la fila 0 arriba (norte).
    rgba = np.flipud(rgba)

    buf = io.BytesIO()
    Image.fromarray(rgba, mode="RGBA").save(buf, format="PNG")
    uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    return uri, field_bounds(field)


def hours_overlay_for(
    year: int,
    level: int,
) -> tuple[str, tuple[tuple[float, float], tuple[float, float]]]:
    """Overlay de horas/año para (año, nivel), leyendo el producto vía el STAC."""
    field = stac.hours_field(year, level)
    return hours_overlay(field, indices.UTCI_STRESS[level])


def hours_legend_items(year: int, level: int) -> list[tuple[str, str]]:
    """[(rango de horas, color hex)] para la leyenda del mapa de horas/año."""
    category = indices.UTCI_STRESS[level]
    field = stac.hours_field(year, level)
    vmax = _hours_vmax(field)
    cmap = _hours_cmap(category)
    step = vmax // _HOURS_LEGEND_BINS
    items = []
    for i in range(_HOURS_LEGEND_BINS):
        lo, hi = i * step, (i + 1) * step
        color = cmap((i + 0.5) / _HOURS_LEGEND_BINS)
        hexcolor = "#{:02x}{:02x}{:02x}".format(*(int(c * 255) for c in color[:3]))
        items.append((f"{lo:,} – {hi:,} h", hexcolor))
    return items
