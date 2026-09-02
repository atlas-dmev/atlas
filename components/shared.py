from ipyleaflet import basemaps

from atlas import indices

# Niveles de estrés UTCI para la vista de horas anuales: {etiqueta -> idx 0..9}.
LEVELS = {c.label: c.idx for c in indices.UTCI_STRESS}


BASEMAPS = {
    "WorldImagery": basemaps.Esri.WorldImagery,
    "Positron": basemaps.CartoDB.Positron,
    "DarkMatter": basemaps.CartoDB.DarkMatter,
    "Mapnik": basemaps.OpenStreetMap.Mapnik,
    "NatGeoWorldMap": basemaps.Esri.NatGeoWorldMap,
}
