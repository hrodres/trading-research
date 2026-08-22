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

## Fase B.3 — Filtro de régimen (selector, componente 1; global + per-par)
- ✅ Regla **declarada a priori** (sin selection bias): bull regime ⇔ `close _2h > SMA200` (≈ 16.7 días). Decisión en `t` usa SOLO la última vela cerrada antes del open del trade (bisect, sin lookahead); régimen indefinido (inicio de serie) = no operar.
- ✅ Dos proxies comparados: **GLOBAL** (BTC/USDT) y **PER-PAR** (el propio par). Klines regenerables desde CT 113 (`results/btc_2h.csv`, `results/pairs_2h.csv` git-ignored).
- 📈 **GLOBAL sube el PF AGREGADO de las 4** (AtrSl 0.555→0.667, Partialtp 0.622→0.720, Rotation 0.711→0.842, VolBreakout 1.112→**1.304**; VolBreakout mediana PF 1.45→1.60, 3/5 ventanas PF≥1.5).
- 📈 **PER-PAR mejora a 3 de 4 vs GLOBAL** (AtrSl 0.695, Partialtp 0.754, Rotation 0.876) pero empeora a la mejor: VolBreakout 1.229 vs 1.304. Mediana PF_perpar VolBreakout = 1.61 (3/5 ventanas ≥1.5).
- ❌ **Ninguna variante cruza gate PF≥1.5 OOS** (mejor agregado: VolBreakout 1.304 global / 1.229 per-par). Techo del long con filtro de régimen sigue ~1.3.
- ⚠️ Lectura: el componente régimen del selector añade valor real (recorta pérdidas de bear en todas y en ambos proxies) pero es insuficiente en solitario: edge de régimen confirmado, captura parte no todo.
- ✅ Evidencia: `results/regime_filter_summary.csv` (columnas all/global/per-par).

## Fase B.4 — Pool del selector (short-candidates, brazo bear)
- ✅ 4 candidatas SHORT espejo (futures Binance perp, `can_short`, fee 0.001, 9 pares `:USDT`, 5 ventanas 2021–2025/26 = 20 backtests): `AtrSlShort`, `PartialtpShort`, `RotationShort`, `VolBreakoutShort`. Smoke VolBreakoutShort 2021 OK (87 trades, is_short=True). Commit `8c139f6`.
- ✅ **Sin filtro: patrón espejo exacto del long** — TODAS ganan en 2022 (bear): AtrSl 1.54, Partialtp 1.67, Rotation 1.70, VolBreakout 1.47; pierden en bull (2021/2023). Mediana PF ~1.0. `results/shortcandidates_summary.csv` + `scripts/analyze_longcandidates.py --extracted <short_dir> --out …` (generalizado).
- ✅ **Con filtro de régimen bear** (`regime_filter.py --direction short`, régimen bear ⇔ close<SMA200, klines perp `results/perp_klines/`, global=BTCUSDT + per-par; None=no operar): PF agregado per-par AtrSl 1.022 / Partialtp 1.166 / Rotation 1.106 / VolBreakout 0.921; global ~0.85–1.02. 2022 per-par se mantiene fuerte (1.42–1.75) pero 2025-26 no cruza (0.78–1.05). **Ninguna cruza gate PF≥1.5 OOS** (0–1/5 ventanas ≥1.5). `results/regime_filter_short_summary.csv`.
- ⚠️ Lectura: el componente régimen añade valor (bear 2022 neto positivo) pero el direccional short, como el long, tiene techo ~1.2 agregado. **El carry (7.55) sigue siendo la única vía que pasa el gate.**

## Fase D — Diversificación
- ✅ **D combinatoria**: PF agregado top-10 = **1.063** (todas las monedas) / **0.963** (gate-compliant sin XRP) — INFERIOR a la mejor celda (1.283). Correlación intra-par 0.95–0.99 → no diversifica. `results/portfolio_D.json`.
- ✅ **D carry (en SECO, sin credenciales)**: funding carry long spot + short perp 1:1, Binance perp 2021–2025 → PF agregado **3.447** (rompe gate). Pero correlación vs trend +0.43/+0.55 (NO diversifica; concentra riesgo de régimen). 2022 cae a PF 0.51. `results/carry_D.json`.
- ✅ **D.2 carry + filtro de régimen** (`scripts/carry_regime.py`): aplicar el componente 1 del selector al carry → **TODAS las ventanas ≥ PF 3.0 y PF agregado 7.55 (global) / 6.88 (per-par)**. 2022 pasa de 0.51 → 3.18. El filtro corta el problema del bear (GL de 1.86 → 0.34). net baja (2.20 vs 4.52: opera solo ~47% del tiempo, en bull) pero calidad riesgo mucho mayor. Primera señal que pasa el gate OOS en TODAS las ventanas. `results/carry_regime_summary.csv`.
- ✅ **Selector v1** (`scripts/selector_v1.py`): primer meta-controlador walk-forward (régimen + selección WF 1-lookback + carry, sin lookahead). El selector LONG (régimen+WF) sube el PF del pool de 0.669 → **1.172** (seleccionar añade valor real: 2023 1.684, 2024 1.596 en bull). Pero el PROCESO completo (long+carry, % combinado) da PF agregado **1.245** con 2/5 ventanas ≥1.5 (2022: 0.584, 2025: 0.825 lastran): el long direccional sigue siendo el lastre, el CARRY es el componente que pasa el gate solo (7.55). `results/selector_v1_summary.csv`.
- ⬜ **Carry en staging** (requiere credenciales + OK): pendiente.
- ⬜ **Mean-reversion**: descartada (EntryMeanRev PF 0.066).

## Fase E — Sizing/ejecución
- ⬜ Kelly fraccionado, maker-only, cap de riesgo por régimen.

## Fase F — Reevaluar
- ✅ **DECISIÓN FINAL (2026-08-22, Héctor): NO a productivo → proyecto ARCHIVADO.**
  - Sin staging del carry (requería credenciales + cuenta real; descartado por decisión explícita).
  - Resultado de investigación: edge direccional LONG y SHORT no alcanza el gate (techo ~1.2–1.3);
    carry + régimen lo supera en backtest seco (7.55) pero no es validable en vivo por decisión.
  - El repo queda como investigación completa y reproducible; punto de reanudación si algún día
    cambia la decisión: `scripts/carry_backtest.py` + credenciales de exchange.

---
*Última actualización: 2026-08-22 — Fases A/B/C/B.2/B.3/B.4/D + Selector v1 ejecutadas. Direccional LONG y SHORT: techo ~1.2–1.3 (no alcanzan; el short es espejo del long — gana en bear 2022, pierde en bull). **Carry + filtro de régimen: única señal que pasa PF≥1.5 OOS en TODAS las ventanas (7.55 global, mínimo 3.08)**. Selector v1: selección walk-forward añade valor (long 0.67→1.17) pero el proceso completo no llega a 1.5 (1.245, 2/5 ventanas) — el direccional (long y short) lastra; el carry es la vía validada. Pendiente: staging del carry en vivo o reforzar/gestionar el direccional.*
