import ipyleaflet as L
from htmltools import HTML, div
from shiny import reactive, render, ui
from shinywidgets import render_widget

from atlas import choropleth, plots, stac
from atlas import render as atlas_render
from components.shared import BASEMAPS, LEVELS

# Centro y zoom para encuadrar México.
_MX_CENTER = (23.5, -102.5)
_MX_ZOOM = 5

# Panes propios para fijar el orden de dibujo sin depender del orden en que
# se (re)agregan las capas: el raster UTCI va debajo (z=350) del overlayPane
# de Leaflet (z=400), donde el renderer SVG dibuja la coropleta socioeconómica.
_UTCI_PANE = "utci"
_SOCIO_PANE = "socio"
_PANES = {_UTCI_PANE: {"zIndex": 350}, _SOCIO_PANE: {"zIndex": 450}}


def map_server(input):
    """Mapa base + capa UTCI. Devuelve ``(base_map, clic)``: el calc del mapa,
    para que otras capas (p. ej. la socioeconómica) se monten sobre el mismo
    mapa, y el reactive.Value con la última celda pulsada (lat, lon)."""
    # Referencia mutable al ImageOverlay actual para poder reemplazarlo sin
    # reconstruir el mapa (preserva el zoom/paneo del usuario).
    estado = {"overlay": None}
    # Última celda pulsada (lat, lon); None hasta el primer clic.
    clic = reactive.Value(None)

    @reactive.calc
    def base_map():
        """Mapa base; se reconstruye solo al cambiar el mapa base."""
        m = L.Map(center=_MX_CENTER, zoom=_MX_ZOOM, scroll_wheel_zoom=True, panes=_PANES)
        m.add_layer(L.basemap_to_tiles(BASEMAPS[input.basemap()]))
        estado["overlay"] = None  # el mapa nuevo aún no tiene capa de campo

        def _on_click(**kwargs):
            if kwargs.get("type") == "click":
                lat, lon = kwargs["coordinates"]
                clic.set((float(lat), float(lon)))

        m.on_interaction(_on_click)
        return m

    @render_widget
    def map():
        return base_map()

    @reactive.effect
    def _pintar_campo():
        """Recalcula y reemplaza el ImageOverlay al cambiar nivel o año."""
        m = base_map()
        uri, bounds = atlas_render.hours_overlay_for(
            int(input.anio()), LEVELS[input.nivel()]
        )
        nuevo = L.ImageOverlay(url=uri, bounds=bounds, opacity=0.75, pane=_UTCI_PANE)

        anterior = estado["overlay"]
        if anterior is not None and anterior in m.layers:
            m.remove_layer(anterior)
        m.add_layer(nuevo)
        estado["overlay"] = nuevo

    @render.ui
    def leyenda():
        items = atlas_render.hours_legend_items(int(input.anio()), LEVELS[input.nivel()])
        filas = []
        for etiqueta, color in items:
            filas.append(
                div(
                    div(
                        style=f"width:14px;height:14px;background:{color};"
                        "border:1px solid #999;margin-right:8px;flex:none;"
                    ),
                    div(etiqueta, style="font-size:12px;"),
                    style="display:flex;align-items:center;margin-bottom:3px;",
                )
            )
        return div(
            HTML(f"<b>Horas/año — {input.nivel()}</b>"),
            div(*filas, style="margin-top:6px;"),
            style="margin-top:10px;",
        )

    @render.text
    def celda_info():
        c = clic()
        if c is None:
            return "Haz clic en el mapa para ver las horas por nivel."
        horas = stac.hours_at(c[0], c[1], int(input.anio()))
        return f"Celda seleccionada: {float(horas['lat']):.2f}, {float(horas['lon']):.2f}"

    @render.plot
    def serie():
        c = clic()
        if c is None:
            return plots.placeholder("Haz clic en el mapa")
        return plots.level_distribution(c[0], c[1], int(input.anio()))

    return base_map, clic


def socio_server(input, base_map, clic=None):
    """Capa socioeconómica (coropleta MEDI) sobre ``base_map``.

    ``clic`` (reactive.Value con (lat, lon)) alimenta el resumen MEDI de la
    celda UTCI pulsada en el pie de página (cruce UTCI × INEGI).

    Dos niveles: municipal (nacional, siempre disponible) y AGEB urbana
    **por ventana**: a partir de ``choropleth.AGEB_ZOOM_MIN`` se cargan sólo
    las AGEB dentro de la vista y se recargan al mover/acercar el mapa; por
    debajo de ese zoom se muestra el municipal con un aviso. Cambiar
    indicador/opacidad/nivel reemplaza sólo la capa GeoJSON; el mapa (zoom,
    paneo, capa UTCI) no se reconstruye.
    """
    estado = {"layer": None, "map_id": None}
    hover = reactive.Value(None)
    # (zoom, (oeste, sur, este, norte)) de la vista actual; ipyleaflet los
    # actualiza al terminar cada movimiento/zoom (no en cada píxel de arrastre).
    vista = reactive.Value(None)
    # Cuántas AGEB devolvió la última ventana (para el aviso).
    ageb_n = reactive.Value(None)

    def _on_hover(event=None, feature=None, id=None, properties=None, **kwargs):
        if properties is not None:
            hover.set(properties)

    def _on_view(change=None):
        m = base_map()
        b = m.bounds
        if not b or len(b) != 2:
            return
        (s, w), (n, e) = b
        vista.set((int(m.zoom), (float(w), float(s), float(e), float(n))))

    @reactive.effect
    def _observar_vista():
        """Engancha el observador de bounds/zoom una vez por mapa."""
        m = base_map()
        if estado["map_id"] != id(m):
            m.observe(_on_view, names=["bounds", "zoom"])
            estado["map_id"] = id(m)
            vista.set(None)

    @reactive.calc
    def modo():
        """'ent' | 'mun' | 'ageb' | 'ageb_lejos' (AGEB pedido pero zoom insuficiente)."""
        nivel = input.socio_nivel()
        if nivel in ("ent", "mun"):
            return nivel
        v = vista()
        if v is None or v[0] < choropleth.AGEB_ZOOM_MIN:
            return "ageb_lejos"
        return "ageb"

    def nivel_datos() -> str:
        """Nivel del producto que se está pintando (ageb_lejos pinta municipios)."""
        md = modo()
        return "mun" if md == "ageb_lejos" else md

    @reactive.effect
    def _indicadores_por_nivel():
        """La lista de indicadores depende del nivel (cada item STAC publica la suya)."""
        anio, nivel = int(input.socio_anio()), input.socio_nivel()
        inds = stac.medi_indicators(anio, nivel)
        actual = input.socio_ind()
        ids = [i["id"] for i in inds]
        ui.update_selectize(
            "socio_ind",
            choices={i["id"]: i["label"] for i in inds},
            selected=actual if actual in ids else (ids[0] if ids else None),
        )

    def indicador_actual() -> dict | None:
        anio = int(input.socio_anio())
        for i in stac.medi_indicators(anio, nivel_datos()):
            if i["id"] == input.socio_ind():
                return i
        return None

    @reactive.effect
    def _pintar_socio():
        m = base_map()
        anterior = estado["layer"]
        if anterior is not None and anterior in m.layers:
            m.remove_layer(anterior)
        estado["layer"] = None
        hover.set(None)                     # el tooltip no debe mostrar un polígono de la capa anterior
        if not input.socio_on():
            return
        anio, ind, op = int(input.socio_anio()), input.socio_ind(), float(input.socio_opacidad())
        if indicador_actual() is None:      # el selector aún no se actualizó al nivel nuevo
            return
        md = modo()
        if md == "ageb":
            zoom, bbox = vista()
            data, n = choropleth.ageb_geojson(anio, ind, bbox, zoom, op)
            ageb_n.set(n)
            nombre = "MEDI AGEB"
        else:
            data = choropleth.polygon_geojson(nivel_datos(), anio, ind, op)
            nombre = f"MEDI {nivel_datos()}"
        capa = L.GeoJSON(
            data=data,
            hover_style={"weight": 2, "color": "#222222", "fillOpacity": 0.9},
            name=nombre,
            pane=_SOCIO_PANE,
        )
        capa.on_hover(_on_hover)
        m.add_layer(capa)
        estado["layer"] = capa

    @render.ui
    def socio_aviso():
        if not input.socio_on():
            return div()
        md = modo()
        if md == "ageb_lejos":
            return div(
                f"Acércate (zoom ≥ {choropleth.AGEB_ZOOM_MIN}) para ver las AGEB; "
                "mientras tanto se muestra el nivel municipal.",
                style="font-size:12px;color:#8a4b00;background:#fff4e0;padding:6px;border-radius:4px;margin-top:8px;",
            )
        if md == "ageb":
            n = ageb_n() or 0
            extra = ""
            if n > choropleth.AGEB_MAX_FEATURES:
                extra = f" (se dibujan {choropleth.AGEB_MAX_FEATURES:,}; acércate más)"
            return div(f"AGEB en la ventana: {n:,}{extra}", style="font-size:12px;color:#444;margin-top:8px;")
        return div()

    @render.ui
    def socio_leyenda():
        if not input.socio_on():
            return div()
        anio, ind = int(input.socio_anio()), input.socio_ind()
        nivel = nivel_datos()
        info = indicador_actual()
        if info is None:
            return div()
        items, n_missing = choropleth.legend_items(anio, ind, nivel)
        etiqueta = info["label"]
        unidad = {"ageb": "AGEB (urbanas y rurales)", "mun": "municipios", "ent": "estados"}[nivel]
        filas = [
            div(
                div(style=f"width:14px;height:14px;background:{color};border:1px solid #999;margin-right:8px;flex:none;"),
                div(texto, style="font-size:12px;"),
                style="display:flex;align-items:center;margin-bottom:3px;",
            )
            for texto, color in items
        ]
        filas.append(
            div(
                div(style=f"width:14px;height:14px;background:{choropleth.MISSING_COLOR};border:1px solid #999;margin-right:8px;flex:none;"),
                div(f"sin dato ({n_missing:,} {unidad})", style="font-size:12px;"),
                style="display:flex;align-items:center;margin-bottom:3px;",
            )
        )
        return div(
            HTML(f"<b>{etiqueta}</b>"),
            div(f"Clases por cuantiles nacionales ({unidad})", style="font-size:11px;color:#666;"),
            div(*filas, style="margin-top:6px;"),
            style="margin-top:10px;",
        )

    @render.plot
    def socio_dispersion():
        """Horas/año en el nivel UTCI elegido vs indicador socioeconómico, por municipio o estado."""
        info = indicador_actual()
        if info is None or not input.socio_on():
            return plots.placeholder("Capa socioeconómica apagada")
        nivel = nivel_datos()
        if nivel == "ageb":
            nivel = "mun"
        return plots.socio_scatter(
            int(input.anio()), LEVELS[input.nivel()], int(input.socio_anio()), info, nivel, input.nivel()
        )

    @render.ui
    def socio_escala():
        """De dónde viene el dato en el nivel mostrado (nativo o heredado)."""
        info = indicador_actual()
        if info is None or not input.socio_on():
            return div()
        texto = info.get("scale_native") or ""
        heredado = "hered" in texto or "ENCEVI" in texto
        return div(
            HTML(f"<b>Escala del dato:</b> {texto}"),
            style="font-size:11px;color:#8a4b00;margin-top:8px;" if heredado else "font-size:11px;color:#666;margin-top:8px;",
        )

    @render.ui
    def socio_hover():
        p = hover()
        info = indicador_actual()
        if p is None or not input.socio_on() or info is None:
            return div("Pasa el cursor sobre un polígono.", style="font-size:12px;color:#666;margin-top:10px;")
        unidad = info.get("unit", "%")
        if p.get("valor") is None:
            valor = f"sin dato ({p.get('flag')})"
            if p.get("cota_sup") is not None:
                valor += f", a lo más {p['cota_sup']:.2f} {unidad}"
        else:
            valor = f"{p['valor']:.2f} {unidad}"
        if p.get("cv") is not None:
            calidad = {"ok": "", "aviso": " · precisión media", "poco_preciso": " · POCO PRECISA"}.get(p.get("calidad") or "", "")
            valor += f" (CV {p['cv']:.0f} %{calidad})"
        if "nom_loc" in p:      # AGEB (NOM_LOC del ITER en filas AGEB es "Total AGEB urbana": no informa)
            ambito = p.get("ambito") or "urbana"
            titulo = f"<b>AGEB {ambito} {p['cvegeo'][-4:]}</b> · {p['nom_mun']}, {p['nom_ent']} ({p['cvegeo']})"
            if ambito == "rural" and p.get("n_localidades") is not None:
                titulo += (f" · {int(p['n_localidades'])} localidades"
                           + (f", {int(p['n_loc_sin_dato'])} de 1–2 viviendas sin indicadores" if p.get("n_loc_sin_dato") else ""))
            if p.get("origen_ampliado"):
                titulo += f" · ampliado por {p['origen_ampliado']}"
        elif "nom_mun" in p:
            titulo = f"<b>{p['nom_mun']}</b>, {p['nom_ent']} ({p['cvegeo']})"
        else:
            titulo = f"<b>{p['nom_ent']}</b> ({p['cvegeo']})"
        return div(
            HTML(titulo),
            div(f"Valor: {valor}", style="font-size:12px;"),
            div(f"Población: {p['pobtot']:,} · viviendas c/caract.: {p['vivparh_cv']:,}"
                if p.get("vivparh_cv") is not None else f"Población: {p['pobtot']:,}",
                style="font-size:12px;color:#444;"),
            style="margin-top:10px;font-size:12px;",
        )

    @render.ui
    def celda_medi():
        """Resumen MEDI de la celda UTCI pulsada (AGEB cuyo centroide cae en ella)."""
        c = clic() if clic is not None else None
        if c is None:
            return div("Al hacer clic en una celda: población y carencias de sus AGEB urbanas.",
                       style="font-size:12px;color:#666;")
        anio = int(input.socio_anio())
        r = stac.medi_at(c[0], c[1], anio)
        titulo = HTML(f"<b>Censo {anio} en la celda ({r['lat_c']:.2f}, {r['lon_c']:.2f})</b>")
        if r["n_ageb"] == 0 and r.get("n_localidades", 0) == 0:
            return div(titulo, div("Sin AGEB urbanas ni localidades rurales con centroide en esta celda.",
                                   style="margin-top:6px;color:#666;"))
        filas = [
            div(f"AGEB urbanas: {r['n_ageb']:,} ({r.get('pob_urbana', 0):,} hab.) · localidades rurales: "
                f"{r.get('n_localidades', 0):,} en {r.get('n_ageb_rural', 0):,} AGEB ({r.get('pob_rural', 0):,} hab.)",
                style="margin-top:6px;"),
        ]
        for ind in stac.medi_indicators(anio, "grid"):
            v, n = r.get(ind["id"]), r.get(ind["id"] + "_n", 0)
            unidad = ind.get("unit", "%")
            texto = f"{v:.2f} {unidad}" if v is not None else "sin dato"
            peso = "índice" if ind.get("is_index") else f"peso MEDI {ind['weight_medi']}"
            estilo = "font-weight:bold;" if ind.get("is_index") else ""
            filas.append(div(
                HTML(f"<span style='{estilo}'>{ind['label']}:</span> {texto} "
                     f"<span style='color:#777'>({n:,} unidades con dato, {peso})</span>")
            ))
        filas.append(div("Tasas del ITER: Σ numerador / Σ denominador de las AGEB urbanas y localidades rurales no censuradas. "
                         "Componentes heredados (ampliado, ENCEVI) e índice: media ponderada por viviendas.",
                         style="font-size:11px;color:#777;margin-top:6px;"))
        return div(titulo, *filas, style="font-size:12px;")
