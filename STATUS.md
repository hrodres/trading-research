# STATUS — checklist de fases (trading-research)

> Checklist canónico del proyecto. GitHub = fuente de verdad.
> Estados: ✅ done · 🔄 in-progress · ⬜ pending

## Infra (base)
- ✅ **freqtrade NATIVO** en CT 113 (`freqtrade-native`, Debian 13, 192.168.1.58, 4c/4GB/8GB `local-lvm`), venv `/opt/ft` (freqtrade 2026.7). Datos en `/opt/freqtrade/user_data/`. Ver `SETUP.md`.
- ✅ 9 pares candidatos Coinbase 2h (2020→2026) descargados: BTC/ETH/SOL/XRP/ADA/DOGE/DOT/AVAX/LINK.
- ✅ Repo GitHub público `hrodres/trading-research` con PROJECT.md, README.md, decision_log.md, LICENSE, .gitignore.
- ✅ Estructura de repo (`scripts/`, `strategies/`, `tests/`).
- ✅ `STATUS.md` (checklist de fases) en GitHub.
- ✅ `requirements.txt` (entorno reproducible para scripts/).
- ✅ `CHANGELOG.md`.
- ✅ `strategies/baseline_trend.py` + `configs/backtest_baseline.json` (Fase A.2).
- ✅ `SETUP.md`: freqtrade **nativo** en CT 113 (Debian 13, sin Docker). Instalación reproducible + cómo correr backtests. Docker `freqtrade` de CT 112 deshabilitado (restart=no).
- ⬜ CI (`.github/workflows/ci.yml`): **NO añadido** — el PAT no tiene scope `workflow`. Los gates (py_compile/pytest/scan) se corren en local antes de cada push.

## Fase A — Cimientos de medida (obligatoria)
- ✅ **A.1 — Screening de pares** (correlación por fecha + liquidez USDT). Ejecutado 2026-08-22. Resultados en `decision_log.md`. Corr 0.58–0.80, BTC↔ETH 0.80, 0 redundantes. Caveats: XRP fuera del gate 4+ años; liquidez fina en DOT/LINK/AVAX/ADA.
- ✅ **A.2 — Estrategia baseline** (`strategies/baseline_trend.py` + `configs/backtest_baseline.json`). Backtest corre = harness OOS validado. Resultado honesto: PF negativo (baseline de referencia, no edge). Detalles en `decision_log.md`.
- ✅ **A.3 — Walk-forward OOS por par** (2021-2025, sizing 100 USDT, sin fitting). Ejecutado 2026-08-22. Orquestador `scripts/walkforward.py` + `configs/backtest_walkforward.json`. **Resultado: 0 pares pasan el gate** (PF 0.276-0.395 en todos). La baseline NO tiene edge. Detalles en `decision_log.md` + `results/walkforward_A3.json`.
- ✅ **A.4 — Documentación** en `decision_log.md` + `STATUS.md` + push.

## Fase B — Señal de entrada
- ✅ **B — Estudio de entradas** (`strategies/entry_study.py` + `scripts/entry_study.py` + `configs/backtest_entrystudy.json`). Ejecutado 2026-08-22 en CT 113 nativo. **6 variants** de ENTRADA sobre el MISMO exit ganador de C (dejar correr EMA-cross + SL -10%), 2021-2025, sizing 100 USDT, sin fitting. **Resultado: 0 variants/par pasan el gate** (mejor PF 0.756 EntryTrendADX; mejor celda EntryVolConfirm SOL/USDT PF 1.283, n=140). Techo trend-following 2h ~1.3 → el salto a PF≥1.5 exige **Fase D (diversificación)**. SOL/USDT es sistemáticamente el mejor par; EntryMeanRev (contrarian) PF 0.066. Detalles en `decision_log.md` + `results/entrystudy_B.json`. Nota: `EntryV9Style` (estilo de entrada de v9) se probó aparte por petición del usuario y quedó aislada como anexo forense (casi inerte, 5 trades/5 años) — NO forma parte de B.

## Fase C — Salida (overhaul)
- ✅ **C — Estudio de exits** (`strategies/exit_study.py` + `scripts/exit_study.py` + `configs/backtest_exitstudy.json`). Ejecutado 2026-08-22. 4 variants sobre MISMA entrada (EMA20>EMA50), 2021-2025, sizing 100 USDT, sin fitting. **Resultado: 0 variants/par pasan el gate** (mejor PF 0.65 ExitEmaCross; mejor par SOL 0.98). Conclusión: el TP fijo corto era el asesino nº1 (arreglar solo el exit duplica PF vs baseline); el bottleneck real es la ENTRADA → Fase B. Detalles en `decision_log.md` + `results/exitstudy_C.json`.

## Fase D — Diversificación
- ⬜ **D (combinatoria/correlación) — EJECUTADA 2026-08-22**: harness `scripts/portfolio_d.py` + `tests/test_portfolio_d.py` (15 passed) + `results/trades_B.json` (6622 trades OOS de Fase B). PF agregado top-10 = **1.063** (todas las monedas) / **0.963** (gate-compliant sin XRP) — **INFERIOR a la mejor celda aislada (1.283)**. Correlación intra-par trend 0.95–0.99 → combinar trend correlacionado NO aporta diversificación. **GATE NO ALCANZADO: PF≥1.5 imposible con spot trend 2h solo.**
- ⬜ **Funding carry** (perpetuos Kraken/Bybit/OKX, **requiere credenciales**) — **DIFERIDO a staging** (PROJECT.md §4). Es la única pata de D que puede romper el techo PF≥1.5 (alpha estructural casi market-neutral). No ejecutable hoy sin OK + credenciales.
- ⬜ **Mean-reversion** — descartada (EntryMeanRev Fase B PF 0.066, desastrosa en 2h spot).

## Fase E — Sizing y ejecución
- ⬜ Kelly fraccionado, maker-only, cap de riesgo por régimen.

## Fase F — Reevaluar
- ⬜ Si OOS ≥ 1.5 → staging real ($50-100). Si ~1.3 → aceptar o archivar.

---
*Última actualización: 2026-08-22 (Fase B completada; techo trend-following 2h ~1.3, camino a Fase D).*
