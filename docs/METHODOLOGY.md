# Metodología — Atlas

> Cómo trabajamos y aprendemos en este proyecto. No es una lista de pasos ni un
> calendario (para eso están los planes de [planes/](planes/) y los temarios
> [TEMARIO.md](TEMARIO.md) / [TEMARIO-items.md](TEMARIO-items.md)). Es una
> **forma de proceder** que se aplica igual a una decisión de una línea o a un
> módulo entero, y que pone en el centro **cuestionar cada elección contra la
> evidencia y la literatura**.

---

## 1. Principios rectores

Toda decisión y todo entregable se juzgan contra estos principios.

1. **Reconstruir para entender.** Se aprende rehaciendo, no leyendo la solución.
   El código existente es referencia, no plantilla a copiar.
2. **Ninguna tecnología es la elección por defecto.** Cada herramienta (Zarr,
   Shiny, ipyleaflet, un codec, un colormap) entra a prueba. "Ya estaba" o "es
   popular" no son razones; lo es la evidencia frente a *este* problema.
3. **Evidencia sobre opinión.** Una afirmación técnica se respalda con un
   experimento propio (*spike*/benchmark) **y** una referencia. Sin una de las
   dos, es una hipótesis, no una decisión.
4. **Contrato antes que código.** La frontera entre módulos (p. ej. el esquema
   del cubo) se acuerda y se vuelve ejecutable (pruebas/fixtures) *antes* de
   construir a ambos lados. Eso permite trabajar en paralelo sin acoplarse.
5. **Núcleo independiente de la interfaz.** La lógica (cómputo, ingesta) no debe
   depender del framework de UI. Lo testeable y reusable vive en el paquete; la
   app solo lo consume.
6. **Lo más simple que funcione hoy, abierto a mañana.** Se construye el corte
   vertical más delgado que sirva de punta a punta; la extensibilidad se reserva
   solo donde hay una razón concreta (p. ej. el índice *pluggable*), no "por si
   acaso".
7. **Reproducibilidad como requisito.** Un tercero clona y reproduce con `uv`.
   Datos fuera de Git, dependencias bloqueadas, comandos documentados.

---

## 2. El ciclo de trabajo

Cualquier unidad de trabajo —elegir un codec, escribir la ingesta, pintar el
mapa— atraviesa el mismo ciclo. Es **iterativo y recursivo**: un módulo grande es
un ciclo que contiene ciclos más pequeños.

```
        ┌──────────────────────────────────────────────┐
        ▼                                                │
   ENMARCAR → INDAGAR → PROTOTIPAR → DECIDIR → IMPLEMENTAR → VALIDAR → INTEGRAR → REFLEXIONAR
                                                                                      │
        └──────────────── (lo aprendido reabre el ciclo) ─────────────────────────────┘
```

1. **Enmarcar.** ¿Qué problema real resuelve esto y cuáles son los *patrones de
   uso concretos*? (Ej.: "pintar el campo de un día" y "leer la serie de una
   celda" son patrones distintos que tiran del diseño en direcciones opuestas).
   Escribe los supuestos explícitamente.
2. **Indagar.** Revisa documentación y literatura de las opciones candidatas
   (§4). Sal con una lista corta de alternativas, no con una sola.
3. **Prototipar (*spike*).** Experimento mínimo y desechable, *time-boxed*, para
   generar evidencia: un benchmark de chunking, un mapa que pinta un fixture, una
   medición de tamaño con dos codecs. El objetivo es aprender, no entregar.
4. **Decidir.** Elige con un criterio explícito y **registra un ADR** (§3),
   incluyendo qué te haría reconsiderar.
5. **Implementar.** Ahora sí, código de calidad que se lee como el de alrededor;
   commits pequeños; respeta el contrato.
6. **Validar.** Pruebas automáticas donde aplique; verificación manual del
   comportamiento real (no solo "compila"). Si falla, se reporta tal cual.
7. **Integrar.** Conecta con el otro módulo *pronto y seguido*; la integración no
   es una fase final, es un hábito.
8. **Reflexionar.** ¿Qué invalidó tus supuestos? Eso reabre el ciclo o agenda un
   ítem nuevo.

> La regla: **ningún código de producción antes de Enmarcar + un mínimo de
> Indagar/Prototipar.** El prototipo puede durar 30 minutos; saltárselo no.

---

## 3. Registro de decisiones (ADR)

Cada decisión no trivial se guarda como **ADR** (*Architecture Decision Record*),
ligero, en `docs/adr/NNNN-titulo.md`. Su valor no es burocrático: obliga a
articular el porqué y deja rastro para revisarlo cuando cambien los supuestos.

**Plantilla:**
```
# ADR-NNNN — <decisión>
Estado: propuesto | aceptado | reemplazado por ADR-XXXX
Contexto:        el problema y los patrones de uso reales.
Opciones:        candidatos considerados (incluido "no hacer nada" / statu quo).
Criterios:       qué pesa y por qué (derivado de ESTE proyecto).
Evidencia:       spike/benchmark propio + referencias de literatura.
Decisión:        qué se elige.
Consecuencias:   lo que ganamos, lo que cedemos, deuda asumida.
Revisión:        qué señal nos haría reconsiderar.
```

Un ADR sin la fila **Evidencia** está incompleto.

Los ADR existentes están en [adr/](adr/) (0001–0005, fase de capas INEGI).

---

## 4. Marco para cuestionar una tecnología

Procedimiento repetible cada vez que una herramienta entra a juicio. Es el
corazón de la metodología.

1. **Enuncia el problema y los patrones de uso** (no genéricos). "Almacenar datos"
   es vago; "leer el campo de un día al instante y, ocasionalmente, la serie de
   una celda, con escritura por *append* anual" decide el diseño.
2. **Deriva criterios ponderados *de este proyecto*.** Ej.: lectura perezosa,
   escalabilidad a años/variables, costo de escritura incremental, reproducibilidad,
   madurez/comunidad, costo de operación. Pondéralos.
3. **Lista candidatos honestos**, incluyendo el statu quo y la opción "no hacerlo"
   o "lo más simple". Cuestionar no es cambiar; a veces confirma.
4. **Reúne evidencia de dos fuentes:**
   - *Propia*: un spike/benchmark sobre tus datos y patrones reales.
   - *Literatura*: documentación primaria, especificaciones, papers, comparativas.
5. **Lee la literatura con criterio.** Prefiere fuente primaria (docs/spec/paper)
   sobre blogs; vigila la fecha (¿sigue vigente?); detecta sesgo (un benchmark de
   un vendedor sobre su producto); distingue "popular" de "adecuado".
6. **Compara en una matriz** criterio×candidato y **decide y registra** (ADR),
   con las **condiciones de revisión** ("reconsiderar si el cubo supera N TB" o
   "si hay escritura concurrente").

> Cuestionar bien produce uno de tres resultados, todos válidos: **confirmar** la
> elección con más fundamento, **cambiarla**, o **acotar cuándo deja de servir**.

---

## 5. Modelo de colaboración (dos roles, un sistema)

- **El contrato es la frontera.** Mientras ambos respeten el esquema acordado,
  cada quien itera a su ritmo sin pisar al otro.
- **Fixtures para desacoplar.** Quien depende de un artefacto aún inexistente
  (p. ej. la app necesita el cubo) trabaja contra un *fixture* sintético que
  cumple el contrato. Nadie se bloquea esperando.
- **Integrar temprano y seguido.** Conectar los módulos es un hábito continuo, no
  un evento final; los desajustes se descubren mientras son baratos.
- **Revisión cruzada y adversaria.** Cada quien **intenta refutar el ADR del
  otro**. El objetivo no es ganar, es endurecer la decisión.

---

## 6. Definición de "hecho"

Una unidad de trabajo está terminada cuando:

- [ ] El entregable funciona y se demostró con comportamiento real (no solo "corre").
- [ ] Existe un ADR con evidencia (spike + ≥1 referencia) si hubo una decisión técnica.
- [ ] Respeta el contrato de interfaz (si toca la frontera) y sus pruebas pasan.
- [ ] El código se lee como el de alrededor; commits pequeños y con mensaje claro.
- [ ] Es reproducible con `uv`; los datos no entraron a Git.
- [ ] Lo que quedó pendiente o incierto está anotado (supuestos, deuda, riesgos).

---

## 7. Incertidumbre y riesgo

- **Decisiones reversibles vs irreversibles.** Las reversibles (de "puerta de
  doble sentido") se toman rápido y se corrigen si hace falta; las difíciles de
  revertir (formato del store, esquema del cubo) merecen más spike y un ADR firme.
- **Spikes *time-boxed*.** Si una indagación se alarga, se acota el tiempo y se
  decide con lo que haya; la perfección informativa no es el objetivo.
- **Supuestos a la vista.** Todo supuesto se escribe; un supuesto tácito es un
  riesgo oculto. Convertir fechas relativas, unidades, husos horarios, etc.

---

## 8. Cómo se evalúa el aprendizaje

No por "terminar pasos", sino por:
- la **calidad del razonamiento** en los ADRs (criterios claros, evidencia real);
- la capacidad de **defender o refutar** una elección con datos y fuentes;
- una **integración funcional** de punta a punta entre los dos módulos;
- la **reproducibilidad** del resultado por un tercero.
