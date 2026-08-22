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
- **Buenas prácticas**: `requirements.txt`, este `CHANGELOG.md`, CI (`.github/workflows/ci.yml`), `tests/test_repo_integrity.py`.
