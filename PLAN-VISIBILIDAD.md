# PLAN-VISIBILIDAD — que el estrés térmico (UTCI) se vea junto a la capa socioeconómica

Objetivo: hoy la coropleta socioeconómica (panel derecho) se dibuja encima del
raster UTCI (panel izquierdo) con opacidad 0.65 y, a escala nacional, lo tapa
casi por completo. Este plan reúne las opciones para que ambas capas se lean,
de la más simple a la más ambiciosa, con su costo y lo que cambia en el código.

Estado de partida: `components/servers.py` monta el raster UTCI en un pane con
`zIndex` 350 y la coropleta en el pane vectorial de Leaflet (400) sobre el
mismo `base_map`; la opacidad del UTCI está fija en 0.75; la socioeconómica
tiene checkbox y slider; el mapa base por defecto es NatGeoWorldMap.

## Opciones

### V1 — Punto de partida y control de opacidad del UTCI (rápida)
- Capa socioeconómica **apagada al arrancar** (o encendida con opacidad 0.3).
- Slider de **opacidad del UTCI** en el panel izquierdo (hoy fija en 0.75).
- Mapa base por defecto más neutro (Positron) para que relieve y colores del
  fondo no compitan con la rampa del nivel.
- Cambios: `components/panels.py` (checkbox `value=False`, slider nuevo,
  basemap por defecto), `components/servers.py` (`ImageOverlay(opacity=…)`
  reactivo). Sin cambios en datos.
- Costo: ~1 h. Riesgo: ninguno.

### V2 — Selector "¿qué va al frente?" y mezcla de colores
- Control con tres estados: **UTCI al frente**, **socioeconómico al frente**,
  **mezcla**. Los panes ya existen: se intercambian sus `zIndex`
  (`Map.panes`) sin reconstruir el mapa.
- En "mezcla", aplicar al pane socioeconómico `mix-blend-mode: multiply`
  (CSS sobre `.leaflet-socio-pane`), que combina los colores en vez de
  cubrirlos: el raster se lee a través de la coropleta.
- Cambios: `components/panels.py` (radio), `components/servers.py` (efecto que
  actualiza `m.panes`), CSS en `page_two_sidebars`.
- Costo: ~2 h. Riesgo: `multiply` oscurece; probar con la rampa viridis y, si
  hace falta, usar una rampa clara para lo social en ese modo.

### V3 — Comparación con barra deslizante (`SplitMapControl`)
- ipyleaflet trae `SplitMapControl(left_layer=…, right_layer=…)`: una barra
  vertical arrastrable que muestra el UTCI a un lado y la coropleta al otro
  sobre el mismo mapa. Patrón estándar para comparar dos capas; sin JS propio.
- Cambios: modo "comparar" en el panel que registra ambas capas en el control
  en lugar de añadirlas sueltas; al salir del modo, se vuelve a la
  superposición. Hay que verificar que el control acepte capas en panes
  distintos y que la recarga por ventana de AGEB siga funcionando dentro del
  control.
- Costo: ~3 h. Riesgo: interacción con el reemplazo reactivo de capas (el
  control guarda referencias a capas concretas).

### V4 — Separar los canales visuales
Que las dos capas no compitan por el relleno. Dos variantes:
- **V4a — socioeconómico como contornos.** Relleno transparente; el grosor o
  la trama del borde codifica la clase (p. ej. 6 grosores o `dashArray`). Deja
  el relleno al UTCI. Funciona mejor a nivel estado/municipio que a AGEB.
- **V4b — UTCI como isolíneas.** Convertir el campo de horas/año del nivel en
  curvas (p. ej. 500, 1 000, 2 000, 3 000 h) con `matplotlib.contour` →
  GeoJSON, dibujadas encima de la coropleta con etiquetas. Muy legible a
  escala nacional; libera el relleno para lo social. Nuevo módulo
  `atlas/isolines.py` análogo a `render.py`.
- Costo: V4a ~2 h; V4b ~4 h (suavizado de la malla de 0.25° antes de
  contornear, etiquetas, leyenda propia).
- Riesgo: a nivel AGEB, las isolíneas de 0.25° son escalones gruesos; sirven
  como contexto, no como detalle.

### V5 — Capa bivariada (cruce en una sola capa)
- A nivel municipio (y estado), cruzar la **clase de horas UTCI** del
  municipio (celda del centroide, como en la gráfica de dispersión) con la
  **clase del indicador socioeconómico** en una leyenda 3 × 3 (tercios ×
  tercios) con paleta bivariada estándar (p. ej. Stevens). Pinta directamente
  "mucho calor y mucha carencia".
- Es un **producto analítico nuevo**, no un ajuste visual: se puede exportar
  y discutir. Requiere: función en `choropleth.py` que calcule las dos clases
  y asigne color; leyenda cuadriculada en el panel; selector "bivariado" como
  tercera capa; decisión de cortes (tercios nacionales fijos).
- Costo: ~1 día. Riesgo: paleta y leyenda exigen cuidado (accesibilidad,
  daltonismo); a nivel AGEB la clase de horas es la de la celda, gruesa.

### V6 — Legibilidad del propio UTCI
- Rampa del nivel con más contraste en la cola alta (`render._hours_cmap`).
- Borde de celda (rejilla fina) para que el raster se perciba como dato y no
  como sombreado del fondo.
- Costo: ~1 h.

## Recomendación

1. **Ahora: V1 + V2.** Rápidas, sin datos nuevos, resuelven la queja inmediata
   y dan al usuario el control del orden y la mezcla.
2. **Siguiente entregable: V5.** Convierte la comparación visual en una capa
   que se puede leer y citar; es el cruce que persigue el atlas.
3. **Opcionales según uso:** V3 para demostraciones; V4b si la bivariada
   resulta pesada o poco clara; V6 en cualquier momento.

## Hitos

- [ ] **V1** — socio apagado/0.3 al inicio, slider de opacidad UTCI, Positron
  por defecto. Verificación en Chromium: al cargar se ve el UTCI; el slider
  cambia `opacity` del `ImageOverlay` sin reconstruir el mapa.
- [ ] **V2** — radio de orden (UTCI / socio / mezcla) con intercambio de
  `zIndex` y `mix-blend-mode`. Verificación: capturas de los tres modos sobre
  la misma vista; el hover sigue funcionando en los tres.
- [ ] **V5** — capa bivariada municipal y estatal con leyenda 3 × 3.
  Verificación: la clase bivariada coincide con las clases univariadas de la
  leyenda de cada capa; captura nacional; el clic en un municipio muestra las
  dos clases en el tooltip.
- [ ] **V3 / V4b / V6** — según demanda.

## Decisiones a confirmar

1. ¿La capa socioeconómica arranca apagada o encendida con baja opacidad?
   Propuesta: encendida a 0.3, para que el panel derecho no parezca inerte.
2. ¿Cortes de la bivariada fijos (tercios nacionales) o por nivel? Propuesta:
   fijos por nivel (municipio y estado por separado), documentados en el STAC.
3. ¿Mapa base por defecto Positron o mantener NatGeo? Propuesta: Positron.
