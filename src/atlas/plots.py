"""Figuras por celda (consumidas por la app).

Mantiene el ploteo fuera de la capa Shiny: ``components.servers`` solo llama a
``level_distribution(...)`` y devuelve la figura desde ``@render.plot``.
"""

from __future__ import annotations

import functools

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from atlas import stac
from atlas.indices import UTCI_STRESS


def level_distribution(lat: float, lon: float, year: int) -> plt.Figure:
    """Barras horizontales: horas/año en cada nivel de estrés para una celda."""
    horas = stac.hours_at(lat, lon, year)
    clat, clon = float(horas["lat"]), float(horas["lon"])
    vals = horas.values

    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    y = np.arange(len(UTCI_STRESS))
    ax.barh(y, vals, color=[c.color for c in UTCI_STRESS], edgecolor="#999", lw=0.5)
    ax.set_yticks(y)
    ax.set_yticklabels([c.label for c in UTCI_STRESS], fontsize=7)
    ax.invert_yaxis()  # frío arriba, calor abajo: mismo orden que la escala
    for yi, v in zip(y, vals):
        if v > 0:
            ax.text(v, yi, f" {int(v):,}", va="center", fontsize=7, color="#333")
    ax.set_xlabel("horas/año")
    ax.set_xlim(0, float(vals.max()) * 1.18)  # aire para las etiquetas
    ax.set_title(f"Horas por nivel · celda ({clat:.2f}, {clon:.2f}) · {year}", fontsize=9)
    fig.tight_layout()
    return fig


@functools.lru_cache(maxsize=16)
def _hours_by_unit(year: int, level: int, nivel: str) -> pd.DataFrame:
    """Horas/año en ``level`` de la celda UTCI del centroide de cada estado/municipio."""
    u = pd.read_parquet(stac.medi_path(nivel, year_medi_default()), columns=["cvegeo", "pobtot", "cent_lat", "cent_lon"])
    field = stac.hours_field(year, level)
    h = field.sel(
        lat=xr.DataArray(u["cent_lat"].to_numpy(), dims="u"),
        lon=xr.DataArray(u["cent_lon"].to_numpy(), dims="u"),
        method="nearest",
    )
    u["horas"] = np.asarray(h.values, dtype="float64")
    return u


def year_medi_default() -> int:
    return stac.available_medi_years("mun")[-1]


def socio_scatter(year: int, level: int, medi_year: int, ind: dict, nivel: str, nivel_label: str) -> plt.Figure:
    """Dispersión: horas/año en el nivel UTCI (celda del centroide) vs indicador MEDI.

    Cada punto es un municipio o estado; el área es proporcional a la
    población. Se reporta la correlación de Spearman (monótona, robusta).
    """
    u = _hours_by_unit(year, level, nivel)
    col = ind["column"]
    v = pd.read_parquet(stac.medi_path(nivel, medi_year), columns=["cvegeo", col]).merge(u, on="cvegeo")
    v = v.dropna(subset=[col, "horas"])
    fig, ax = plt.subplots(figsize=(4.6, 2.9))
    if len(v) < 3:
        ax.text(0.5, 0.5, "sin datos suficientes", ha="center", va="center", color="#666")
        ax.axis("off")
        return fig
    size = 4 + 60 * np.sqrt(v["pobtot"] / v["pobtot"].max())
    ax.scatter(v["horas"], v[col], s=size, alpha=0.35, color="#3b528b", edgecolor="none")
    rho = float(v["horas"].corr(v[col], method="spearman"))
    unidad = ind.get("unit", "%")
    ax.set_xlabel(f"horas/año · {nivel_label} · {year}", fontsize=7)
    ax.set_ylabel(f"{ind['id']} ({unidad})", fontsize=7)
    ax.tick_params(labelsize=7)
    nombre = {"mun": "municipios", "ent": "estados"}[nivel]
    ax.set_title(f"{len(v):,} {nombre} · Spearman ρ = {rho:+.2f} · tamaño ∝ población", fontsize=8)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    return fig


def placeholder(mensaje: str) -> plt.Figure:
    """Figura vacía con un mensaje (estado inicial antes del primer clic)."""
    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    ax.text(0.5, 0.5, mensaje, ha="center", va="center", fontsize=11, color="#666")
    ax.axis("off")
    fig.tight_layout()
    return fig
