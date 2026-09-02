"""Figuras por celda (consumidas por la app).

Mantiene el ploteo fuera de la capa Shiny: ``components.servers`` solo llama a
``level_distribution(...)`` y devuelve la figura desde ``@render.plot``.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

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


def placeholder(mensaje: str) -> plt.Figure:
    """Figura vacía con un mensaje (estado inicial antes del primer clic)."""
    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    ax.text(0.5, 0.5, mensaje, ha="center", va="center", fontsize=11, color="#666")
    ax.axis("off")
    fig.tight_layout()
    return fig
