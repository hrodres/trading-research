# CHANGELOG — trading-research

Registro de cambios del repositorio (criterio PROJECT.md §8.2: memoria auditable de qué funcionó).

---

## 2026-08-22
- **Setup inicial**: repo público, `PROJECT.md`, `README.md`, `decision_log.md`, `LICENSE` (MIT), `.gitignore`.
- **Fase A.1 (screening)**: `scripts/screening.py` corregido (alineación por fecha + liquidez USDT). Correlaciones 0.58–0.80, BTC↔ETH 0.80, 0 redundantes.
- **Estructura repo**: `scripts/` + `strategies/` + `tests/`.
- **Gobernanza**: principio "GitHub = fuente de verdad" en `PROJECT.md` + `README.md`.
- **Checklist de fases**: `STATUS.md`.
- **Buenas prácticas**: `requirements.txt`, este `CHANGELOG.md`, CI (`.github/workflows/ci.yml`), `tests/test_repo_integrity.py`.
