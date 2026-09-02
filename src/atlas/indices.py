"""Escala de estrés térmico UTCI: categorías, colores y clasificación puntual."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class StressCategory:
    """Una clase de estrés térmico con su rango [lo, hi) en °C y color."""

    idx: int
    label: str
    lo: float  # límite inferior inclusivo (°C)
    hi: float  # límite superior exclusivo (°C)
    color: str  # hex para el mapa/leyenda


# Escala UTCI estándar de ECMWF (10 clases), etiquetas en español, paleta azul→rojo.
UTCI_STRESS: tuple[StressCategory, ...] = (
    StressCategory(0, "Estrés por frío extremo", -np.inf, -40, "#053061"),
    StressCategory(1, "Estrés por frío muy fuerte", -40, -27, "#2166ac"),
    StressCategory(2, "Estrés por frío fuerte", -27, -13, "#4393c3"),
    StressCategory(3, "Estrés por frío moderado", -13, 0, "#92c5de"),
    StressCategory(4, "Estrés por frío ligero", 0, 9, "#d1e5f0"),
    StressCategory(5, "Sin estrés térmico", 9, 26, "#d9f0d3"),
    StressCategory(6, "Estrés por calor moderado", 26, 32, "#fddbc7"),
    StressCategory(7, "Estrés por calor fuerte", 32, 38, "#f4a582"),
    StressCategory(8, "Estrés por calor muy fuerte", 38, 46, "#d6604d"),
    StressCategory(9, "Estrés por calor extremo", 46, np.inf, "#b2182b"),
)

# Cortes internos para np.digitize (los hi de todas menos la última).
_UTCI_BINS = [c.hi for c in UTCI_STRESS[:-1]]


def utci_category(value: float) -> StressCategory:
    """Categoría de estrés para un valor escalar de UTCI (°C)."""
    return UTCI_STRESS[int(np.digitize(value, _UTCI_BINS))]
