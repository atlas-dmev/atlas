# Plan 05 — incorporar las AGEB rurales al atlas (antes PLAN-AGEB-RURAL.md)

Objetivo: cerrar el hueco de cobertura del nivel AGEB. Hoy la capa AGEB sólo
tiene las 64 313 AGEB **urbanas** del ITER (100.3 M de personas); lo rural
(cerca de una quinta parte de la población, donde más pesan la leña, la falta
de electricidad y de refrigerador) sólo aparece diluido en el municipio. El
Censo 2020 sí publica lo necesario para construir las **AGEB rurales**, con las
mismas variables y el mismo denominador que las urbanas.

## Hechos verificados (2026-09-02)

| hecho | evidencia |
|---|---|
| El marco 2020 trae **17 469 AGEB rurales** como polígonos (`00a`, `Ambito = Rural`, clave de 9: `ENT+MUN+AGEB`) | libreta 004; ya extraídos en `data/raw/INEGI/mg_2020/` |
| La capa de **localidades rurales puntuales** (`00lpr`, dentro del zip del marco) tiene **295 779 puntos** y cada uno trae `CVE_AGEB`: cubren **16 399** de las 17 469 AGEB rurales (el resto no tiene localidad habitada o es sólo territorio) | inspección del zip |
| El **ITER nacional** (`iter_00_cpv2020_csv.zip`, 36.6 MB) publica una fila por **localidad**, urbana y rural, con las 230 variables del cuestionario básico, incluidos `VIVPARH_CV`, `VPH_S_ELEC`, `VPH_REFRI`, `VPH_SINLTC`, `VPH_SINRTV` | `HEAD` 200 en `https://www.inegi.org.mx/contenidos/programas/ccpv/2020/datosabiertos/iter/iter_00_cpv2020_csv.zip` |
| Censura INEGI en localidades: indicador con < 3 unidades → `*`; en localidades de **1 o 2 viviendas** sólo se publican `POBTOT`, `VIVTOT` y `TVIVHAB` (todo lo demás `*`) | descriptor del ITER (mismo criterio que AGEB/manzana) |
| **331 AGEB** que hoy están en el producto con datos del ITER urbano existen en el marco como rurales (contienen una localidad urbana) | libreta 004/005, `ambito_mgn = rural` |

Consecuencia: la AGEB rural se construye **sumando las localidades rurales que
contiene**, por clave, sin ninguna operación espacial; y como las localidades
son puntos, el cruce con la malla UTCI mejora (cada localidad va a su celda,
sin depender del centroide de un polígono que puede medir cientos de km²).

## Diseño (propuesta original; la implementación final se describe en los hitos)

> Diferencias al implementar: la tabla puente **no** es un archivo nuevo sino
> `medi_ageb_2020_grid.parquet` ampliado con una fila por localidad rural
> (`unidad = localidad`); las 331 AGEB mixtas quedaron con su fila urbana; en
> el ITER por localidad la censura es por localidad completa, así que no hizo
> falta la cota por localidad censurada (`n_loc_sin_dato` cuenta las de 1–2
> viviendas); el zoom mínimo quedó en 10.

```
ITER nacional (localidades)  +  00lpr (punto → AGEB rural)  +  00a rural (polígonos)
   │  011_ITER_rural.ipynb
   ▼
medi_ageb_2020.parquet  ← + 16 399 AGEB rurales (ambito = rural), mismas columnas
medi_loc_2020_grid.parquet ← nueva tabla puente por LOCALIDAD (urbana y rural) → celda UTCI
   │  009 → 010 → 007 (reejecutar: clima, MEDI y STAC incluyen ahora lo rural)
   ▼
app: capa AGEB por ventana ya pinta rurales; leyenda y tooltip avisan el ámbito
```

### Producto AGEB (mismo esquema, filas nuevas)
- Filas rurales con `cvegeo` de 9 caracteres (`ENT+MUN+AGEB`), `cve_loc`
  nulo, `ambito = rural`, `n_localidades`, `n_loc_censuradas`.
- Numerador y denominador **sumados** sobre las localidades de la AGEB;
  porcentajes y banderas con la misma regla que lo urbano. Cota superior por
  censura: 2 viviendas **por localidad censurada** (`p_*_sup`), no por AGEB.
- Los tres componentes del ampliado y la calefacción se heredan del municipio
  (las localidades rurales nunca son ≥ 50 k).
- Las **331 AGEB mixtas** se completan: a su fila urbana actual se le suman
  las localidades rurales que contengan (decisión 1).

### Tabla puente por localidad
- `medi_loc_2020_grid.parquet`: una fila por localidad con población, denominadores,
  numeradores, banderas, `cvegeo_ageb`, `ambito`, `lat_c`/`lon_c` de su celda.
  Las urbanas se derivan de las AGEB actuales (centroide); las rurales, del punto.
- `stac.medi_at` pasa a leer esta tabla: el resumen por celda incluye lo rural
  y reporta población y viviendas urbanas/rurales por separado.

### Regla climática y MEDI
- Para AGEB rurales, `h_calor`/`h_frio` = promedio de sus localidades
  ponderado por población (no el centroide del polígono).
- Municipio y estado recalculan la necesidad climática con todas sus
  localidades, no sólo las AGEB urbanas.
- MEDI rural con intervalo, igual que urbano; ninguna fórmula cambia.

### App
- La capa AGEB por ventana dibuja rurales y urbanas; las rurales con opacidad
  menor (0.45 del valor del slider) y borde punteado, para no sugerir
  uniformidad en polígonos grandes (decisión 2).
- Clases por cuantiles: **una sola escala nacional** con urbanas y rurales,
  para que el color sea comparable (decisión 3); la leyenda muestra cuántas
  unidades de cada ámbito hay.
- Tooltip: ámbito, número de localidades y cuántas están censuradas.
- Umbral de zoom: las AGEB rurales son grandes; podrían mostrarse desde zoom 9.
  Medir tamaño de GeoJSON por ventana antes de decidir.

## Hitos

- [x] **R0 — Descarga del ITER nacional (011).** 36.6 MB con `SOURCE.md`.
  Nacional = 126 014 024 ✓; 189 432 localidades (sin las filas agregadas
  9998/9999) suman exactamente la nacional; 82 012 localidades de 1–2
  viviendas (415 mil personas) sólo publican población.
- [x] **R1 — Localidad → AGEB rural (011).** 184 190 localidades rurales con
  punto y AGEB (25.7 M de personas); 0 localidades del ITER sin punto rural
  ni AGEB urbana. Hallazgo: en el ITER por localidad la censura es por
  localidad completa, no por indicador, así que toda AGEB rural con
  denominador tiene sus cuatro numeradores.
- [x] **R2 — Producto AGEB rural (011).** 14 868 AGEB rurales (12 873 con
  indicadores, 1 995 sin viviendas con características; 2 601 polígonos sin
  localidad habitada no aparecen), todas con polígono, escritas junto a las
  urbanas: 79 181 filas, 203 MB (los polígonos rurales pesan). Medianas
  rurales: sin refrigerador 18.6 %, sin teléfono 21.2 %, sin radio/TV 9.9 %,
  sin electricidad 1.4 %.
- [x] **R3 — Tabla puente por localidad (011)** y `medi_at` con unidades
  urbanas y rurales por separado: 248 503 filas; 2 929 celdas con población
  (antes 1 381). Una celda del desierto de Sonora que antes daba "sin AGEB"
  ahora reporta 3 localidades y 614 personas.
- [x] **R4 — Reejecutar 009 → 010 → 007.** Umbrales climáticos 902 / 626 h
  (antes 912 / 625: dentro de ±5 %); 47.8 % de las AGEB necesitan AC. MEDI en
  71 917 de 79 181 AGEB; ranking estatal sin cambio (los estados y municipios
  no dependen de las AGEB). STAC con 79 181 filas en `medi-ageb-2020`.
- [x] **R5 — App.** Rurales con 45 % de opacidad y trazo punteado; tooltip
  "AGEB rural · N localidades, M de 1–2 viviendas sin indicadores"; resumen
  por celda con AGEB urbanas y localidades rurales y su población; umbral de
  zoom bajado a 10 (medición: Oaxaca rural 2.4 MB a zoom 9, 1.1 MB a zoom 10;
  CDMX 6.5 MB a zoom 9, 4.3 MB a zoom 10). Verificado en Chromium: ventana de
  valles centrales de Oaxaca a zoom 10 con 506 AGEB, 189 rurales punteadas.
- [x] **R6 — Documentación.** ADR-0008, `docs/DATOS-INEGI.md` §12,
  `docs/SUPOSICIONES.md` (§2, §4, §5, §8, FAQ), README (orden del pipeline
  con 011).

## Riesgos

- **Censura alta.** Muchas localidades rurales tienen 1–2 viviendas y publican
  sólo población: la AGEB rural tendrá numeradores incompletos aunque el
  denominador sea conocido. El intervalo min–max será más ancho que en lo
  urbano; hay que mostrarlo, no esconderlo.
- **Polígonos grandes.** Una AGEB rural puede abarcar varias celdas UTCI y
  cientos de km²; el color uniforme exagera. La opacidad reducida y el
  tooltip con número de localidades mitigan, no resuelven.
- **Tamaño por ventana.** 17 469 polígonos rurales tienen muchos vértices;
  medir antes de bajar el umbral de zoom.
- **Dobles conteos** en las 331 AGEB mixtas si se suman localidades urbanas
  ya incluidas: la unión debe excluir explícitamente las localidades urbanas.

## Decisiones (confirmadas el 2026-09-02)

1. Las 331 AGEB mixtas quedan con su fila urbana; sus localidades rurales no
   se suman (mezclaría dos fuentes en una fila). **Confirmado.**
2. Rurales con opacidad reducida (45 %) y trazo punteado. **Confirmado.**
3. Una sola escala de clases nacional para urbanas y rurales. **Confirmado.**
4. Umbral de zoom de la capa AGEB: 10. **Confirmado.**
5. El nivel "localidad" sólo alimenta el resumen por celda; una capa de puntos
   rurales queda como trabajo opcional. **Confirmado.**
