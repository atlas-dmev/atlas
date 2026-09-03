# Plan 04 — completar el MEDI con el Cuestionario ampliado del Censo 2020 y calcularlo como capa (antes PLAN-MEDI-ITER.md)

Objetivo: incorporar al atlas los **tres componentes del MEDI que faltan**
(0.40 del peso) usando lo que el Censo 2020 sí mide, aunque no en el ITER
básico sino en el **Cuestionario ampliado** (muestra probabilística, válida por
municipio), y con eso calcular el **índice MEDI** como una capa más, en tres
niveles: estado, municipio y AGEB urbana.

Estado de partida (plan anterior, [03-capas-inegi-medi.md](03-capas-inegi-medi.md)):
los cuatro componentes que el ITER básico mide por AGEB ya están en el atlas
(electricidad 0.24, refrigerador 0.21, teléfono 0.08, radio/TV 0.07 = 0.60).

| componente que falta | peso | dónde está en el Censo 2020 | nivel alcanzable |
|---|---|---|---|
| Combustible de cocina ≠ electricidad / GLP / gas natural / queroseno / biogás | 0.13 | Ampliado, pregunta 8 (`COMBUSTIBLE`: leña o carbón, gas, electricidad, otro, no cocinan) | municipio (+ localidades ≥ 50 k, estado) |
| Fogón o estufa abierta sin chimenea | 0.13 | Ampliado, pregunta 9 (`ESTUFA`: con / sin tubo o chimenea; sólo quienes cocinan con leña o carbón) | municipio |
| Sin aire acondicionado ni calefacción, **condicional al clima** | 0.14 | AC: Ampliado, pregunta 15 (`AIRE_ACON`: sí / no). Calefacción: **no está en el Censo**; sólo en ENCEVI 2018 (`uso_calef`, `calefactor.csv`) por región climática / estado | AC municipio; calefacción región o estado |

## Insumos

| insumo | qué es | de dónde |
|---|---|---|
| Microdatos del Cuestionario ampliado 2020, tabla `Viviendas_CA` (32 zips, uno por estado; Ags = 3.2 MB) | ~4 M viviendas con `ENT`, `MUN`, `LOC50K`, `ESTRATO`, `UPM`, `FACTOR` y 83 variables, entre ellas `COMBUSTIBLE`, `ESTUFA`, `ELECTRICIDAD`, `FOCOS`, `FOCOS_AHORRA`, `AIRE_ACON`, `CALENTADOR_SOLAR`, `PANEL_SOLAR` | `https://www.inegi.org.mx/contenidos/programas/ccpv/2020/microdatos/Censo2020_CA_<abr>_csv.zip` con abreviaturas INEGI verificadas por `HEAD` (`ags`, `bc`, `bcs`, `cam`, `coa`, `col`, `chs`, `chh`, `cdmx`, `dgo`, `gto`, `gro`, `hgo`, `jal`, `mex`, `mich`, `mor`, `nay`, `nl`, `oax`, `pue`, `qro`, `qroo`, `slp`, `sin`, `son`, `tab`, `tam`, `tla`, `ver`, `yuc`, `zac`) → `data/raw/INEGI/censo_ampliado_2020/` |
| Descriptor de la tabla `Viviendas_CA` | Códigos de cada variable (p. ej. `AIRE_ACON` 5 = sí, 6 = no, 9 = no especificado) | Red Nacional de Metadatos, catálogo 632, datafile F14 |
| Tabulados estatales ya en repo | `uso_combustible.xlsx` y `cocina_c_chimenea.xlsx` (32 estados) | `data/raw/INEGI/tabulados/` — **verificación cruzada**: son la misma fuente, deben coincidir con lo que se estime desde microdatos |
| ENCEVI 2018 | `encevi.csv` (`uso_aire`, `uso_calef`) + `vivienda.csv` (`factor_sem`, `region`, `entidad`) | `data/raw/INEGI/encevi_2018/` |
| Marco Geoestadístico 2020, capa `00ent` | 32 polígonos estatales, ya extraídos | `data/raw/INEGI/mg_2020/conjunto_de_datos/` |
| Boletín de resultados complementarios del Censo 2020 | Cifras de control: 12.5 % de viviendas con leña o carbón a nivel nacional; Chiapas 49.3 %, Oaxaca 46.1 %, Guerrero 40.8 %; 0.8 % con panel solar; 48 % con calentador de agua | INEGI, 2021 |

## Lo que hay que decidir antes de calcular (ADR-0006)

1. **Fórmula del índice.** Con tabulados o agregados sólo es posible la suma
   ponderada de tasas, `MEDI = Σ wᵢ · pᵢ`, con `pᵢ` en [0, 1] y `Σ wᵢ = 1`. Si
   el diseño original es de conteo por hogar (tipo Alkire-Foster, con corte
   *k*), sólo el nivel estatal/municipal desde microdatos del ampliado podría
   aproximarlo, y sólo con los tres componentes del ampliado (el ITER básico no
   tiene microdatos). Propuesta: suma ponderada en los tres niveles; anotar la
   alternativa AF como trabajo futuro con microdatos.
2. **Componentes censurados (AGEB).** Publicar intervalo: `medi_min` con los
   censurados en 0 y `medi_max` con los censurados en 2 viviendas, más
   `medi` = punto medio y `n_censurados`. Sin renormalizar pesos.
3. **Regla "condicional al clima".** Dos opciones:
   (a) regiones ENCEVI: AC exigible en la región 1 (cálida extrema) y 3
   (tropical), calefacción en la región 1 (norte) en invierno;
   (b) **desde la malla UTCI del propio atlas**: una unidad necesita
   enfriamiento si su celda supera *H_calor* horas/año en niveles ≥ "calor
   fuerte", y calefacción si supera *H_frío* horas/año en niveles ≤ "frío
   moderado". Propuesta: (b), con umbrales fijados por cuantiles de la malla y
   documentados; (a) como verificación de cara.
4. **Precisión muestral.** Cada tasa municipal del ampliado lleva su
   coeficiente de variación (diseño estratificado por conglomerados:
   `ESTRATO`, `UPM`, `FACTOR`). Regla de publicación propuesta, como INEGI:
   CV ≤ 15 % se muestra; 15–30 % se muestra con aviso; > 30 % se marca como
   "estimación poco precisa" y se pinta con trama/gris.
5. **Calefacción.** Se hereda de la región o estado ENCEVI (2018) al municipio
   y a la AGEB; se documenta como el único componente no censal y no municipal.

## Flujo de datos

```
data/raw/INEGI/censo_ampliado_2020/Censo2020_CA_<abr>_csv.zip   (32)   ← 008 los baja
   │  008_AMPLIADO_mun.ipynb   (lee Viviendas_CA, recodifica, agrega con FACTOR por
   │                            municipio / estado / LOC50K, CV por diseño, verifica
   │                            contra tabulados estatales y boletín)
   ▼
data/derived/INEGI/2020/ampliado_mun_2020.parquet      ← tasas + CV + n por municipio
data/derived/INEGI/2020/ampliado_ent_2020.parquet      ← lo mismo por estado
data/derived/INEGI/2020/ampliado_loc50k_2020.parquet   ← lo mismo por localidad ≥ 50 k
   │  009_CLIMA_confort.ipynb  (regla climática desde el STAC utci: horas de calor/frío
   │                            por celda → necesidad de AC / calefacción por AGEB,
   │                            municipio y estado; calefacción desde ENCEVI)
   ▼
data/derived/INEGI/2020/clima_{ageb,mun,ent}_2020.parquet ← h_calor, h_frio, necesita_ac, necesita_calef
data/derived/INEGI/2020/encevi_ent_2018.parquet, clima_umbrales_2020.parquet
   │  010_MEDI_index.ipynb     (une todo por cve_ent / cvegeo; MEDI, min, max en 3 niveles)
   ▼
data/derived/INEGI/2020/medi_ent_2020.parquet          ← nuevo: 7 componentes + MEDI, geometría 00ent
data/derived/INEGI/2020/medi_mun_2020.parquet          ← + 3 componentes del ampliado + confort + MEDI
data/derived/INEGI/2020/medi_ageb_2020.parquet         ← + 3 componentes heredados del municipio + MEDI
   │  007_STAC_inegi.ipynb     (item nuevo medi-ent-2020; indicadores nuevos en los tres)
   ▼
data/stac/inegi/
```

## Productos: columnas nuevas

Municipal (`medi_mun_2020.parquet`), desde el ampliado con factor de expansión:

| columna | definición |
|---|---|
| `p_lena` | % viviendas cuyo combustible principal es leña o carbón **u otro combustible** (códigos 1 y 4 de `COMBUSTIBLE`; "no cocinan" excluido del denominador) |
| `p_fogon_sin_chim` | % de **todas** las viviendas que cocinan con leña/carbón sin chimenea (`ESTUFA` = sin tubo, sobre el total de viviendas) |
| `p_sin_ac` | % viviendas sin aire acondicionado (`AIRE_ACON` = 6) |
| `cv_lena`, `cv_fogon`, `cv_sin_ac`, `n_muestra` | precisión muestral por municipio |
| `necesita_ac`, `necesita_calef` | bandera climática (T3) |
| `p_sin_calef` | % sin calefacción (ENCEVI, heredado de región/estado) |
| `p_sin_confort` | carencia de confort térmico = sin AC donde se necesita AC, sin calefacción donde se necesita calefacción, combinación documentada donde ambas |
| `medi`, `medi_min`, `medi_max`, `n_censurados` | índice y cotas |

Estatal (`medi_ent_2020.parquet`): los siete componentes nativos (los cuatro
del ITER desde las filas de entidad de los 32 archivos oficiales; los tres del
ampliado desde microdatos) + MEDI, con geometría `00ent`.

AGEB (`medi_ageb_2020.parquet`): los tres componentes del ampliado se
**heredan de la localidad ≥ 50 k o del municipio** (columna `origen_ampliado`),
la calefacción del estado (ENCEVI), y se calcula MEDI con sus cotas. `necesita_ac`/`necesita_calef` sí son
propias de la AGEB (vienen de su celda UTCI).

## STAC y app

- Item nuevo `medi-ent-2020` (extensión table, `atlas:indicators` con los
  siete + MEDI). Los items `medi-mun-2020` y `medi-ageb-2020` amplían sus
  indicadores; cada indicador declara `scale_native` (`ageb` | `mun` | `ent` |
  `region`) para que la leyenda diga de dónde viene el dato en ese nivel.
- `atlas:indicators` gana campos `cv_column` (si aplica) y `is_index`.
- App: opción **Estado** en el selector de nivel (misma mecánica que el
  municipal, 32 polígonos); la lista de indicadores se actualiza según el
  nivel; tooltip con CV y aviso de precisión; leyenda con nota "componente
  estatal/municipal heredado" cuando `scale_native` ≠ nivel mostrado. El
  resumen por celda del pie de página suma también el MEDI (ponderado por
  viviendas con características).

## Hitos

- [x] **T0 — ADR-0006: definición del MEDI.** Escrito en estado *propuesto*
  con las reglas del plan (suma ponderada, intervalo por censura, regla
  climática UTCI, CV según INEGI, calefacción ENCEVI); la implementación las
  usa y quedan parametrizadas. Pendiente de confirmación del equipo.
- [x] **T1 — Descarga del ampliado (008).** 32 zips (489 MB) con `SOURCE.md`.
  Abreviaturas reales de INEGI: `cam`, `coa`, `chs`, `chh`, `tam`, `tla` en
  vez de las intuitivas. 4 016 627 viviendas; factores que suman 34.99 M.
- [x] **T2 — Tasas con precisión (008).** `ampliado_{ent,mun,loc50k}_2020.parquet`
  (32 / 2 469 / 232 filas) con `p_*`, `cv_*`, `calidad_*`, `n_*`. Verificado:
  leña 12.49 % (boletín 12.5), panel solar 0.81 % (0.8), estados vs tabulados
  (máx 0.4 pts, chimenea exacto). Tres municipios sin dato (cobertura 3 del
  Censo: 04012, 07125, 29048). Precisión: AC ok en 99 % de municipios;
  combustible 60/29/11 %; chimenea 52/30/18 % (ok/aviso/poco preciso).
- [x] **T3 — Regla climática (009, ADR-0007).** H_CALOR = 912 h/año > 32 °C
  (95.4 % de coincidencia estatal con regiones ENCEVI), H_FRIO = 625 h/año
  < 0 °C (87.8 % con estados ≥ 8 % de calefactor). AGEB: 46 % necesitan AC,
  10 % calefacción, 3 % ambas. Productos `clima_{ageb,mun,ent}_2020.parquet`,
  `encevi_ent_2018.parquet`, `clima_umbrales_2020.parquet`.
- [x] **T4 — Nivel Estado en STAC y app.** `medi_ent_2020.parquet` (7
  componentes nativos); item `medi-ent-2020`; `read_medi("ent", …)`; opción
  Estado; indicadores por nivel (`update_selectize`); tooltip con CV y
  calidad; nota "Escala del dato" cuando el valor es heredado; polígonos con
  CV > 30 % con borde rojo punteado. Verificado en Chromium.
- [x] **T5 — Índice MEDI (010).** Estado: 32/32, de 1.7 (CDMX) a 36.4
  (Chiapas; luego Oaxaca 34.4, Guerrero 30.1). Municipio: 2 466/2 469, hasta
  66.3. AGEB: 59 047/64 313 (5 247 sin viviendas + 19 de cobertura 3), hasta
  90; intervalo medio 0.46 pts; 5.2 % cambiarían de clase entre min y max.
  AC Censo vs ENCEVI por estado: ρ = 0.97. Indicadores nuevos declarados en
  los cuatro items STAC con `scale_native`, `cv_column`, `unit`, `is_index`.
- [x] **T6 — Cruce con el UTCI.** El resumen por celda incluye los siete
  componentes y el MEDI (media ponderada por viviendas para heredados e
  índice). Nueva gráfica en el panel derecho: dispersión horas/año en el nivel
  UTCI elegido (celda del centroide) vs indicador actual, por municipio o
  estado, tamaño ∝ población, con ρ de Spearman.
- [x] **T7 — Documentación.** `docs/DATOS-INEGI.md` (secciones 8–10),
  ADR-0006 y ADR-0007, README, temario (A13, B13). Archivado en
  `docs/planes/04-medi-ampliado.md`; el ADR-0006 sigue *propuesto* hasta que
  el equipo lo confirme.

## Riesgos

- **Precisión municipal.** En municipios pequeños el ampliado tiene pocas
  viviendas en muestra; los CV altos no se ocultan, se muestran. Si resulta
  inservible en muchos municipios, la alternativa es publicar el ampliado a
  nivel de `LOC50K` + estado y heredar al municipio con aviso.
- **"Otro combustible".** El MEDI excluye queroseno y biogás, que el Censo
  agrupa en "otro". Se asume "otro" = carencia (es < 0.2 % en todos los
  estados según `uso_combustible.xlsx`); documentar.
- **Calefacción 2018 vs Censo 2020.** Distintos años y distinto diseño; el
  componente de confort térmico mezcla fuentes. Queda explícito en la leyenda.
- **Tamaño.** Los 32 zips del ampliado pueden sumar varios cientos de MB; se
  conservan como procedencia, fuera de Git como todo `data/`.

## Decisiones tomadas (confirmar con el equipo)

1. Regla climática: (b) horas UTCI, calibrada contra (a). Implementada.
2. Umbral de publicación por CV: regla INEGI (15 / 30 %). Implementada.
3. Nivel Estado: entra a la app. Implementado.
4. Año UTCI para la regla: promedio de los años catalogados (2022–2023).
   Implementado; se recalcula al agregar años.
5. **Pendiente del equipo:** que el MEDI sea suma ponderada de tasas y no
   conteo por hogar (ADR-0006), y la regla de frío (el noreste queda fuera con
   625 h < 0 °C; ver ADR-0007).
