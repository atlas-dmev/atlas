from shiny import ui


def select_level(levels_labels, selected=None):
    return ui.input_selectize(
        "nivel",
        "Nivel de estrés",
        choices=list(levels_labels),
        selected=selected or list(levels_labels)[0],
    )


def select_year(years, selected=None):
    choices = [str(y) for y in years]
    return ui.input_selectize(
        "anio",
        "Año",
        choices=choices,
        selected=selected or (choices[-1] if choices else None),
    )


def select_basemap(BASEMAPS):
    return ui.input_selectize(
        "basemap",
        "Mapa base",
        choices=list(BASEMAPS.keys()),
        selected="NatGeoWorldMap",
    )


def legend_panel():
    return ui.output_ui("leyenda")


def cell_footer(with_medi: bool = False):
    """Footer a lo ancho del layout: al hacer clic en una celda del mapa
    muestra su distribución de horas/año por nivel y, si hay productos MEDI,
    el resumen socioeconómico de las AGEB de esa celda (cruce UTCI × INEGI)."""
    cuerpo = [ui.output_plot("serie", height="200px")]
    if with_medi:
        cuerpo = [
            ui.div(ui.output_plot("serie", height="200px"), style="flex:1 1 auto;min-width:0;"),
            ui.div(
                ui.output_ui("celda_medi"),
                style="flex:0 0 340px;border-left:1px solid #ddd;padding-left:14px;margin-left:12px;overflow:auto;",
            ),
        ]
    return ui.div(
        ui.output_text("celda_info"),
        ui.div(*cuerpo, style="display:flex;align-items:stretch;height:200px;"),
        style=(
            "flex:0 0 auto;height:240px;background:#f8f8f8;"
            "border-top:1px solid #ddd;padding:6px 16px 8px;"
            "font-size:12px;color:#333;"
        ),
    )


def socio_panel(indicators, years):
    """Panel derecho — capa socioeconómica (INEGI, MEDI).

    ``indicators`` viene de ``stac.medi_indicators(año)`` (id -> etiqueta) y
    ``years`` de ``stac.available_medi_years()``; nada se hardcodea aquí.
    """
    if not indicators:
        return ui.div(
            ui.tags.b("Indicadores socioeconómicos"),
            ui.tags.p(
                "No hay productos MEDI en el STAC. Corre notebooks/004–007.",
                style="font-size:12px;color:#666;",
            ),
        )
    year_choices = [str(y) for y in years]
    return ui.div(
        ui.tags.b("Indicadores socioeconómicos (INEGI)"),
        ui.input_checkbox("socio_on", "Mostrar capa", value=True),
        ui.input_selectize(
            "socio_ind",
            "Indicador",
            choices={i["id"]: i["label"] for i in indicators},
            selected=indicators[0]["id"],
        ),
        ui.input_selectize("socio_anio", "Censo", choices=year_choices, selected=year_choices[-1]),
        ui.input_selectize(
            "socio_nivel",
            "Nivel",
            choices={"mun": "Municipio", "ageb": "AGEB urbana (al acercar)"},
            selected="mun",
        ),
        ui.input_slider("socio_opacidad", "Opacidad", min=0.1, max=1.0, value=0.65, step=0.05),
        ui.output_ui("socio_aviso"),
        ui.output_ui("socio_leyenda"),
        ui.output_ui("socio_hover"),
        ui.tags.p(
            "Municipio: totales del Censo 2020 (urbano + rural). AGEB: sólo AGEB "
            "urbanas, cargadas para la ventana visible al acercar el mapa. "
            "Gris: dato censurado por INEGI (< 3 viviendas) o sin viviendas.",
            style="font-size:11px;color:#666;margin-top:10px;",
        ),
    )


def sidebar_left(*args):
    return ui.sidebar(*args, bg="#f8f8f8", open="always", width=340)


def sidebar_right(*args):
    return ui.sidebar(*args, position="right", bg="#f8f8f8", open="always", width=320)


# Renderizado pixelado (nearest-neighbor) de la capa de imagen del mapa: cada
# celda de 0.25° se ve como un bloque nítido, sin suavizado/interpolación del
# navegador. Deja claro que los datos están discretizados al grid.
_DISCRETE_RASTER_CSS = ui.tags.style(
    ".leaflet-image-layer{"
    "image-rendering:pixelated;"
    "image-rendering:-moz-crisp-edges;"
    "image-rendering:crisp-edges;"
    "}"
)


def page_two_sidebars(left, main, right, footer=None):
    """Sidebars izquierda/derecha flanqueando el mapa; footer opcional a lo
    ancho de la parte inferior del layout."""
    cuerpo = ui.layout_sidebar(
        left,
        ui.layout_sidebar(right, main),
    )
    hijos = [cuerpo] if footer is None else [cuerpo, footer]
    return ui.page_fillable(
        _DISCRETE_RASTER_CSS,
        *hijos,
        padding=0,
        gap=0,
    )
