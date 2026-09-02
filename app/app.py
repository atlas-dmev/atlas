import sys
from pathlib import Path

# Permite `shiny run app/app.py` desde cualquier cwd: la raíz del repo debe estar
# en sys.path para importar el paquete de UI `components`.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shiny import App
from shinywidgets import output_widget

from atlas import stac
from components.shared import BASEMAPS, LEVELS
from components.panels import (
    cell_footer,
    legend_panel,
    page_two_sidebars,
    select_basemap,
    select_level,
    select_year,
    sidebar_left,
    sidebar_right,
    socio_panel,
)
from components.servers import map_server, socio_server

# Años con producto de niveles, descubiertos en el STAC (no hardcodeados).
_ANIOS = stac.available_years()
# Productos MEDI (INEGI): años e indicadores publicados en la colección `inegi`.
_ANIOS_MEDI = stac.available_medi_years()
_INDICADORES = stac.medi_indicators(_ANIOS_MEDI[-1]) if _ANIOS_MEDI else []

app_ui = page_two_sidebars(
    left=sidebar_left(
        select_basemap(BASEMAPS),
        select_level(LEVELS, selected="Estrés por calor fuerte"),
        select_year(_ANIOS),
        legend_panel(),
    ),
    right=sidebar_right(
        socio_panel(_INDICADORES, _ANIOS_MEDI),
    ),
    main=output_widget("map"),
    footer=cell_footer(with_medi=bool(_INDICADORES)),
)


def server(input, output, session):
    base_map, clic = map_server(input)
    if _INDICADORES:
        socio_server(input, base_map, clic)


app = App(app_ui, server)
