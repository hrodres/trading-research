# Decision Log — trading-research

Registro cronológico de decisiones y resultados. **Los números vivos están en
`results/*.json`**; aquí solo veredicto cualitativo y enlace.

## 2026-08-22 — Setup
- Proyecto nuevo para buscar edge sistemático (PF ≥ 1.5 OOS) con freqtrade como harness.
- Datos públicos Coinbase spot 2h, 9 pares candidatos, sin credenciales.
- Repo GitHub público.

## Cambio de alcance (2026-08-22) — El proyecto ES un sistema de señales
- CRÍTICA del usuario: el objetivo NO es "encontrar 1 estrategia long con PF≥1.5 OOS". Es un **meta-controlador** que decide la mejor estrategia en cada momento (regime/online selection).
- Sesgo señalado: backtestear N candidatas y quedarse con la de mayor PF = **selection bias / look-ahead**. Fix: selector con **walk-forward estricto** — la decisión en `t` usa solo datos `≤ t`; el PF se mide en datos `> t`.
- Las 4 candidatas long (rotation/volbreakout/atr_sl/partialtp) = **pool del selector**, no el producto final.
- Aclaración del usuario (06:00): freqtrade sigue siendo el harness (decisión de inicio, vigente); la crítica NO va contra freqtrade/backtesting, sino contra CÓMO se valida la selección.
- Criterio de éxito real: **el selector logra PF≥1.5 OOS con selección walk-forward honesta**. Rama: `feat/long-candidates`.

## Fase A.1 — Screening
- Correlación log-returns 0.58–0.80; 0 pares con corr ≥0.80 (margen para diversificar). Liquidez BTC $1.68M → DOT $8.5K/2h. XRP arranca 2023-07 (fuera del gate 4+ años).

## Fase A.2 / A.3 — Baseline + Walk-forward OOS
- Baseline valida el harness OOS (no busca edge). A.3 walk-forward 2021–2025, sizing 100 USDT, sin fitting → **0 pares pasan gate** (PF 0.276–0.395). `results/walkforward_A3.json`.

## Fase C — Exits
- 4 variants (mismo exit ganador). El TP fijo corto era el asesino nº1; "let winners run" sube PF ~2x vs baseline. **0 variants/par pasan gate** (mejor PF 0.65; mejor celda SOL 0.98). Bottleneck = entrada. `results/exitstudy_C.json`.

## Fase B — Entradas
- 6 variants. **0 variants/par pasan gate**. Mejor celda: EntryVolConfirm SOL/USDT PF **1.283** (techo trend 2h ~1.3). MeanRev (contrarian) PF 0.066 → régimen trend-following. `results/entrystudy_B.json`.

## Fase B.2 — Pool del selector (long-candidates)
- 4 candidatas long (`AtrSlLong`, `PartialtpLong`, `RotationLong`, `VolBreakoutLong`) sobre 9 pares Coinbase 2h, 5 ventanas 2021–2026, fees 1.2% worst-case. **Ninguna pasa gate PF≥1.5**.
- Mejor: `VolBreakoutLong` (PF mediana 1.45; 2021: 2.36, 2023: 1.53, 2024: 1.45; 2022: 0.46, 2025-26: 0.60). `RotationLong` mediana 1.01; `AtrSlLong` y `PartialtpLong` 0/5 ventanas rentables.
- **Patrón de régimen**: todas ganan en bull (2021/2023/2024) y pierden en bear/range (2022/2025-26) → edge de régimen, no alpha independiente. Confirmado: 0 candidatas avanzan. `results/longcandidates_summary.csv`.

## Fase B.3 — Filtro de régimen (selector, componente 1; global + per-par)
- Regla A PRIORI (antes de ver resultados): bull regime ⇔ close 2h > SMA200; decisión en `t` solo con velas cerradas ≤ `t` (sin lookahead); régimen no definido (inicio serie) = no operar.
- Proxies comparados: **GLOBAL** (BTC/USDT) y **PER-PAR** (el propio par). Ambos mejoran el PF agregado de las 4 vs sin filtro (VolBreakout: 1.112 → 1.304 global / 1.229 per-par; Rotation: 0.711 → 0.842 / 0.876; Partialtp: 0.622 → 0.720 / 0.754; AtrSl: 0.555 → 0.667 / 0.695).
- **Ninguna variante alcanza gate PF≥1.5 OOS** (mejor agregado VolBreakout 1.304 global; mediana PF_perpar 1.61, 3/5 ventanas ≥1.5 pero 2022 y 2025-26 siguen perdiendo). El componente régimen añade valor pero no basta: techo del long con filtro ~1.3. `results/regime_filter_summary.csv`.
- **Siguiente paso lógico pendiente**: combinar régimen (componente 1) + carry (único mecanismo PF 3.4 en seco), u orientar el selector a selección walk-forward de estrategia por ventana.

## Fase D — Diversificación
### D.1 Combinatoria
- Agrega 6622 trades OOS de B. PF agregado top-10 = **1.063** / **0.963** (gate sin XRP) — INFERIOR a la mejor celda (1.283). Correlación intra-par 0.95–0.99 → no diversifica. **Gate NO alcanzado con spot trend 2h solo.** `results/portfolio_D.json`.
### D.2 Carry en SECO
- Funding público Binance USDT-M perp 2021–2025 (49.377 eventos). Long spot + short perp 1:1 → PF agregado **3.447** (rompe gate). PERO correlación vs trend +0.43/+0.55 (concentra riesgo de régimen); 2022 cae a PF 0.51. Staging pendiente (credenciales + OK). `results/carry_D.json`.

## Estado final
- A✅ B✅ B.2✅ B.3✅ C✅ D(combinatoria+carry seco)✅. Carry staging ⬜ · E ⬜ · F ⬜.
- Ninguna señal direccional alcanza PF≥1.5 (techo ~1.3, incluso con filtro de régimen global: VolBreakoutLong PF agregado 1.304). El carry lo rompe en backtest (PF 3.447) pero es mecanismo de funding, no señal direccional, y no está validado en vivo. Repo en "punto honesto", documentación consolidada.

## 10:17 — D.2: carry + filtro de régimen (componente selector aplicado al carry)
- Hipótesis: el carry cae a PF 0.51 en 2022 porque en bear el funding se vuelve negativo. Aplicar el interruptor de régimen (close BTC 2h > SMA200 / close propio par > SMA200, sin lookahead) debería recortar esas pérdidas.
- Resultado (mismo modelo que carry_D.json, fees taker 0.001): PF agregado ALL 3.447 → **GLOBAL 7.551 / PERPAR 6.879**; GL agregado cae de 1.863 a 0.341/0.298 (se cortan las pérdidas del bear). Por año, TODAS las ventanas ≥ 3.08: 2022 pasa de 0.51 → 3.18/3.09.
- Coste: net baja (4.52 → 2.20/1.72) porque solo se opera en bull (~47% de eventos, el resto apagado). Trade-off calidad vs cantidad: a favor de calidad si el objetivo es PF (gate).
- **Primera señal del proyecto que pasa el gate PF≥1.5 OOS en TODAS las ventanas.** Evidence: `results/carry_regime_summary.csv`. Lectura: el selector (régimen) ya tiene 1 mecanismo con edge validado; falta staging (credenciales) para ejecución real.

## 10:37 — Selector v1: primer meta-controlador walk-forward (visión hecha código)
- Diseño A PRIORI: pool de 4 longs B.2 + régimen (SMA200 2h BTC, sin lookahead) + selección WF 1-lookback (estrategia de mejor PF bull en ventana anterior; primera ventana = ensemble del pool) + carry en bull. Métrica: PF del PROCESO.
- Resultado: **el selector LONG (régimen+WF) sube PF de 0.669 (pool crudo) a 1.172** — seleccionar añade valor real (2023: 1.684, 2024: 1.596); WF eligió VolBreakoutLong en todas las ventanas tras la primera.
- **Proceso completo PF 1.245 (2/5 ventanas ≥1.5)** — el long direccional lastra en 2022 (0.584) y 2025 (0.825); el carry solo pasa el gate en todas (7.55). Dato de diseño: al sumar long(%) + carry(rate) en una sola métrica hay caveat de escala (documentado en el script).
- Lectura: el meta-controlador funciona como CEREBRO (la selección mejora al pool), pero con el pool actual de longs no basta; la vía validada y fuerte es el carry. Siguientes opciones: (a) staging del carry (credenciales, cuenta pequeña), (b) reducir el peso/presencia del long en el proceso, (c) validar el short para dar al selector un brazo bajista.
