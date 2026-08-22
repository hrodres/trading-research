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

## Fase B.3 — Filtro de régimen global (selector, componente 1)
- Regla A PRIORI (antes de ver resultados): bull regime ⇔ close BTC/USDT 2h > SMA200; decisión en `t` solo con velas cerradas ≤ `t` (sin lookahead); régimen no definido (inicio serie) = no operar.
- Aplicado a los trades de B.2: **mejora el PF agregado de las 4** (AtrSl 0.555→0.667, Partialtp 0.622→0.720, Rotation 0.711→0.842, VolBreakout 1.112→1.304); VolBreakout mediana PF 1.45→1.60 con 3/5 ventanas ≥1.5.
- **Ninguna alcanza gate PF≥1.5 OOS con el filtro.** El meta-filtro de régimen añade valor (recorta las pérdidas de bear) pero no basta: el techo del long con filtro global sigue ~1.3. `results/regime_filter_summary.csv`.
- **Siguiente decisión pendiente**: régimen más fino (por par, no solo BTC global) u orientar el selector a combinar régimen + carry (único mecanismo PF 3.4 en seco).

## Fase D — Diversificación
### D.1 Combinatoria
- Agrega 6622 trades OOS de B. PF agregado top-10 = **1.063** / **0.963** (gate sin XRP) — INFERIOR a la mejor celda (1.283). Correlación intra-par 0.95–0.99 → no diversifica. **Gate NO alcanzado con spot trend 2h solo.** `results/portfolio_D.json`.
### D.2 Carry en SECO
- Funding público Binance USDT-M perp 2021–2025 (49.377 eventos). Long spot + short perp 1:1 → PF agregado **3.447** (rompe gate). PERO correlación vs trend +0.43/+0.55 (concentra riesgo de régimen); 2022 cae a PF 0.51. Staging pendiente (credenciales + OK). `results/carry_D.json`.

## Estado final
- A✅ B✅ B.2✅ B.3✅ C✅ D(combinatoria+carry seco)✅. Carry staging ⬜ · E ⬜ · F ⬜.
- Ninguna señal direccional alcanza PF≥1.5 (techo ~1.3, incluso con filtro de régimen global: VolBreakoutLong PF agregado 1.304). El carry lo rompe en backtest (PF 3.447) pero es mecanismo de funding, no señal direccional, y no está validado en vivo. Repo en "punto honesto", documentación consolidada.
