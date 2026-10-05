# Supuestos, decisiones y límites del atlas — guía para el equipo de investigación

> Todo lo que hay que saber antes de usar, citar o cuestionar una capa del
> atlas. Cada punto remite a la evidencia (libreta) y a la decisión (ADR) que
> lo sustenta. Estado al 2026-09-02 (commit `f147343`). Documentos hermanos:
> [DATOS.md](DATOS.md) (metodología de datos, con cifras),
> [adr/](adr/) (decisiones con evidencia), [planes/](planes/) (hitos cerrados),
> [planes/04-medi-ampliado.md](planes/04-medi-ampliado.md) (último plan, cerrado).

---

## 0. Glosario y claves

- **UTCI** (*Universal Thermal Climate Index*): temperatura equivalente que
  integra aire, humedad, viento y radiación. El atlas usa la escala ISB de 10
  niveles: 0 frío extremo (< −40 °C), 1 frío muy fuerte (−40 a −27), 2 frío
  fuerte (−27 a −13), 3 frío moderado (−13 a 0), 4 frío ligero (0 a 9), 5 sin
  estrés (9 a 26), 6 calor moderado (26 a 32), 7 calor fuerte (32 a 38), 8
  calor muy fuerte (38 a 46), 9 calor extremo (> 46). "Horas por nivel" son
  las horas del año en que el UTCI de la celda cayó en cada nivel.
- **ITER**: Principales resultados por localidad / por AGEB y manzana urbana
  del Censo (cuestionario básico, universo). **Ampliado**: cuestionario
  ampliado del Censo (muestra). **ENCEVI**: Encuesta Nacional sobre Consumo de
  Energéticos en Viviendas Particulares 2018.
- **AGEB**: área geoestadística básica. Urbana: manzanas en localidades de
  ≥ 2 500 hab. o cabeceras; rural: territorio con localidades dispersas.
- **MEDI**: índice de carencias energéticas del hogar según el diseño del
  equipo (`descriptores_MEDI.xlsx`: 7 carencias con pesos). **Las siglas y la
  referencia publicada del diseño no están en el repositorio**: pedirlas al
  equipo para citarlas (§14).
- **Claves** (`cvegeo`): estado 2 dígitos; municipio 5; AGEB rural 9
  (`ENT+MUN+AGEB`); AGEB urbana 13 (`ENT+MUN+LOC+AGEB`); localidad 9
  (`ENT+MUN+LOC`). Siempre con ceros a la izquierda; nunca usar la columna
  concatenada del extracto.

## 1. Qué es el atlas y qué no es

- Es un **visor de estrés térmico (UTCI, ERA5-HEAT) para México** cruzado con
  **carencias energéticas del hogar (MEDI, Censo 2020)**. Sirve para ver dónde
  coinciden calor y carencia, a tres escalas, y para explorar la relación
  entre ambas por celda, municipio o estado (en el mapa y en el resumen por
  celda; el cruce cuantificado vive en las libretas y en la futura capa
  bivariada del plan de visibilidad).
- **No es** una medición de pobreza energética por hogar: por AGEB y municipio
  sólo hay tasas agregadas, no microdatos de todos los componentes (§7).
- **No es** una serie temporal: cada fuente tiene su fecha (§9). El UTCI se
  actualiza por año; el Censo es una foto de marzo de 2020.
- Todo el procesamiento es reproducible con `uv` y las libretas 001–010; los
  datos viven fuera de Git y se descargan de fuentes públicas (§10).

## 2. Fuentes y su representatividad

La pregunta más importante ante cualquier número del atlas es **de qué fuente
viene**, porque de eso depende a qué escala es válido.

| fuente | qué es | cobertura | unidad válida | año | error |
|---|---|---|---|---|---|
| **ERA5-HEAT (Copernicus)** | reanálisis global; UTCI horario en malla de 0.25° (~27 km), en kelvin en el archivo y convertido a °C al clasificar | todo México + mar; celdas con UTCI indefinido (viento fuera del rango de la fórmula, p. ej. Tehuantepec) tienen menos de 8 760 h válidas (`valid_hours`); los diarios de 2022 vienen recortados a 33 °N y los de 2023 a 33.5 °N, así que la regla climática usa la malla común | la celda; no describe microclimas urbanos ni islas de calor | 2022 y 2023 catalogados; tiempo en UTC, no hora local | modelo, sin error muestral; sesgos de reanálisis |
| **ITER básico, Censo 2020** ("Principales resultados por AGEB y manzana urbana") | conteos del cuestionario básico para el **universo** de viviendas | AGEB **urbanas** (localidades ≥ 2 500 hab. o cabeceras); filas municipio y entidad son totales completos, urbano + rural | AGEB urbana, municipio, estado | levantamiento 2–27 marzo 2020 | sin error muestral; **censura** por confidencialidad (asterisco = menos de 3 unidades) |
| **ITER nacional, Censo 2020** (una fila por localidad) | mismas 230 variables por **localidad**, urbana y rural | todas las localidades habitadas; las de 1–2 viviendas sólo con población | localidad; sumadas por clave dan la **AGEB rural** (§4) | marzo 2020 | sin error muestral; censura por localidad completa en las de 1–2 viviendas |
| **Cuestionario ampliado, Censo 2020** (microdatos `Viviendas_CA`) | **muestra probabilística** de 4 016 627 viviendas (factores suman 34.99 M) | nacional | válido para nacional, estado, **cada municipio** y **localidades de 50 000+ hab.**; no por AGEB | marzo 2020 | error muestral: coeficiente de variación publicado por unidad (§5) |
| **ENCEVI 2018** (INEGI) | encuesta de consumo de energéticos en viviendas, 28 953 viviendas con factor | nacional | diseñada para nacional y **3 regiones climáticas**; por estado (~900 viviendas) sólo con cautela | 2018 | error muestral, no calculado aquí por estado |
| **Marco Geoestadístico 2020** (INEGI) | polígonos oficiales de estados, municipios, AGEB urbanas y rurales | nacional; misma edición que el Censo 2020 | claves casan 1:1 con el ITER | dic-2020 / feb-2021 | sin error; `.prj` sin código EPSG (se asigna 6372) |
| Tabulados estatales (`uso_combustible.xlsx`, `cocina_c_chimenea.xlsx`) | resúmenes por estado del ampliado | 32 estados | estado | 2020 | idénticos a lo estimado desde microdatos (verificación cruzada) |
| Extracto `bd_MEDI_AGEB.csv` (entregado al equipo) | extracto del ITER por AGEB | 64 313 AGEB | **no se usa**: trae `VIVPAR_HAB` como denominador (incorrecto), Sonora con otra columna, una fila mal en BC, una AGEB faltante | 2020 | — |

Consecuencia práctica: **un valor por AGEB sólo es "propio" si viene del ITER
básico**. Todo lo que viene del ampliado o de la ENCEVI es una estimación de
una unidad mayor asignada a la AGEB (§4).

## 3. Definiciones exactas de los indicadores

Todos son **porcentaje de viviendas particulares habitadas**, con el
denominador oficial de INEGI para los indicadores de vivienda, `VIVPARH_CV`
(viviendas habitadas *con características captadas*). Usar `VIVPAR_HAB`, como
hacía el extracto, produce porcentajes negativos ([ADR-0001](adr/0001-fuente-oficial-inegi-y-denominador.md)).

| id | carencia MEDI | fórmula | peso | escala nativa |
|---|---|---|---|---|
| `sin_elec` | sin electricidad | `VPH_S_ELEC / VIVPARH_CV` | 0.24 | AGEB, municipio, estado |
| `sin_refri` | sin refrigerador | `(VIVPARH_CV − VPH_REFRI) / VIVPARH_CV` (INEGI publica "con") | 0.21 | AGEB, municipio, estado |
| `sin_confort` | sin confort térmico condicional al clima | ver §6 | 0.14 | mixta (§4) |
| `lena` | combustible ≠ electricidad/GLP/gas natural | leña o carbón **u otro combustible**, sobre las viviendas **que cocinan** con respuesta (excluye "no cocinan" y no especificado) | 0.13 | municipio, estado, localidad ≥ 50 k |
| `fogon_sin_chim` | fogón o estufa abierta sin chimenea | cocinan con leña/carbón y no tienen tubo o chimenea, sobre las viviendas **que cocinan** | 0.13 | municipio, estado, localidad ≥ 50 k |
| `sin_telef` | sin teléfono fijo ni celular | `VPH_SINLTC / VIVPARH_CV` | 0.08 | AGEB, municipio, estado |
| `sin_rtv` | sin radio ni televisor | `VPH_SINRTV / VIVPARH_CV` | 0.07 | AGEB, municipio, estado |
| `sin_ac` | sin aire acondicionado (insumo, peso 0) | `AIRE_ACON = no`, sobre viviendas con respuesta | — | municipio, estado, localidad ≥ 50 k |
| `medi` | índice | `Σ wᵢ · pᵢ`, 0–100 | 1.00 | ver §7 |

Supuestos dentro de las definiciones:

- **"Otro combustible"** (código 4 del Censo) cuenta como carencia. El diseño
  MEDI excluye queroseno y biogás, que el Censo no separa; "otro" es < 0.2 %
  en todos los estados, así que el efecto es despreciable.
- El denominador de combustible y chimenea son las viviendas **que cocinan**,
  no todas. Los tabulados estatales de INEGI usan todas las viviendas; por eso
  la verificación cruzada se hace con una variante (`lena_all`) y no con el
  indicador publicado.
- Refrigerador, teléfono y radio/TV se toman tal como INEGI los publica; no
  distinguen funcionamiento ni antigüedad.

## 4. Escalas: qué es propio de cada nivel y cómo se hereda

El atlas publica tres niveles y el cruce con la malla UTCI. No hay
operaciones espaciales entre unidades censales: **todo está anidado por
clave** (AGEB ⊂ localidad ⊂ municipio ⊂ estado ⊂ región ENCEVI), porque el
marco y el ITER son de la misma edición 2020 (64 313 AGEB caen en los 2 469
municipios sin excepción; 331 AGEB del ITER sólo existen en el marco como
rurales y se unen por su clave de 9).

| componente | estado | municipio | AGEB |
|---|---|---|---|
| electricidad, refrigerador, teléfono, radio/TV | propio (ITER, fila entidad) | propio (ITER, fila municipio: urbano + rural) | **propio** (ITER por AGEB en urbanas; suma de localidades del ITER nacional en rurales) |
| combustible, chimenea, AC | propio (ampliado) | propio (ampliado, con CV) | **heredado**: de la localidad ≥ 50 k si la AGEB pertenece a una (31 248 AGEB urbanas, 49 % de las urbanas y 39 % del total con rurales; 67 % de la población urbana), si no del municipio (`origen_ampliado`; todas las rurales) |
| calefacción | heredado de la ENCEVI (estado) | heredado (estado) | heredado (estado) |
| necesidad de AC / calefacción (clima) | población de sus municipios | población de sus AGEB; municipios sin AGEB urbana, celda de su centroide | **propio**: la celda UTCI de su centroide |
| MEDI | 7 componentes nativos | 6 nativos + calefacción estatal | 4 propios + 3 heredados + calefacción estatal |

Qué implica heredar:

- Un valor heredado es **el mismo número repetido** en todas las AGEB de la
  unidad. En el mapa por AGEB de combustible o de MEDI se ven escalones
  municipales; la app lo avisa ("Escala del dato: … heredado") y el tooltip
  dice de dónde vino.
- Es una **falacia ecológica** asumir que la tasa municipal describe a cada
  AGEB; sólo describe el promedio de la unidad de origen. Para comparar dos
  AGEB de la misma ciudad úsense los componentes propios, no los heredados.
- El **cruce con la celda UTCI** asigna cada AGEB urbana a la celda de 0.25°
  que contiene su centroide y cada **localidad rural a la celda de su punto**
  (tabla puente con una fila por AGEB urbana y una por localidad rural). Una
  AGEB urbana que cruza dos celdas cuenta entera en una; a ~27 km de celda y
  < 1 km de AGEB el efecto es marginal. Las AGEB rurales, que pueden abarcar
  varias celdas, promedian las celdas de sus localidades ponderando por
  población. Para municipios y estados la necesidad climática se pondera por
  población, no por área.
- El resumen por celda del pie de página suma numerador y denominador de las
  AGEB no censuradas para los componentes del ITER, y pondera por viviendas
  los heredados y el índice. Es un promedio urbano de la celda, no del
  territorio rural que la rodea.
- Problema de la unidad de área modificable (MAUP): los cuantiles y las
  correlaciones cambian con el nivel. Las correlaciones de la gráfica de
  dispersión son ecológicas (entre unidades), no individuales.
- La función de **dispersión** `plots.socio_scatter` (retirada del panel;
  disponible para análisis) toma las horas UTCI de la celda del **centroide**
  de cada municipio o estado, mientras que la necesidad climática del índice
  pondera las celdas de sus localidades por población. Para un municipio
  grande y heterogéneo las dos cifras pueden diferir.
- Las **clases de la leyenda** son cuantiles nacionales fijos por nivel e
  indicador (para AGEB, urbanas y rurales juntas): comparables entre
  ciudades, pero no son umbrales de política ni de riesgo.

## 5. Censura, precisión y huecos

- **Asteriscos del ITER** = menos de 3 unidades (0, 1 o 2). Se guardan como
  nulo con bandera (`ok | censurado | sin_viviendas`). Ningún componente se
  imputa en la capa; el índice publica un **intervalo**: `medi_min` con los
  censurados en 0 y `medi_max` con 2 viviendas ([ADR-0002](adr/0002-asteriscos-censura.md)).
  Por AGEB la censura es alta en electricidad (nulo en 34 %), teléfono (20 %)
  y radio/TV (21 %), baja en refrigerador (9 %); el intervalo del índice mide
  0.46 puntos en promedio y sólo 5 % de las AGEB cambiarían de clase entre
  sus extremos. Por municipio y estado la censura es marginal (electricidad
  nula en 103 municipios, radio/TV en 3).
- **`sin_viviendas`**: 5 247 AGEB urbanas no tienen viviendas con
  características captadas (parques industriales, zonas en construcción) y
  1 995 AGEB rurales sólo tienen localidades de 1–2 viviendas. No tienen índice.
- **AGEB rurales** (§4, ADR-0008): 14 868 con datos; sus indicadores excluyen
  las localidades de 1–2 viviendas (415 mil personas en el país), que sólo
  publican población. Se dibujan con menos opacidad y trazo punteado porque
  un polígono grande con color uniforme exagera; el tooltip dice cuántas
  localidades tiene y cuántas quedaron sin indicadores.
- **Precisión del ampliado**: cada tasa municipal/estatal/localidad lleva
  `cv_*` (coeficiente de variación por linealización de Taylor con
  conglomerado último sobre `ESTRATO`/`UPM`) y `calidad_*` con la regla INEGI:
  ≤ 15 % ok, 15–30 % aviso, > 30 % poco preciso (borde rojo punteado en el
  mapa). AC es preciso en 99 % de los municipios; combustible ok en 60 %,
  aviso 29 %, poco preciso 11 %; chimenea 52 / 30 / 18 %. **Un municipio
  pequeño con 20 % de leña y CV 40 % no debe citarse como "20 %"**. Los
  estratos con una sola UPM en la muestra aportan varianza cero, así que el
  CV está **subestimado** en los municipios más pequeños; INEGI publica sus
  propias estadísticas de precisión si hace falta contrastar.
- **Tres municipios sin datos del ampliado**: Seybaplaya (04012), Honduras de
  la Sierra (07125) y 29048 (Tlaxcala) vienen completos en "cobertura 3" del
  Censo (viviendas sin información de ocupantes). Quedan nulos con sus 19 AGEB.
- **Localidad en el tooltip**: `NOM_LOC` en las filas AGEB del ITER dice
  "Total AGEB urbana"; por eso no se muestra el nombre de la localidad.

## 6. La regla "condicional al clima"

Definida con la propia malla UTCI ([ADR-0007](adr/0007-regla-climatica-utci.md), libreta 009):

- `h_calor` = horas/año en niveles ≥ 7 (calor fuerte o más, UTCI > 32 °C);
  `h_frio` = horas/año en niveles ≤ 3 (frío moderado o más, UTCI < 0 °C);
  promedio de los años catalogados (2022–2023).
- **Necesita AC** si `h_calor ≥ 902`; **necesita calefacción** si `h_frio ≥ 626`
  (valores con las AGEB rurales incluidas; con sólo urbanas eran 912 y 625:
  la regla es estable).
  Umbrales calibrados para reproducir la evidencia externa a nivel estatal:
  regiones ENCEVI para AC (95.4 % de coincidencia ponderada por población;
  excepciones: Morelos, Nayarit y Colima, "templados" en ENCEVI pero
  calurosos) y estados con ≥ 8 % de viviendas con calefactor para frío
  (87.8 %). Se probó también < 9 °C: discrimina peor, porque el altiplano
  acumula horas frescas sin usar calefacción.
- Resultado: 47.8 % de las AGEB necesitan AC, 10.7 % calefacción, 3.8 % ambas,
  45.3 % ninguna (tienen confort térmico = 0 por definición).
- `p_sin_confort` = `p_sin_ac` donde sólo se necesita AC; `p_sin_calef` donde
  sólo calefacción; media de ambas donde las dos; 0 donde ninguna.
- **Limitación conocida**: Nuevo León, Coahuila y Tamaulipas usan calefactor
  (18–29 % de viviendas) por frentes fríos cortos que no suman 626 h bajo
  cero; con esta regla no "necesitan" calefacción. Es una decisión abierta
  con el equipo: una regla por rachas o grados-hora la cambiaría (parámetros
  en la libreta 009).
- La necesidad climática se mide con UTCI a 2 m de un reanálisis: no capta
  isla de calor urbana ni condiciones interiores.
- Las horas se cuentan sobre las horas **válidas** de la celda; en celdas con
  UTCI indefinido parte del año (sobre todo marinas), `h_calor` y `h_frio`
  quedan subestimadas. En tierra el efecto es marginal.

## 7. El índice MEDI

- **Fórmula**: `medi = Σ wᵢ · pᵢ`, con `pᵢ` en 0–100 y pesos del diseño
  (0.24, 0.21, 0.14, 0.13, 0.13, 0.08, 0.07; suman 1.00). Sin renormalizar
  cuando un componente falta: si falta, el índice es nulo ([ADR-0006](adr/0006-definicion-medi.md),
  en estado *propuesto* hasta que el equipo lo confirme).
- **Interpretación**: es la **intensidad promedio de carencia** de la unidad,
  no el porcentaje de hogares pobres energéticos. Un MEDI de 30 en Guerrero
  no significa "30 % de hogares en pobreza energética"; significa que, en
  promedio ponderado por los pesos, el 30 % de las viviendas carece de cada
  componente. Un índice tipo Alkire-Foster (hogar carente si supera un corte
  k) necesita microdatos de los siete componentes por hogar, que no existen
  para el ITER básico; sólo podría aproximarse por municipio con los
  microdatos del ampliado y quedó anotado como trabajo futuro.
- **Resultados de cara** (2020): estados de 1.7 (CDMX) a 36.4 (Chiapas),
  seguido de Oaxaca 34.4 y Guerrero 30.1; municipios de 0.4 a 66.6; AGEB
  hasta 95 (con rurales; 71 917 de 79 181 con índice). El aire acondicionado
  del Censo y el de la ENCEVI por estado correlacionan 0.97.
- **Pesos**: son los del archivo `descriptores_MEDI.xlsx` que entregó el
  equipo (0.24, 0.21, 0.14, 0.13, 0.13, 0.08, 0.07). El atlas no tiene la
  referencia metodológica que los justifica; hay que citarla desde el equipo.
- **Sensibilidad a los pesos**: no evaluada; cambiar un peso es editar `W` en
  la libreta 010 y reejecutar 010 y 007 (ítem B13 del temario).

## 8. Geometría y proyecciones

- Los productos se guardan y sirven en **EPSG:4326** (lat/lon). Lo que
  requiere metros (centroides, simplificación) se calcula antes en
  **EPSG:6372** (Lambert cónica conforme México ITRF2008), que es la
  proyección del marco aunque su `.prj` no traiga el código ([ADR-0003](adr/0003-crs-4326-almacenar-6372-medir.md)).
- **No calcular áreas ni densidades sobre los GeoParquet finales**: 4326 no es
  métrico y 6372 es conforme, no equivalente. Si hacen falta áreas, usar una
  proyección equivalente (Albers) en el pipeline.
- La app **simplifica** la geometría para dibujar (500 m para estados y
  municipios; medio píxel del zoom para AGEB) y **no** la usa para medir. Los
  polígonos del parquet están a resolución oficial completa.
- Las AGEB se dibujan por ventana a partir de zoom 10 ([ADR-0005](adr/0005-ageb-por-ventana-vector.md));
  a escala nacional se ve el municipal aunque el selector diga AGEB.

## 9. Temporalidad

| dato | fecha de referencia |
|---|---|
| UTCI, horas por nivel | años calendario 2022 y 2023, hora UTC (no hora local) |
| Regla climática | promedio 2022–2023; se recalcula al catalogar más años |
| ITER y ampliado | Censo 2020: levantamiento 2–27 de marzo de 2020, referencia 15 de marzo |
| Calefacción y AC de contraste | ENCEVI 2018 |
| Marco Geoestadístico | edición Censo 2020 |

Las capas socioeconómicas son una foto; cruzarlas con distintos años de UTCI
no describe cambios en las carencias, sólo en el clima.

## 10. Reproducibilidad y cómo cambiar un supuesto

- Orden del pipeline INEGI: **004 → 005 → 006 → 008 → 009 → 010 → 007**
  (001–003 para el UTCI). 010 escribe columnas dentro de los productos de 005
  y 006: si se reejecutan éstas, hay que volver a correr 008 → 010 → 007.
- Descargas: marco 257 MB, ITER por AGEB 247 MB, ITER nacional 37 MB,
  ampliado 489 MB; todo con `SOURCE.md` (URL, fecha, hash). `data/` está fuera
  de Git. El producto AGEB (urbanas + rurales) pesa 203 MB; la app lo lee por
  ventana, nunca entero.
- Dónde se cambia cada supuesto: denominadores y recodificaciones, 005 y 008;
  reglas de censura, 005 y 010; umbrales climáticos y niveles UTCI, 009;
  pesos y fórmula del índice, 010; qué indicadores expone la app, 007
  (`INDICATORS`); umbral de zoom y clases, `src/atlas/choropleth.py`.
- Todas las decisiones no triviales tienen ADR en `docs/adr/` con evidencia y
  la señal que obligaría a revisarlas.
- "Verificado" en este repositorio significa que la libreta tiene una
  comprobación automática (`assert`) contra una cifra oficial o contra otra
  fuente: población nacional, tabulados estatales, boletín del Censo,
  regiones ENCEVI. Las tolerancias están escritas en cada libreta (p. ej.
  0.5 puntos entre microdatos y tabulado estatal de leña).

## 11. Cómo citar

- **UTCI / ERA5-HEAT:** Di Napoli, C., Barnard, C., Prudhomme, C., Cloke, H. L.
  y Pappenberger, F. (2021). *ERA5-HEAT: A global gridded historical dataset
  of human thermal comfort indices from climate reanalysis*. Geoscience Data
  Journal, 8(1), 2–10. Datos: Copernicus Climate Change Service (C3S), Climate
  Data Store. Escala UTCI: Bröde, P. et al. (2012). *Deriving the operational
  procedure for the Universal Thermal Climate Index (UTCI)*. Int. J.
  Biometeorol., 56, 481–494.
- **Censo 2020:** INEGI. *Censo de Población y Vivienda 2020*. Principales
  resultados por AGEB y manzana urbana; Principales resultados por localidad
  (ITER); Cuestionario ampliado, microdatos; Marco Geoestadístico 2020.
- **ENCEVI 2018:** INEGI. *Encuesta Nacional sobre Consumo de Energéticos en
  Viviendas Particulares 2018*.
- **Este atlas:** citar el repositorio con el commit (p. ej. `f147343`) y el
  ADR que sustente la cifra usada; las cifras derivadas (MEDI, regla
  climática) son procesamiento propio, no de INEGI ni de Copernicus.

## 12. Preguntas frecuentes

- **¿Por qué el MEDI por AGEB tiene bloques del tamaño de un municipio?**
  Porque tres componentes son heredados (§4). Mira los componentes propios
  para la variación intraurbana.
- **¿Puedo comparar una AGEB de Mérida con una de Monterrey?** Sí para los
  componentes del ITER (clases por cuantiles nacionales, iguales en toda la
  app); con cautela para los heredados y el índice.
- **¿Por qué hay tantas AGEB grises en electricidad?** Censura de INEGI:
  cuando hay 0, 1 o 2 viviendas sin electricidad, INEGI publica asterisco. La
  cota superior (`p_sin_elec_sup`) casi siempre es < 1 %.
- **¿Por qué Nuevo León sale sin necesidad de calefacción?** §6. Es un límite
  de la regla por horas acumuladas bajo cero.
- **¿El MEDI es un porcentaje de hogares?** No; es intensidad promedio (§7).
- **¿Por qué el porcentaje de leña de mi municipio tiene un borde rojo?**
  Coeficiente de variación mayor a 30 %: la muestra del ampliado es pequeña
  ahí. Repórtalo con su CV o usa el estado.
- **¿Por qué la cifra estatal de leña no coincide exactamente con el tabulado
  de INEGI?** Diferencias de hasta 0.4 puntos por el tratamiento de los no
  especificados y porque el indicador del atlas usa como denominador las
  viviendas que cocinan.
- **¿Por qué el extracto que nos entregaron da otros números?** Porque usaba
  el denominador incorrecto y tenía errores en Sonora y Baja California (§2).
  El atlas se construye desde los archivos oficiales.
- **¿Se pueden sumar poblaciones de AGEB para obtener la municipal?** Casi:
  urbanas + rurales cubren todo menos los 2 601 polígonos rurales sin
  localidad habitada. Usa la fila municipal, que ya es urbano + rural.
- **¿Qué celda UTCI le toca a una AGEB que cruza dos?** La del centroide.
- **¿Puedo usar estos datos en una publicación?** Sí: INEGI (Términos de Libre
  Uso) y Copernicus (licencia ERA5) lo permiten con cita. Cita las fuentes
  primarias y el atlas como procesamiento; los ADR documentan cada decisión.

## 13. Qué no hacer con estas capas

- No interpretar un valor heredado como medición de la AGEB.
- No citar tasas del ampliado sin su CV, ni las "poco precisas" como puntuales.
- No calcular áreas sobre los productos en 4326.
- No comparar el MEDI de 2020 con un UTCI futuro como si midiera cambio social.
- No tratar el MEDI como conteo de hogares pobres ni sumar pesos parciales.
- No usar la necesidad climática como medida de confort interior.
- No leer las clases de cuantiles como umbrales de riesgo o de política.

## 14. Decisiones pendientes del equipo

1. Confirmar que el MEDI es suma ponderada de tasas (ADR-0006) o pedir la
   versión Alkire-Foster municipal con microdatos del ampliado.
2. Regla de frío: horas acumuladas bajo 0 °C (actual) o rachas/grados-hora.
3. Si los componentes heredados deben pintarse por AGEB o sólo por municipio.
4. Umbral de zoom para AGEB (10) y si el municipal debe seguir siendo la
   vista nacional por defecto.
5. ~~Las 331 AGEB mixtas~~ — decidido: conservan su fila urbana sin sumar
   localidades rurales (plan 05).
6. Confirmar las siglas del MEDI y la referencia metodológica de sus pesos
   para poder citarlos.
