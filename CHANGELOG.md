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
- **Fase B ampliada con EntryV9Style (curiosidad forense)**: añadida 7ª variant `EntryV9Style` que replica el *estilo* de entrada de v9 (score_bull ≥2 de 3 señales: momentum + volume_support + engulfing_bull). Mismo exit de C, walk-forward 2021-2025. Resultado: **casi inerte** (5 trades en 5 años, PF 0.0, win 0%) → la señal de entrada de v9 no tiene edge por sí sola. Documentado en decision_log.md. `strategies/entry_study.py` y `scripts/entry_study.py` actualizados a 7 variants.
- **Infra: freqtrade NATIVO (sin Docker)** — `SETUP.md`. Nuevo CT 113 (`freqtrade-native`, Debian 13, 192.168.1.58, 8 GB en local-lvm) con venv `/opt/ft` (freqtrade 2026.7). Migrados los 9 klines de CT 112. Docker `freqtrade` de CT 112 fijado a `restart=no` (no auto-arranca; NO eliminado sin aprobación explícita del usuario). `requirements.txt` actualizado a `freqtrade==2026.7`.
- **Corrección de doc**: README/PROJECT/STATUS ya no describen la infra como "contenedor Docker freqtrade en CT 112" (es referencia obsoleta). Infra activa = **freqtrade nativo en CT 113** (ver `SETUP.md`). `decision_log.md`/`SETUP.md` conservan las menciones a Docker como registro histórico/legacy.
