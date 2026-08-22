# Decision Log — trading-research

Registro auditable de decisiones y su justificación. (Criterio del PROJECT.md: cada cambio/ajuste se documenta.)

---

## 2026-08-22 — Setup inicial del proyecto

**Decisión:** Crear proyecto nuevo `trading-research` (clean slate, no basado en v9) para buscar edge experto/pro (PF ≥ 1.5 OOS).

**Justificación:**
- v9 tiene edge frontera (~PF 1.2) que no compensa el riesgo del perfil 2x (28% capital por SL). Mejor buscar edge mejor con disciplina que operar ciego.
- No construir backtester desde cero: usar **freqtrade** (OSS maduro: backtest OOS, hyperopt). Trabajo propio = señales (edge) + orquestador adaptativo.
- **Sin credenciales**: Fase A usa datos públicos de Coinbase.

**Infra montada:**
- Contenedor Docker `freqtrade` (imagen `freqtradeorg/freqtrade:stable`) en CT 112 (`docker-apps`, Proxmox 192.168.1.222). Límites `--cpus 2 --memory 2g`. Volumen `/docker/freqtrade/user_data`.
- Exchange para Fase A: **Coinbase** (spot, klines públicas, sin API key). Kraken descartado para Fase A (no sirve klines directos → `--dl-trades` muy lento); reservado para funding carry (Fase D).
- 9 pares candidatos descargados (Coinbase 2h, 2020→2026): BTC, ETH, SOL, XRP, ADA, DOGE, DOT, AVAX, LINK. BNB/MATIC/LTC no listados en Coinbase spot USDT → descartados. **Son candidatos a screening, NO pares elegidos** (la selección final es data-driven: liquidez + matriz de correlación + backtest individual OOS, según PROJECT.md §8.1).

**Repo GitHub:** `hrodres/trading-research` (**público** — contenido no-sensible, datos de mercado públicos, sin credenciales). Token de GitHub usado vía variable de entorno y limpiado del remote local tras el push.

**No hecho aún:** estrategias, backtests. Primero verificar entorno (hecho) y luego screening de pares + Fase A (walk-forward OOS de la señal simple).

**Riesgo conocido:** contención de CPU con chromium si se corre backtest grande en CT 112 (mitigado con `--cpus 2`).

---

## 2026-08-22 — Fase A.1: Screening de pares (CORREGIDO)

**Contexto:** La 1ª versión de `screening.py` alineaba precios por POSICIÓN en vez de por FECHA → correlaciones espurias ~0 para pares con distinto inicio. Bug confirmado y corregido (alineación por fecha + liquidez en USDT). Ver commit de `screening.py`.

**Datos:** Coinbase 2h. Cobertura por par:
- BTC/ETH: 2021-05 → 2026-01 (20528 velas)
- SOL 2021-06, DOGE 2021-06, DOT 2021-06, AVAX 2021-09, ADA/LINK 2022-02, **XRP 2023-07** (10906 velas, el más corto).
- **Periodo común (todos los pares): 2023-07-13 → 2026-01-08 = 10113 velas (~2.5 años).**

**Matriz de correlación (log-returns, periodo común):** rango 0.58–0.80. BTC↔ETH = 0.80 (la más alta, pero NO redundante: corte ≥0.80 no saltó). ETH↔LINK 0.75, DOT↔ADA 0.76, DOT↔LINK 0.74. **0 pares con corr ≥0.80 → no hay redundancia total; hay margen real para diversificar** (lección aplicada vs v9, que tenía todo amontonado).

**Liquidez (mediana USDT / vela 2h):** BTC $1.68M · ETH $1.13M · SOL $210K · XRP $120K · DOGE $57K · ADA $25K · AVAX $25K · LINK $14K · DOT $8.5K.

**Conclusiones (observación, NO elección de pares aún):**
1. Crypto es un mercado correlacionado de verdad (no ruido). Diversificación real ayuda pero no elimina el riesgo común (BTC mueve a casi todos).
2. **Caveat de historia:** el periodo común es solo ~2.5 años porque XRP arranca en 2023-07. BTC/ETH/SOL/etc. tienen ~4.6 años. Para el gate de 4+ años del PROJECT.md, **XRP queda fuera del gate final** (solo 2.5y) aunque se mida en el común.
3. **Liquidez fina** (DOT/LINK/AVAX/ADA <$30K/2h): riesgo de slippage real. Válidos para medir OOS; en staging habrá que acotar tamaño posición.

**Siguiente:** A.2 (estrategia baseline trend/momentum) + A.3 (walk-forward OOS por par). La elección de universo de pares se hace tras A.3, no ahora.

---

## 2026-08-22 — Fase A.2: Estrategia baseline (harness OOS validado)

**Decisión:** Crear `strategies/baseline_trend.py` (trend/momentum EMA20>EMA50, SL -10%, ROI 8/4/2%, sin leverage ni trailing) + `configs/backtest_baseline.json`. Objetivo: **validar el harness OOS**, no buscar edge.

**Resultado del backtest** (timerange 2023-05-01→2026-01-08, 9 pares Coinbase 2h, fees 1.2% peor tier, `stake_amount: unlimited` → sizing 100% balance compuesto):
- Trades: 356 · Win rate 52.0% (185/0/171)
- Avg profit: **-1.76%** · Total P&L: **-99.89%** (1000→~1 USDT)
- Drawdown: **99.89%** · Sharpe: **-3.66**
- Mejor par XRP -3.06% · Peor par BTC -26.41%

**Conclusión honesta:** la baseline es la línea base a superar; NO es edge (PF lejos de ≥1.5). Cumplió su propósito: **el harness OOS funciona** (backtest reproducible, fees+SL reales, salida en métricas).

**Dos aprendizajes reales del resultado:**
1. **TP asimétrico vs SL destruye PF.** ROI capa el gain en +8% pero SL = -10% + fees ~2.4%. Con 52% win rate la esperanza por trade es negativa. Esto es exactamente lo que la **Fase C (exits)** debe arreglar.
2. **El DD 99.89% es artefacto del sizing.** `stake_amount: unlimited` opera el 100% del balance por trade y compone. Eso NO representa el riesgo real del proyecto (1–2% por trade, según PROJECT.md). Para **A.3** se usará sizing acotado (el que cuenta para el gate PF≥1.5).

**Bloqueos técnicos resueltos (freqtrade 2026.7):** `--datadir` debe apuntar a `data/coinbase/` (donde están los `.feather` como `<PAIR>-2h.feather`); el config exige bloques `pairlists`, `entry_pricing`, `exit_pricing`, `order_types`. Anotado para reutilizar en A.3.

**Siguiente:** A.3 (walk-forward OOS por par con sizing 1-2% y validation fuera de muestra; aquí se decide el universo por datos, gate PF ≥ 1.5 OOS).

---

## 2026-08-22 — Fase A.3: Walk-forward OOS por par (resultado)

**Método:** 5 backtests anuales (2021-2025), los 9 pares a la vez (`max_open_trades=9`), `stake_amount=100` USDT fijo (**sizing acotado**, sin compuesto agresivo), fees 1.2%. Export trades por año y agrupado por par. Sin fitting en IS -> todo es OOS valido por construccion (evita overfit). Orquestador: `scripts/walkforward.py` (lee el zip auto-nombrado de freqtrade 2026.7 via `.last_result.json`).

**Resultado (PF agregado 2021-2025 por par):**
- SOL 0.395 (n=563, win 62.3%) | XRP 0.372 (244, 54.9%) | AVAX 0.346 (494, 60.5%)
- LINK 0.343 (424, 57.1%) | DOGE 0.340 (549, 57.4%) | ADA 0.332 (394, 54.1%)
- DOT 0.311 (454, 55.3%) | ETH 0.299 (408, 48.8%) | BTC 0.276 (335, 40.9%)
- **Pares que pasan el gate (PF>=1.5, n>=30, 4+yr): NINGUNO.**

**Conclusion honesta:** la estrategia baseline (tendencia EMA20>EMA50, SL -10%, TP +8%) **NO tiene edge** — PF ~0.3 en todos los pares (pierde ~2 de cada 3 USD que gana). El win rate alto (55-62%) engana: TP asimetrico (+8% cap) vs SL (-10% + fees) hace que cada win promedio < cada loss. BTC es el peor (PF 0.276, win 40.9%): la senal "compra alto, corta gains, SL en pullbacks" destruye P&L sistematicamente.

**Esto NO es fallo del harness** (que funciona y es reproducible) ni del proyecto. Es la medida honesta que las fases B/C/D deben superar. A.3 cumplio su objetivo: medir fuera de muestra sin overfit.

**Siguiente:** B (senal de entrada: regime detection, breakout, pullback, volumen) y C (exits: TP fijo vs trailing vs tiempo) para buscar donde SI hay edge. No se elige universo de pares todavia (seleccion data-driven tras OOS, segun PROJECT.md §8.1).

---

## 2026-08-22 — Fase C: Estudio de exits (resultado)

**Objetivo:** aislar el efecto del EXIT. Se mantiene la MISMA entrada que la baseline de A.3 (close > EMA20 > EMA50) y el mismo SL base -10%. Lo unico que cambia es la mecanica de salida cuando el trade esta en ganancia. Esto separa la pregunta "el exit es malo" de "la senal es mala".

**Variants (todas en `strategies/exit_study.py`, misma entrada):**
- `ExitFixedWide` : TP +10/5/3% + SL -10% + EMA-cross. Baseline "reparada" (ataque directo a la asimetria SL/TP de A.3).
- `ExitTrailing`  : trailing asimetrico (offset +10%, positivo +2%) + SL -10%. Deja correr tendencia, protege ganancias.
- `ExitEmaCross` : SOLO EMA-cross + SL -10% (sin ROI). "Let winners run": sale solo cuando la tendencia se invierte.
- `ExitTimeStop` : combo (TP+SL+EMA-cross) + tope temporal duro 4 dias.

**Metodo:** mismo que A.3 (walk-forward OOS por ano 2021-2025, 9 pares, sizing fijo 100 USDT, fees 1.2%). Sin fitting en IS -> todo OOS valido por construccion (evita overfit). Se corren las 4 variants en UNA pasada por ano via `--strategy-list` (freqtrade 2026.7 exporta un solo zip con `d["strategy"][nombre]`). Orquestador: `scripts/exit_study.py`. Referencia oficial freqtrade (stoploss.md) usada para el trailing asimetrico.

**Resultado (PF agregado 2021-2025, todas las monedas):**
| Variant | PF | n | win% | Mejor par (PF) |
|---|---|---|---|---|
| ExitEmaCross (dejar correr) | **0.65** | 1581 | 19.7 | SOL 0.98 |
| ExitTrailing (asim.) | 0.55 | 2208 | 27.6 | SOL 0.71 |
| ExitFixedWide (TP +10/5/3%) | 0.41 | 3413 | 49.9 | SOL 0.46 |
| ExitTimeStop (combo + tope 4d) | 0.39 | 3643 | 47.1 | SOL 0.44 |

**Pares que pasan el gate (PF>=1.5, n>=30, 4+yr): NINGUNO.** Mejor celda individual: ExitEmaCross SOL/USDT PF 0.979 (n=186), aun lejos de 1.5.

**Conclusion honesta (esto es lo importante de C):**
1. **El TP fijo corto era el asesino nº1.** La baseline de A.3 era IDENTICA salvo el TP cap a +8% en vez de dejar correr; pasar a ExitEmaCross (sin cap) sube el PF de ~0.3 a 0.65 (≈2x) solo cambiando el exit. El `minimal_roi` asimetrico destruia la esperanza matematica.
2. **Cuanto mas dejas correr al ganador, mayor el PF:** EMA-cross (0.65) > trailing (0.55) > fixed-wide (0.41) > time-stop (0.39). El TP fijo corto es lo peor; "let winners run" lo mejor.
3. **Pero ni el mejor exit llega a 1.5.** El cuello de botella NO es el exit: es la SENAL DE ENTRADA (EMA20>EMA50 no tiene edge real). El exit importa, pero no es suficiente.
4. **SOL/USDT** es el mejor par en las 4 variants (0.98/0.71/0.46/0.44): consistentemente el mas fuerte, pero aun lejos del gate.

**Decision de diseno:** fijar `ExitTrailing`/`ExitEmaCross` como exit por defecto del proyecto (nunca TP fijo corto) y dirigir el esfuerzo a **Fase B (senal de entrada)**. El exit esta resuelto a nivel de principio; el edge hay que buscarlo en la entrada.

**Siguiente:** Fase B (regime detection + breakout/pullback/volumen, validado OOS).

---

## 2026-08-22 — Fase B: estudio de señales de ENTRADA (COMPLETADA)

**Objetivo:** aislar el efecto de la ENTRADA. Todas las variants comparten el MISMO exit ganador de Fase C (ExitEmaCross: dejar correr hasta EMA-cross + SL -10%, sin TP fijo corto). Lo único que cambia es la condición de entrada. Reusa el patrón de C (`--strategy-list` en una pasada por año).

**Variants (7 en total, `strategies/entry_study.py`):**
- `EntryTrend` : EMA20>EMA50 (referencia de A.3/C).
- `EntryTrendADX` : EMA20>EMA50 + ADX>25 (filtra chop).
- `EntryBreakout` : ruptura máximo 20v (Donchian).
- `EntryPullback` : EMA20>EMA50 + pullback a EMA20 + RSI gira up.
- `EntryVolConfirm`: EMA20>EMA50 + volumen > 1.5x media.
- `EntryMeanRev` : RSI<30 en rango (contrarian, contraste).
- `EntryV9Style` : estilo de ENTRADA del bot v9 (forense). score_bull >=2 de 3: momentum (precio>SMA20 y RSI 45-65) + volume_support (cerca soporte 50v) + engulfing_bull (RSI<=40, vol>=1.2x media).

**Método:** walk-forward OOS por año 2021-2025, 9 pares, sizing fijo 100 USDT, fees 1.2‰, sin fitting en IS → todo OOS por construcción. Ejecutado en CT 113 (freqtrade nativo 2026.7). Orquestador `scripts/entry_study.py`, config `configs/backtest_entrystudy.json`, evidencia `results/entrystudy_B.json`.

**Resultado (PF agregado 2021-2025, todas las monedas):**
| Variant | PF | n | win% | Mejor par (PF) |
|---|---|---|---|---|
| EntryTrendADX | **0.756** | 1018 | 23.1 | SOL 1.142 |
| EntryBreakout | 0.742 | 1109 | 22.7 | SOL 1.158 |
| EntryVolConfirm | 0.731 | 1294 | 20.6 | SOL **1.283** |
| EntryTrend | 0.65 | 1581 | 19.7 | SOL 0.979 |
| EntryPullback | 0.611 | 1501 | 17.8 | SOL 1.041 |
| EntryMeanRev | 0.066 | 119 | 7.6 | LINK 0.648 |
| **EntryV9Style** | **0.0** | **5** | 0.0 | — (inertE) |

**Pares que pasan el gate (PF≥1.5, n≥30, 4+yr): NINGUNO.** Mejor celda individual: EntryVolConfirm SOL/USDT PF 1.283 (n=140, win 30%) — se queda justo por debajo de 1.5.

**Conclusiones honestas (lo importante de B):**
1. **Los filtros de entrada SÍ ayudan** vs la EMA plana: TrendADX/Breakout/VolConfirm suben el PF de 0.65 → 0.73–0.76. Pero no bastan para el gate.
2. **Techo de trend-following 2h spot ~1.3.** Incluso la mejor entrada+exit en SOL se techa en ~1.28. El bottleneck ya no es solo la entrada: es sistémico al régimen 2h spot.
3. **SOL/USDT es sistemáticamente el mejor par** en todas las entradas (PF 0.98–1.28). BTC el peor (0.49–0.54).
4. **EntryMeanRev (contrarian) es desastroso (PF 0.066)** → confirma que el régimen es trend-following, no mean-reversion. Descartar contrarian en 2h spot.
5. **El salto a PF≥1.5 no vendrá de una señal sola** → requiere **Fase D (diversificación/agregación de portfolio)**: combinar varias entradas/pares no correlacionadas para que el PF de portfolio suba por diversificación (y control de DD).

### Añadido posterior (curiosidad forense): `EntryV9Style`
- Por petición explícita del usuario (03:46 UTC), se añadió `EntryV9Style` como 7ª variant: replica el ESTILO de la señal de ENTRADA de v9 (`evaluate_long_entry` de `engine.py`) — score_bull >=2 de 3 señales (momentum + volume_support + engulfing_bull) con los umbrales reales de v9. Mismo exit de C, mismo walk-forward 2021-2025.
- **RESULTADO: casi INERTE.** Solo **5 trades en 5 años** (3 BTC, 2 ETH), en SOL/XRP/ADA/DOGE/DOT/AVAX/LINK no disparó NUNCA. PF=0.0, win 0%.
- **Conclusión de la curiosidad:** la señal de entrada de v9 replicada fielmente NO tiene edge — ni siquiera genera suficientes trades para medirla (n=5). Confirma que v9 no se quedaba en PF~1.2 solo por el perfil de riesgo 2x: **la entrada en sí es mala/inactiva** en 2h spot. El sistema completo sobrevivía por apalancamiento + gestión, no por la señal. No es candidata; queda como registro forense.

## 2026-08-22 — Fase D: Diversificación de portfolio (COMPLETADA, resultado honesto)

**Objetivo:** medir si combinar múltiples estrategias/pares NO correlacionadas levanta el PF agregado y baja el DD (el multiplicador real de la diversificación, según PROJECT.md Fase D).

**Diseño (honesto sobre el alcance):**
- PROJECT.md define Fase D como *Mean-reversion + funding carry + control de correlación*. De esas 3 patas:
  - **Mean-reversion** ya se probó en Fase B (`EntryMeanRev`, PF 0.066) → desastroso en 2h spot. Descartado.
  - **Funding carry** (perpetuos Kraken/Bybit/OKX) es la verdadera fuente de alpha estructural, pero **requiere credenciales** → diferido a staging por el propio PROJECT.md. NO se puede medir hoy.
  - **Control de correlación / combinatoria** → esto SÍ se hace ya. Es la única pata de Fase D ejecutable sin credenciales.
- Harness: `scripts/portfolio_d.py` (stdlib puro, sin freqtrade/numpy — corre en cualquier host). Entrada: `results/trades_B.json` (6622 trades crudos OOS de Fase B, extraídos de los zips canónicos 03:34, walk-forward 2021-2025, sizing fijo 100 USDT/trade). Mide PF agregado, curva de equity, max drawdown pico-a-valle, Sharpe anualizado aproximado y matriz de correlación de P&L mensual por celda (variant,pair). Tests: `tests/test_portfolio_d.py` (15 passed).

**Resultado (PF agregado OOS):**
| Escenario | PF | n | maxDD%* | Sharpe | Net P&L |
|---|---|---|---|---|---|
| all (6×9=54 celdas) | 0.685 | 6622 | 945 | -0.99 | -9478 USDT |
| top-10 celdas por PF (todas las monedas) | 1.063 | 1182 | 107 | 0.11 | +342 USDT |
| top-10 celdas por PF, solo pares 4+ años (gate-compliant, sin XRP) | 0.963 | 1431 | 167 | -0.08 | +? |
| Mejor celda aislada (ref B: EntryVolConfirm SOL) | 1.283 | 140 | — | — | — |

(*) maxDD% = caída pico-a-valle de la curva de equity **corriente** (base pequeña ~cientos de USDT, no normalizada a capital). Caveat de medida: no es DD% sobre capital gestionado; sirve solo para comparar forma de curva entre escenarios, no en valor absoluto.

**Hallazgo clave (lo importante de D):** el PF agregado del portfolio (**1.063** top-10 todas las monedas; **0.963** gate-compliant sin XRP) es **INFERIOR** a la mejor celda aislada (1.283). La matriz de correlación explica por qué:
- Intra-par, las variantes trend están **0.95–0.99** correlacionadas (misma señal con filtros distintos).
- SOL ↔ XRP (distinto par) ~0.2–0.3; el resto del universo correlaciona 0.58–0.80 (Fase A.1).
- Conclusión: combinar trend correlacionado **NO** aporta diversificación real — solo diluye el PF de la mejor celda con las demás (todas <1.28). El régimen 2h spot es uno solo; no hay señales independientes que sumar.

**Veredicto de Fase D:** el gate **PF ≥ 1.5 NO se alcanza** con spot trend 2h solo, por mucho que se agregue. El lever real es el **funding carry** (alpha estructural de perpetuos, casi market-neutral), que está **diferido a staging** (requiere credenciales, PROJECT.md §4). La pata de combinatoria/correlación de Fase D queda hecha y documentada; su conclusión es que **no basta**.

**Siguiente:** Fase E (sizing/Kelly, maker-only) es irrelevante hasta tener edge OOS ≥1.5, y Fase F (reevaluar) dice: si ~1.3 → aceptar o archivar. Con spot trend ~1.0–1.3 agregado, la decisión honesta es **archivar el track spot trend** y abrir el track carry en staging. Se documenta en decision_log + STATUS; se pide OK de Héctor antes de cualquier credencial/staging (guardarraíles PROJECT.md: sin $ real sin gate, sin acciones en vivo sin OK).

**Evidencia:** `results/portfolio_D.json` (consolidado), `results/portfolio_D_all.json` y `results/portfolio_D_top10.json` (matrices de correlación completas), `results/trades_B.json` (trade-level OOS).

## 2026-08-22 — Fase D (carry) — Backtest en SECO de funding carry (COMPLETADO, sin credenciales)

**Autorizado por Héctor (04:36) en modo paper: sin cuenta, sin $ real, solo datos públicos.**

**Método:** `scripts/carry_backtest.py` (stdlib puro). Descarga fundingRate histórico 8h de **Binance USDT-M perp vía API pública** (sin API key) para 9 pares, 2021-01→2025-12 (49.377 eventos). Simula hold continuo **long spot + short perp 1:1** (cashflow SHORT = +rate·notional: cobra funding positivo). Fee round-trip = 4 láminas (taker 0.1% / maker 0.02%). PF = sum(cashflows +)/sum(|cashflows −|). Compara correlación mensual vs trend de Fase B y desglosa por año.

**Resultado (PF de la corriente de funding, agregado 9 pares):**
| Régimen fee | PF agregado | Net P&L (notional=1) | Mejor par (PF) | Peor par |
|---|---|---|---|---|
| Taker 0.1% | **3.447** | +4.5581 | LINKUSDT 17.70 / BTCUSDT 18.22 | BNBUSDT 0.90 (neto −0.05) |
| Maker 0.02% | 3.447 | +4.5581 | — | — |
- % de eventos con funding positivo: **80.7%** (39.867) vs 19.3% negativos (9.510). Rate medio 0.0092%/8h.
- **Por año (TAKER):** 2021 PF 9.16 (neto +3.19) · 2022 PF **0.51 (neto −0.42)** · 2023 PF 2.96 (+0.52) · 2024 PF 8.11 (+1.01) · 2025 PF 2.29 (+0.25). **El carry cae por debajo de 1 solo en 2022 (año bajista)**.
- **Correlación con el trend de Fase B: POSITIVA (+0.43 a +0.55)**, NO negativa. El carry NO diversifica el riesgo de régimen: es otra apuesta a que el mercado siga alcista. En 2022 (bajista) el carry pierde y el trend también.

**Veredicto honesto de Fase D (carry):**
1. **SÍ rompe el techo PF≥1.5** — PF agregado 3.4, muy por encima del 1.5 del gate. El carry es el lever real que el spot trend (~1.0–1.3) no podía dar.
2. **PERO NO es diversificación de riesgo** — correlación positiva con el trend. Sumar carry al portfolio sube el PF pero **concentra** la exposición al régimen alcista. No reparte el riesgo; lo amplifica en una dirección.
3. **Dependencia de régimen:** en años bajistas (2022) el carry es neto negativo (PF 0.51). No es un edge direccional-neutral real; es una apuesta estructural a que el funding siga positivo (lo cual ocurre ~80% del tiempo en crypto, pero no siempre).
4. **Datos honestos sobre venue:** usé Binance perp funding (público) vs Coinbase spot de Fase B. No es el mismo exchange ni el mismo producto; el punto era comparar corrientes de retorno, no replicar venue. Para staging real habrá que usar un venue consistente (Kraken/Bybit/OKX según PROJECT.md) y validar funding + ejecución allí.
5. **Riesgos NO modelados en seco** (de la charla previa con Héctor): liquidación de la short perp si el precio sube sin margen, basis risk, funding negativo prolongado, riesgo de exchange (contraparte/hackeo/delisting). El backtest asume cobertura perfecta 1:1 y sin coste de mantener spot — en vivo hay slippage, préstamo de spot y gap de base.

**Conclusión de Fase D completa:** el edge PF≥1.5 EXISTE vía carry (en papel, 2021-2025). El proyecto NO está agotado; la vía real es carry, no spot trend. Pero el carry es riesgo de régimen concentrado, no diversificación mágica. **Siguiente paso (Fase E/F + staging):** solo tras OK explícito de Héctor y con credenciales de un venue top-tier, abrir staging con $50–100, validar funding + ejecución real, y medir PF neto con todos los costes. Sin OK y sin credenciales: NADA en vivo.

**Evidencia:** `scripts/carry_backtest.py`, `tests/test_carry_backtest.py` (9 tests, incl. regresión del bug de signo), `results/carry_D_taker.json` + `results/carry_D_maker.json` (desglose por par/año/correlación), `results/funding_raw.json` (datos crudos, 1.3 MB, NO versionado — regenerable).

