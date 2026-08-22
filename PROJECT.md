# PROYECTO: trading-research — Búsqueda de edge experto/pro en crypto

> Proyecto de I+D **separado** del bot v9. Objetivo: un conjunto de estrategias
> sistemáticas con **PF ≥ 1.5 sostenido out-of-sample**, riesgo estrictamente controlado.
> No es "máximo beneficio en el menor tiempo" — eso es receta de blow-up.

---

## 1. Propósito (North Star)

Desarrollar, como proyecto de investigación autónomo, un **portfolio de estrategias
sistemáticas** para crypto (spot + perpetuos) que alcance un **Profit Factor (PF) ≥ 1.5**
en validación **out-of-sample (OOS)**, neto de fees + slippage realista + compuesto,
con drawdown acotado. El edge debe ser **real y robusto**, no un artefacto de overfit.

### Por qué un proyecto nuevo (no un parche a v9)
- **v9** = infra de ejecución autónoma (abre/cierra, OCO, self-heal, mutator, multi-par). Funciona → queda **congelada en testnet** como "la infra ya hecha".
- **Este proyecto** = investigación de alpha (edge). Objetivos y ciclos distintos.
- Separar evita romper lo que funciona y mantiene los gates de calidad limpios.

---

## 2. Criterios de éxito (medibles)

| Métrica | Umbral de ÉXITO | Umbral de EXCELENCIA |
|---|---|---|
| PF agregado OOS (walk-forward 2-3a, neto fees+slip+compuesto) | **≥ 1.5** | ≥ 2.0 |
| Max drawdown (backtest) | ≤ 20% | ≤ 12% |
| Sharpe anualizado (backtest) | ≥ 1.0 | ≥ 1.5 |
| Supera el baseline v9 (PF ~1.2) | sí, por margen claro | — |
| Racha perdedora acotada | no mata el capital | — |

**Solo si se cumple ÉXITO en OOS** → se abre la puerta a migrar a ejecución (staging $50-100, no más).

> Nota: un experto real ronda PF 1.5-2.0 sostenido. Por encima de 2.0 casi siempre es overfit o esconde cola de riesgo. El target 1.5 es ambicioso pero honesto.

---

## 3. No-objetivos / Guardarraíles (explícitos, no negociables)

- ❌ **Sin apalancamiento para inflar PF.** El leverage no sube el edge; amplifica el riesgo de blow-up. (El perfil `agresivo_2x` de v9 — 120% size + 2x — es el ejemplo de lo que NO hacer.)
- ❌ **Sin overfit.** Validación OOS obligatoria. Prohibido ajustar parámetros mirando el OOS.
- ❌ **Sin dinero real** hasta pasar el gate de staging.
- ❌ **Sin perseguir velocidad.** "Máximo beneficio en el menor tiempo" = volar la cuenta.
- ❌ Acoplar este repo al bot v9 en producción (clean slate: v9 es solo lección, no base de código).

---

## 4. Alcance técnico

- **Repo:** **público** en GitHub (`trading-research`). Contenido 100% no-sensible (datos de mercado públicos, sin credenciales). Ver `.gitignore` (excluye secrets, datos y estado runtime).
- **Clean slate:** NO se basa en v9. v9 queda solo como fuente de lecciones (qué no hacer: testnet como validación, single-strategy, backtester sin tests, perfil 2x). Se escribe código nuevo desde cero, con tests unitarios en el close engine y harness reutilizable.
- **Datos:** **sin credenciales**. Fase A: **Coinbase** (spot, klines públicas, sin API key). Para la estrategia de funding carry (Fase D) se evalúan **Kraken Futures / Bybit / OKX** — esos sí requieren credenciales y se dejan para staging (gate de OOS aprobado).
- **Harness multi-estrategia:** capaz de combinar y medir el PF agregado de varias estrategias no correlacionadas.
- **Estrategias objetivo:**
  1. **Trend-following** (mejorado respecto a v9 — el trailing es el punto débil actual).
  2. **Mean-reversion** (no correlacionada con tendencia).
  3. **Captura de funding rate / market-neutral** (carry, casi puro alpha por estructura).
- **Regime detection:** volatilidad, fuerza de tendencia, para no operar en mercados muertos.
- **Sizing:** Kelly fraccionado por estrategia + cap de riesgo por régimen (1-2% capital por trade, no 28% como v9).
- **Ejecución simulada:** maker-only (rebates), slippage realista, compuesto.
- **Framework OOS walk-forward:** ventanas in/out, 2-3 años de datos reales.

---

## 5. Fases (cada una con gate de aceptación)

- **A — Cimientos de medida (obligatoria).** Reparar el backtester del repo (bug de mislabel SL/trailing que hoy nos engañó), armar harness multi-estrategia, framework OOS walk-forward, fees+slip+compuesto.
  - *Gate:* backtest reproducible y fiable. Sin esto, cualquier claim de PF es basura.
- **B — Señal de entrada.** Regime detection, señales alternativas (breakout, pullback, volumen), validar en OOS.
  - *Gate:* mejora de PF base demostrada fuera de muestra.
- **C — Salida (overhaul).** El trailing actual destruye P&L; probar TP fijo vs trailing vs tiempo, exits escalados.
  - *Gate:* mejora medible sin overfit.
- **D — Diversificación (el multiplicador real).** Mean-reversion + funding carry + control de correlación.
  - *Gate:* PF agregado > suma de partes (diversificación aporta, no solo ruido).
- **E — Sizing y ejecución.** Kelly fraccionado, maker-only, cap de riesgo por régimen.
  - *Gate:* PF neto estable tras todos los costes.
- **F — Reevaluar con evidencia.** Si OOS ≥ 1.5 → staging real ($50-100). Si ~1.3 → aceptar o archivar.

---

## 6. Restricciones / Gobernanza

- **Calidad (NÚCLEO):** `py_compile` + tests + backup antes de cada cambio. Nunca commitear sin validar.
- **Modelo:** `hy3-free` para análisis/interactivo (este chat). El cron de v9 (`auto-trade-v9`, deepseek-v4-flash) **no se toca**.
- **Sin acciones en vivo:** no órdenes reales, no crear repos externos, sin OK explícito.
- **Commits:** código y documentación por separado.
- **GitHub = fuente de verdad (canónica).** Este repo en GitHub es la fuente; las copias en local o en contenedores (CT 113 `/opt/freqtrade/user_data`) son **artefactos de despliegue**, no fuente. Si discrepan, manda GitHub. Verificar contra la API tras cada push.
- **Estructura de repo disciplinada:** `scripts/` (análisis/utilidades), `strategies/` (freqtrade), `tests/` (unitarios). Al mover/añadir código, actualizar `PROJECT.md` + `README.md`.
- **Ritual de push:** embeber el token real en la URL, **nunca** el placeholder; tras el push, limpiar el token del remote local. Scan anti-secret (`grep -rniE 'ghp_|github_pat_|password'`) antes de cada commit.

---

## 7. Definición de Hecho (DoD)

El proyecto está "listo para decidir" cuando:
1. Hay un backtest OOS reproducible del portfolio multi-estrategia.
2. El PF y drawdown cumplen los umbrales de ÉXITO.
3. Se documenta la decisión: migrar a staging / archivar / iterar.

---

## 8.1 Selección de pares (screening data-driven)

No por intuición. Criterios y método:
- **Liquidez profunda** (top-tier: BTC, ETH, SOL, BNB, XRP…) y medir slippage real, no asumir.
- **Historia larga y limpia** (4+ años de klines) para el walk-forward.
- **Correlación baja entre lo que aporta** → calcular matriz de correlación; evitar duplicar la misma señal (lección v9: BTC/ETH/SOL/LINK bailan igual → poca diversificación real).
- **Funding disponible** para la estrategia de carry/market-neutral (perpetuos).
- **Comportamiento por régimen** (bull/bear/chop).
- **Método:** descargar pares elegibles, calcular liquidez/volatilidad/matriz de correlación, backtestear cada uno **por separado** antes de combinar. Nada entra al portfolio sin pasar OOS individual.

## 8.2 Sistema "vivo" / adaptativo (autogestión con límites)

El proyecto puede ser un sistema que se adapte y autogestione, **pero la adaptación debe ser disciplinada o es máquina de blow-up**.

**SÍ hace (seguro):**
- Orquestador de investigación periódico (semanal/mensual): re-corre walk-forward, comprueba gate de PF por estrategia, retira las muertas, ajusta asignación por rendimiento *validado*, reacciona al régimen.
- Auto-gestión de riesgo: capa que baja exposición si el drawdown se acerca al límite.
- Cambios auditables: cada ajuste → `decision_log.md` (memoria de qué funcionó).

**NO hace (riesgo):**
- Mutar parámetros persiguiendo el retorno reciente (overfit a ruido → blow-up).
- Auto-desplegar a mainnet sin OK humano.

**Límite honesto:** el "aprendizaje" es a nivel de *investigación* (mejorar diseño, jubilar fallidas), **no** "descubrir alpha nuevo en vivo". El orquestador solo mueve parámetros **dentro de rangos fijos y validados OOS**; prohibido inventar fuera de rango o cambiar estrategias sin re-pasar el gate. Deploy a mainnet siempre pasa por OK humano.

> Esto es la versión limpia del mutator de v9: adaptación acotada y validada, no libre.

---

## 9 Notas de contexto (legacy v9)
- El backtester del repo v9 estaba **roto** (etiquetaba stop-loss como trailing), dando números falsos.
- Con lógica corregida, el portfolio v9 da **PF ~1.2** (363 trades, fees reales) — un edge **frontera** que **no compensa el riesgo** del perfil 2x (~28% de capital por SL).
- Un experto real saca PF 1.5-2.0 vía: múltiples estrategias no correlacionadas, mejor señal, sizing estricto y ejecución barata.
- Este proyecto persigue exactamente eso: subir el edge de ~1.2 al rango experto, **con disciplina**, no con apalancamiento.
