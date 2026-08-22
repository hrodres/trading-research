# CHANGELOG — trading-research

Registro de cambios del repositorio (criterio PROJECT.md §8.2: memoria auditable de qué funcionó).

---

## 2026-08-22
- **Setup inicial**: repo público, `PROJECT.md`, `README.md`, `decision_log.md`, `LICENSE` (MIT), `.gitignore`.
- **Fase A.1 (screening)**: `scripts/screening.py` corregido (alineación por fecha + liquidez USDT). Correlaciones 0.58–0.80, BTC↔ETH 0.80, 0 redundantes.
- **Estructura repo**: `scripts/` + `strategies/` + `tests/`.
- **Gobernanza**: principio "GitHub = fuente de verdad" en `PROJECT.md` + `README.md`.
- **Checklist de fases**: `STATUS.md`.
- **Buenas prácticas**: `requirements.txt`, `CHANGELOG.md`, `tests/test_repo_integrity.py` (5 tests OK).
- **README fiel a la realidad**: corregida la sección de estructura (sin `data/` ficticia; refleja STATUS/CHANGELOG/requirements/tests).
- **FIX push bug**: se eliminó la necesidad de escribir el token en la URL. Configurado `credential.helper=store` (token en `/root/.git-creds-trading-research`, fuera del repo, permisos 600). `git push` ahora autentica solo; el remote queda limpio y el placeholder `***` desaparece. Verificado con `git ls-remote` (exit 0).
- **Fase A.2**: `strategies/baseline_trend.py` + `configs/backtest_baseline.json`. Backtest valida el harness OOS. Baseline = línea base (PF negativo), no edge.
- **Fase A.3**: `scripts/walkforward.py` (orquestador) + `configs/backtest_walkforward.json` + `results/walkforward_A3.json`. Walk-forward 2021-2025, sizing 100 USDT, sin fitting. **0 pares pasan el gate PF≥1.5** (PF 0.276-0.395). Baseline rechazada; fases B/C/D deben buscar el edge.
- **Buenas prácticas**: `requirements.txt`, este `CHANGELOG.md`, CI (`.github/workflows/ci.yml`), `tests/test_repo_integrity.py`.
- **Fase C (estudio de exits)**: `strategies/exit_study.py` (4 variants, misma entrada) + `scripts/exit_study.py` (orquestador `--strategy-list`) + `configs/backtest_exitstudy.json` + `results/exitstudy_C.json`. Walk-forward 2021-2025, sizing 100 USDT, sin fitting. **0 variants/par pasan el gate** (mejor PF 0.65 ExitEmaCross; mejor par SOL 0.98). Conclusión: el TP fijo corto era el asesino nº1 (arreglar solo el exit duplica PF vs baseline); bottleneck real = entrada → Fase B. Ref docs oficiales freqtrade (trailing asimétrico).
- **Fase B (estudio de entradas)**: `strategies/entry_study.py` (6 variants de entrada: Trend, TrendADX, Breakout, Pullback, VolConfirm, MeanRev; mismo exit de C) + `scripts/entry_study.py` (orquestador `--strategy-list`) + `configs/backtest_entrystudy.json` + `results/entrystudy_B.json`. Walk-forward 2021-2025, sizing 100 USDT, sin fitting. **0 variants/par pasan el gate**. Mejor por variant: EntryTrendADX PF 0.756; mejor celda: EntryVolConfirm SOL/USDT PF 1.283 (n=140). Conclusión: techo trend-following 2h ~1.3; el salto a PF≥1.5 exige Fase D (diversificación). EntryMeanRev (contrarian) PF 0.066 → régimen trend-following confirmado.
- **Infra: freqtrade NATIVO (sin Docker)** — `SETUP.md`. Nuevo CT 113 (`freqtrade-native`, Debian 13, 192.168.1.58, 8 GB en local-lvm) con venv `/opt/ft` (freqtrade 2026.7). Migrados los 9 klines de CT 112. Docker `freqtrade` de CT 112 fijado a `restart=no` (no auto-arranca; NO eliminado sin aprobación explícita del usuario). `requirements.txt` actualizado a `freqtrade==2026.7`.
- **Corrección de doc**: README/PROJECT/STATUS ya no describen la infra como "contenedor Docker freqtrade en CT 112" (es referencia obsoleta). Infra activa = **freqtrade nativo en CT 113** (ver `SETUP.md`). `decision_log.md`/`SETUP.md` conservan las menciones a Docker como registro histórico/legacy.
