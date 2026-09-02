# Datos INEGI en el atlas — qué son, cómo se procesan y qué limitaciones tienen

> Metodología **de datos** de las capas socioeconómicas (Censo 2020, diseño
> MEDI). El plan e hitos están en [../PLAN-SOCIOECONOMICOS.md](../PLAN-SOCIOECONOMICOS.md);
> las decisiones con evidencia, en [adr/](adr/). Este documento es la
> referencia que un usuario del atlas necesita para interpretar lo que ve.

## 1. Qué se muestra

Dos indicadores del diseño MEDI (índice de carencia energética del hogar),
como **porcentaje de viviendas**:

| indicador | definición | peso MEDI | fuente |
|---|---|---|---|
| Sin electricidad | `VPH_S_ELEC / VIVPARH_CV` | 0.24 | Censo 2020, ITER por AGEB y municipio |
| Sin refrigerador | `(VIVPARH_CV − VPH_REFRI) / VIVPARH_CV` | 0.21 | Censo 2020, ITER por AGEB y municipio |

`VIVPARH_CV` = *viviendas particulares habitadas con características captadas*.
Es el universo sobre el que INEGI calcula todos los `VPH_*`; usar `VIVPAR_HAB`
produce porcentajes negativos ([ADR-0001](adr/0001-fuente-oficial-inegi-y-denominador.md)).

Dos niveles:

- **Municipio** (2 469): totales oficiales del municipio, urbano + rural. La
  población suma 126 014 024, la nacional de 2020.
- **AGEB urbana** (64 313): sólo localidades de 2 500 habitantes o más (o
  cabeceras municipales). Lo rural no tiene AGEB en el ITER; queda cubierto
  únicamente por el municipal.

## 2. Fuentes y procedencia

| insumo | dónde | libreta |
|---|---|---|
| Marco Geoestadístico 2020 integrado (`00a` AGEB, `00mun`, `00ent`) | `data/raw/INEGI/mg_2020/` + `SOURCE.md` (URL, fecha, SHA-256) | 004 |
| Principales resultados por AGEB y manzana urbana, 32 zips | `data/raw/INEGI/iter_2020/ageb_manzana/` | 005 |
| Extracto `bd_MEDI_AGEB.csv` (verificación cruzada) | `data/raw/INEGI/iter_2020/` | 005 |

Licencia: Términos de Libre Uso de la Información del INEGI.

## 3. Reglas de procesamiento

1. **Claves.** `cvegeo` de 13 = `ENT(2)+MUN(3)+LOC(4)+AGEB(4)`, reconstruida
   desde las partes con relleno de ceros; la columna concatenada del extracto
   pierde ceros en 2 194 filas. Se limpia una comilla espuria (`'0030`).
2. **Unión con el marco.** Primero por clave de 13 contra las AGEB urbanas del
   marco (63 982); las 331 restantes existen como AGEB *rurales* (clave de 9,
   sin localidad) y se unen así (`ambito_mgn = rural`). Ninguna queda sin polígono.
3. **Asteriscos.** `*` = menos de 3 unidades. Se guardan como nulo con bandera
   (`ok | censurado | sin_viviendas`); el porcentaje es nulo si falta numerador
   o denominador. Electricidad lleva `p_sin_elec_sup`, cota superior
   `min(2, VIVPARH_CV − VPH_C_ELEC) / VIVPARH_CV` ([ADR-0002](adr/0002-asteriscos-censura.md)).
4. **CRS.** El marco viene en Lambert (EPSG:6372, sin código en el `.prj`).
   Centroides y simplificación se calculan en 6372; los productos se escriben
   en EPSG:4326 ([ADR-0003](adr/0003-crs-4326-almacenar-6372-medir.md)).
5. **Productos** en `data/derived/INEGI/2020/`, catalogados en `data/stac/inegi/`
   ([ADR-0004](adr/0004-geoparquet-y-stac-table.md)): `medi_ageb_2020.parquet`,
   `medi_mun_2020.parquet`, `medi_ageb_2020_grid.parquet` (tabla puente).

## 4. El cruce con el UTCI

Cada AGEB se asigna a la celda de 0.25° de la malla ERA5 que contiene su
centroide (`lat_c`, `lon_c`, centros en múltiplos de 0.25°). Al hacer clic en
una celda, el pie de página suma numerador y denominador de las AGEB **no
censuradas** de esa celda y reporta cuántas se usaron. Es una asignación por
centroide, no por área: una AGEB grande que cruza dos celdas cuenta entera en
una. A 0.25° (~27 km) el efecto es marginal para AGEB urbanas (< 1 km típicas).

## 5. Cómo se pinta

- Clases por **cuantiles nacionales** (6), fijas por nivel e indicador, para
  que dos ciudades sean comparables. Si más de un sexto de los valores son
  cero (electricidad por AGEB), la primera clase es exactamente "0 %".
- Gris = sin dato (censurado o sin viviendas con características); la leyenda
  dice cuántos.
- AGEB **por ventana** a partir de zoom 11, simplificadas a medio píxel
  ([ADR-0005](adr/0005-ageb-por-ventana-vector.md)).

## 6. Limitaciones conocidas

- Censura: `p_sin_elec` nulo en 22 053 AGEB (34 %); `p_sin_refri` en 5 888 (9 %).
  En municipios: electricidad nula en 103, refrigerador completo.
- `NOM_LOC` en las filas AGEB del ITER es "Total AGEB urbana": no hay nombre de
  localidad en el tooltip.
- Sólo AGEB urbanas: los huecos entre ciudades no son "sin carencia", son "sin
  AGEB".
- Temporalidad: Censo 2020 (referencia 15 de marzo de 2020) frente a UTCI anual
  2022–2023. Las capas son estáticas hasta el próximo censo.
- El extracto `bd_MEDI_AGEB.csv` tiene errores propios (Sonora, una fila de BC,
  una AGEB faltante); no se usa para el producto.

## 7. Qué sigue (fuera de esta fase)

Teléfono y radio/TV (mismo flujo, otra columna), CONEVAL municipal
2010/2015/2020, capas estatales de combustible/chimenea, ENCEVI 2018 por región
climática, y una vista de dispersión "horas en nivel X vs % sin refrigerador".
