# STATUS — checklist de fases (trading-research)

> Checklist canónico del proyecto. GitHub = fuente de verdad.
> Estados: ✅ done · 🔄 in-progress · ⬜ pending

## Infra (base)
- ✅ Contenedor Docker `freqtrade` en CT 112 (`docker-apps`, Proxmox 192.168.1.222), `--cpus 2 --memory 2g`, volumen `/docker/freqtrade/user_data`.
- ✅ 9 pares candidatos Coinbase 2h (2020→2026) descargados: BTC/ETH/SOL/XRP/ADA/DOGE/DOT/AVAX/LINK.
- ✅ Repo GitHub público `hrodres/trading-research` con PROJECT.md, README.md, decision_log.md, LICENSE, .gitignore.
- ✅ Estructura de repo (`scripts/`, `strategies/`, `tests/`).
- ✅ `STATUS.md` (checklist de fases) en GitHub.
- ✅ `requirements.txt` (entorno reproducible para scripts/).
- ✅ `CHANGELOG.md`.
- ✅ `strategies/baseline_trend.py` + `configs/backtest_baseline.json` (Fase A.2).
- ⬜ CI (`.github/workflows/ci.yml`): **NO añadido** — el PAT no tiene scope `workflow`. Los gates (py_compile/pytest/scan) se corren en local antes de cada push.

## Fase A — Cimientos de medida (obligatoria)
- ✅ **A.1 — Screening de pares** (correlación por fecha + liquidez USDT). Ejecutado 2026-08-22. Resultados en `decision_log.md`. Corr 0.58–0.80, BTC↔ETH 0.80, 0 redundantes. Caveats: XRP fuera del gate 4+ años; liquidez fina en DOT/LINK/AVAX/ADA.
- ✅ **A.2 — Estrategia baseline** (`strategies/baseline_trend.py` + `configs/backtest_baseline.json`). Backtest corre = harness OOS validado. Resultado honesto: PF negativo (baseline de referencia, no edge). Detalles en `decision_log.md`.
- ⬜ **A.3 — Walk-forward OOS por par** (fees + slippage + sizing acotado 1-2%, validation fuera de muestra). Aquí se decide el universo por datos (gate PF ≥ 1.5 OOS).
- ✅ **A.4 — Documentación** en `decision_log.md` + `STATUS.md` + push.

## Fase B — Señal de entrada
- ⬜ Regime detection + señales alternativas (breakout, pullback, volumen), validar en OOS.

## Fase C — Salida (overhaul)
- ⬜ TP fijo vs trailing vs tiempo, exits escalados, validado OOS.

## Fase D — Diversificación
- ⬜ Mean-reversion + funding carry (Kraken/Bybit/OKX, con credenciales) + control de correlación.

## Fase E — Sizing y ejecución
- ⬜ Kelly fraccionado, maker-only, cap de riesgo por régimen.

## Fase F — Reevaluar
- ⬜ Si OOS ≥ 1.5 → staging real ($50-100). Si ~1.3 → aceptar o archivar.

---
*Última actualización: 2026-08-22 (Fase A.1 completada).*
