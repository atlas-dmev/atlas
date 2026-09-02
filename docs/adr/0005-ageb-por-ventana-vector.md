# ADR-0005 — Capa AGEB como vector por ventana a partir de zoom 11
Estado: aceptado (2026-09-02)
Contexto:        64 313 AGEB detalladas (~2 KB por polígono) no caben como GeoJSON nacional (> 100 MB) ni tienen sentido a escala nacional. Se necesita mostrarlas al acercar el mapa.
Opciones:        (a) GeoJSON nacional; (b) rasterizar la ventana a PNG (como el UTCI); (c) vector por ventana (bbox del mapa) con simplificación por zoom y umbral de zoom; (d) mostrar sólo las AGEB del municipio pulsado; (e) vector tiles (PMTiles) con plugin JS.
Criterios:       hover con valores; nitidez al acercar; navegación continua entre ciudades; sin JS a medida ni servidor de tiles; respuesta < 1 s en la ventana más densa (CDMX).
Evidencia:       Medición S6 (viewport 1500×900): CDMX zoom 10 = 6 609 AGEB / 4.3 MB / 0.5 s; zoom 11 = 4 289 / 2.9 MB / 0.3 s; zoom 12 = 2 262 / 1.6 MB / 0.1 s; Mérida zoom 11 = 991 / 1.3 MB. ipyleaflet emite `bounds`/`zoom` al terminar cada movimiento (sin *debounce*). Prueba en Chromium headless: recarga por arrastre < 2.6 s, hover correcto. Referencias: Leaflet (`moveend`, panes y `zIndex`); Douglas–Peucker (`simplify` de GEOS) con tolerancia ligada al tamaño de píxel Web Mercator.
Decisión:        (c) con `AGEB_ZOOM_MIN = 11`, tope de 8 000 AGEB por ventana y clases por cuantiles nacionales (clase "0 %" aparte cuando > 1/6 de los valores son cero). (d) queda anotada como alternativa simple si el vector por ventana resultara pesado en equipos modestos.
Consecuencias:   +hover y nitidez; +sin infraestructura; −cada movimiento envía 1–4 MB al navegador; −el municipal sigue siendo la vista nacional (deliberado).
Revisión:        si el tiempo de recarga en CDMX supera ~1 s en uso real, bajar a PNG por ventana (b) o pasar a PMTiles (e).
