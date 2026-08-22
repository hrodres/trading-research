# Decision Log — trading-research

Registro cronológico de decisiones y resultados. **Los números vivos están en
`results/*.json`**; aquí solo veredicto cualitativo y enlace.

## 2026-08-22 — Setup
- Proyecto nuevo para buscar edge sistemático (PF ≥ 1.5 OOS) con freqtrade como harness.
- Datos públicos Coinbase spot 2h, 9 pares candidatos, sin credenciales.
- Repo GitHub público.

## Fase A.1 — Screening
- Correlación log-returns 0.58–0.80; 0 pares con corr ≥0.80 (margen para diversificar). Liquidez BTC $1.68M → DOT $8.5K/2h. XRP arranca 2023-07 (fuera del gate 4+ años).

## Fase A.2 / A.3 — Baseline + Walk-forward OOS
- Baseline valida el harness OOS (no busca edge). A.3 walk-forward 2021–2025, sizing 100 USDT, sin fitting → **0 pares pasan gate** (PF 0.276–0.395). `results/walkforward_A3.json`.

## Fase C — Exits
- 4 variants (mismo exit ganador). El TP fijo corto era el asesino nº1; "let winners run" sube PF ~2x vs baseline. **0 variants/par pasan gate** (mejor PF 0.65; mejor celda SOL 0.98). Bottleneck = entrada. `results/exitstudy_C.json`.

## Fase B — Entradas
- 6 variants. **0 variants/par pasan gate**. Mejor celda: EntryVolConfirm SOL/USDT PF **1.283** (techo trend 2h ~1.3). MeanRev (contrarian) PF 0.066 → régimen trend-following. `results/entrystudy_B.json`.

## Fase D — Diversificación
### D.1 Combinatoria
- Agrega 6622 trades OOS de B. PF agregado top-10 = **1.063** / **0.963** (gate sin XRP) — INFERIOR a la mejor celda (1.283). Correlación intra-par 0.95–0.99 → no diversifica. **Gate NO alcanzado con spot trend 2h solo.** `results/portfolio_D.json`.
### D.2 Carry en SECO
- Funding público Binance USDT-M perp 2021–2025 (49.377 eventos). Long spot + short perp 1:1 → PF agregado **3.447** (rompe gate). PERO correlación vs trend +0.43/+0.55 (concentra riesgo de régimen); 2022 cae a PF 0.51. Staging pendiente (credenciales + OK). `results/carry_D.json`.

## Estado final
- A✅ B✅ C✅ D(combinatoria+carry seco)✅. Carry staging ⬜ · E ⬜ · F ⬜.
- Ninguna señal direccional alcanza PF≥1.5 (techo ~1.3). El carry lo rompe en backtest pero es mecanismo de funding, no señal direccional, y no está validado en vivo. Repo en "punto honesto", documentación consolidada.
