# trading-research

![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Status](https://img.shields.io/badge/status-research-yellow)
![Exchange](https://img.shields.io/badge/exchange-Coinbase-blue)
![Engine](https://img.shields.io/badge/engine-freqtrade-orange)

Búsqueda de **edge experto/pro** en crypto (Profit Factor ≥ 1.5 sostenido out-of-sample).

Proyecto de I&D de trading cuantitativo en crypto: usa **freqtrade** como andamiaje (backtest OOS, hyperopt) y construye la capa de valor propia — señales (edge), orquestador adaptativo y aprendizaje por acción/omisión.

## Estado
- Infra: **freqtrade NATIVO** en CT 113 (`freqtrade-native`, Debian 13, Proxmox 192.168.1.222) — ver `SETUP.md`.
- Datos: 9 pares candidatos Coinbase 2h (2020→2026), **sin credenciales**.
- Edge actual: frontera (~PF 1.2). Objetivo: ≥ 1.5.

## Cómo funciona
1. **Fase A** — Medir bien (walk-forward OOS, fees + slippage).
2. **Fase B-D** — Señal de entrada, salida, y diversificación (trend + mean-reversion + funding carry).
3. **Fase F** — Reevaluar. Solo si OOS ≥ 1.5 → staging real (mínimo).

## Documentación
- `PROJECT.md` — propósito, criterios de éxito, guardarraíles, fases.
- `STATUS.md` — **checklist de fases** (qué está done / in-progress / pending).
- `decision_log.md` — decisiones y su justificación (auditable).
- `CHANGELOG.md` — registro de cambios del repositorio.

## Estructura del repo
```
trading-research/
├── scripts/
│   ├── screening.py          # Fase A.1: correlación + liquidez por par (Coinbase 2h)
│   ├── walkforward.py         # Fase A.3: walk-forward OOS por par (freqtrade harness)
│   ├── exit_study.py          # Fase C: estudio de exits (4 variants, --strategy-list)
│   ├── entry_study.py         # Fase B: estudio de entradas (7 variants, --strategy-list)
│   └── inspect_export.py      # util: inspecciona estructura del export de freqtrade 2026.7
├── strategies/
│   ├── baseline_trend.py     # Fase A.2: estrategia baseline tendencia/momentum
│   ├── exit_study.py         # Fase C: 4 variants de exit (misma entrada)
│   └── entry_study.py        # Fase B: 6 variants de entrada (mismo exit)
├── configs/
│   ├── backtest_baseline.json    # config backtest A.2
│   ├── backtest_walkforward.json # config walk-forward A.3 (sizing 100 USDT)
│   ├── backtest_exitstudy.json   # config Fase C (exit study)
│   └── backtest_entrystudy.json  # config Fase B (entry study)
├── results/
│   ├── walkforward_A3.json   # resultado A.3 (PF por par 2021-2025)
│   ├── exitstudy_C.json      # resultado C (PF por variant/par 2021-2025)
│   └── entrystudy_B.json     # resultado B (PF por variant/par 2021-2025)
├── tests/
│   └── test_repo_integrity.py  # CI local: estructura, compilación, sin secretos
├── PROJECT.md                # propósito, fases, guardarraíles
├── STATUS.md                 # checklist de fases (done / in-progress / pending)
├── SETUP.md                  # instalación freqtrade NATIVO (CT 113, sin Docker) + cómo correr backtests
├── decision_log.md           # log auditable de decisiones
├── CHANGELOG.md              # registro de cambios del repositorio
├── requirements.txt          # freqtrade==2026.7 + pyarrow + pandas/numpy/pytest
├── .gitignore                # excluye secrets, datos y estado runtime
├── LICENSE                   # MIT
└── README.md
```
> **Datos NO versionados:** los klines Coinbase 2h viven en `/opt/freqtrade/user_data/data/coinbase/` dentro de **CT 113** (freqtrade nativo, sin Docker), no en el repo (ver `.gitignore` y `SETUP.md`).

## Principios
- Sin apalancamiento para inflar el PF.
- Sin overfit (OOS obligatorio).
- Sin dinero real hasta el gate de staging.
- **GitHub es la fuente de verdad** (canónica). Las copias en local/contenedores son artefactos de despliegue; si discrepan, manda GitHub. Verificar contra la API tras cada push.
- **Estructura disciplinada:** `scripts/` (análisis), `strategies/` (freqtrade), `tests/` (unitarios). Al mover/cambiar código, actualizar `PROJECT.md` + `README.md`.

> Repo público. Datos de mercado públicos, sin credenciales.
