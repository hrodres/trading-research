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

## Fase B.2 — Pool del selector (long-candidates)
- ✅ 4 candidatas long sobre 9 pares Coinbase 2h, 5 ventanas 2021–2025/26 (20 backtests, fees 1.2% worst-case): `AtrSlLong`, `PartialtpLong`, `RotationLong`, `VolBreakoutLong`.
- ✅ **Ninguna pasa gate PF≥1.5 OOS**. Mejor `VolBreakoutLong`: mediana PF 1.45 (2021: 2.36, 2023: 1.53, 2024: 1.45; 2022: 0.46, 2025-26: 0.60 → 3/5 ventanas PF>1). `RotationLong` mediana 1.01; `AtrSlLong` y `PartialtpLong` 0/5 ventanas.
- ⚠️ **Patrón de régimen**: TODAS pierden en 2022 y 2025-26 (bear/range) y ganan en 2021/2023/2024 (bull). Edge = régimen alcista, no alpha independiente. Confirmado: 0 candidatas avanzan.
- ✅ `results/longcandidates_summary.csv` + `scripts/analyze_longcandidates.py`.

## Fase B.3 — Filtro de régimen global (selector, componente 1)
- ✅ Regla **declarada a priori** (sin selection bias): bull regime ⇔ `close BTC/USDT 2h > SMA200` (200 velas ≈ 16.7 días). Decisión en `t` usa SOLO la última vela cerrada antes del open del trade (bisect, sin lookahead); régimen indefinido (inicio de serie) = no operar.
- ✅ Aplicado a los 20 trades de B.2 (`scripts/regime_filter.py`, klines BTC regenerable desde CT 113 → `results/btc_2h.csv` git-ignored).
- 📈 **Mejora el PF AGREGADO de las 4** (AtrSl 0.555→0.667, Partialtp 0.622→0.720, Rotation 0.711→0.842, VolBreakout 1.112→**1.304**; VolBreakout mediana PF 1.45→1.60, 3/5 ventanas PF≥1.5).
- ❌ **Ninguna cruza gate PF≥1.5 OOS** con el filtro. Techo del long con filtro global sigue ~1.3 (VolBreakout 2022: 0.54, 2025-26: 0.77).
- ⚠️ Lectura: el meta-filtro de régimen es un componente VÁLIDO del selector (recorta pérdidas en bear en todas), pero insuficiente en solitario: confirma edge de régimen, captura parte, no todo.
- ✅ Evidencia: `results/regime_filter_summary.csv`.

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
*Última actualización: 2026-08-22 — Fases A/B/C/B.2/B.3/D ejecutadas. Sin señal direccional que alcance PF≥1.5 (techo ~1.3, incluso con filtro de régimen global: mejor PF agregado 1.304 VolBreakoutLong); el carry lo rompe en seco (3.447) pero no está validado en vivo.*
