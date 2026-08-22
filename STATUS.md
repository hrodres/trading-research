# STATUS — checklist de fases (trading-research)

> Checklist canónico del proyecto. GitHub = fuente de verdad.
> ✅ done · 🔄 in-progress · ⬜ pending

## Infra (base)
- ✅ **freqtrade nativo** (venv, freqtrade 2026.7). Datos en `user_data/data/coinbase/`. Ver `SETUP.md`.
- ✅ 9 pares candidatos Coinbase 2h (2020→2026): BTC/ETH/SOL/XRP/ADA/DOGE/DOT/AVAX/LINK.
- ✅ Repo GitHub público con PROJECT.md, README.md, STATUS.md, decision_log.md, SETUP.md, LICENSE, .gitignore.
- ✅ Estructura `scripts/`, `strategies/`, `tests/`, `configs/`, `results/`.
- ✅ `requirements.txt` (entorno reproducible).
- ⬜ CI `.github/workflows/ci.yml`: no añadido (PAT sin scope `workflow`). Gates corren en local.

## Fase A — Cimientos de medida
- ✅ **A.1** Screening (correlación por fecha + liquidez). Corr 0.58–0.80, 0 redundantes. XRP fuera del gate 4+ años.
- ✅ **A.2** Baseline tendencia (harness OOS validado; PF negativo, no edge).
- ✅ **A.3** Walk-forward OOS 2021–2025: **0 pares pasan gate** (PF 0.276–0.395). Detalle en `results/walkforward_A3.json`.

## Fase B — Señal de entrada
- ✅ **B** 6 variants sobre el exit ganador de C, 2021–2025. **0 variants/par pasan gate** (mejor PF 0.756 EntryTrendADX; mejor celda EntryVolConfirm SOL/USDT PF 1.283). Techo trend 2h ~1.3. `results/entrystudy_B.json`.

## Fase C — Salida
- ✅ **C** 4 variants sobre misma entrada. **0 variants/par pasan gate** (mejor PF 0.65 ExitEmaCross; mejor par SOL 0.98). El TP fijo corto era el asesino nº1. `results/exitstudy_C.json`.

## Fase D — Diversificación
- ✅ **D combinatoria**: PF agregado top-10 = **1.063** (todas las monedas) / **0.963** (gate-compliant sin XRP) — INFERIOR a la mejor celda (1.283). Correlación intra-par 0.95–0.99 → no diversifica. `results/portfolio_D.json`.
- ✅ **D carry (en SECO, sin credenciales)**: funding carry long spot + short perp 1:1, Binance perp 2021–2025 → PF agregado **3.447** (rompe gate). Pero correlación vs trend +0.43/+0.55 (NO diversifica; concentra riesgo de régimen). 2022 cae a PF 0.51. `results/carry_D.json`.
- ⬜ **Carry en staging** (requiere credenciales + OK): pendiente.
- ⬜ **Mean-reversion**: descartada (EntryMeanRev PF 0.066).

## Fase E — Sizing/ejecución
- ⬜ Kelly fraccionado, maker-only, cap de riesgo por régimen.

## Fase F — Reevaluar
- ⬜ Si OOS ≥ 1.5 → staging. Si ~1.3 → aceptar o archivar.

---
*Última actualización: 2026-08-22 — Fases A/B/C/D ejecutadas. Sin señal direccional que alcance PF≥1.5 (techo ~1.3); el carry lo rompe en seco pero no está validado en vivo.*
