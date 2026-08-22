# trading-research

Búsqueda de **edge experto/pro** en crypto (Profit Factor ≥ 1.5 OOS). Proyecto de I&D
cuantitativo: usa **freqtrade** como andamiaje (backtest OOS) y construye la capa de valor propia.

## Estado (resumen)
- **Infra:** freqtrade NATIVO en un contenedor LXC dedicado (Debian 13, Proxmox). Ver `SETUP.md`.
- **Datos:** 9 pares Coinbase 2h (2020→2026), **sin credenciales**.
- **Fases:** A ✅ · B ✅ · B.2 (long-candidates) ✅ · C ✅ · D (combinatoria + carry en seco) ✅ / carry staging ⬜ · E ⬜ · F ⬜.
- **Veredicto honesto:** ninguna señal direccional (long) alcanza PF≥1.5 (techo ~1.3). La mejor candidata del pool del selector (`VolBreakoutLong`) da PF mediana 1.45 en 5 ventanas 2021-2026 pero pierde en bear/range (2022, 2025-26) — edge de régimen, no alpha. El funding carry lo rompe en backtest en seco (PF 3.4) pero es mecanismo de funding, no señal direccional, y no está validado en vivo. Por el criterio del usuario (edge direccional validado), el proyecto no tiene viabilidad demostrada. Ver `STATUS.md` y `decision_log.md`.

## Documentación (números vivos en `results/*.json`)
- `PROJECT.md` — propósito, criterios de éxito, guardarraíles.
- `STATUS.md` — checklist de fases (done / pending).
- `decision_log.md` — registro cronológico de decisiones y veredictos (apunta a los JSON).
- `SETUP.md` — instalación freqtrade nativo + cómo correr backtests.

## Desarrollo
Este repositorio fue concebido, planeado y ejecutado por un **LLM** operando dentro de
**OpenClaw** (runtime de agente). El LLM definió el plan del proyecto (fases A–F, guardarraíles
de no-overfit y sin apalancamiento), decidió qué estudios y qué **tests** ejecutar, y corrió los
backtests y la agregación sobre freqtrade en un entorno nativo. La sesión de esta revisión usó
el modelo `opencode-zen/hy3-free`. Los datos, las estrategias y las conclusiones son del
proyecto; la autoría de la ejecución y las decisiones de diseño corresponde al asistente.

## Estructura
```
trading-research/
├── scripts/      # screening, walkforward, exit/entry_study, portfolio_d, carry_backtest, analyze_longcandidates
├── strategies/   # freqtrade: baseline_trend, exit_study, entry_study, *_long (pool selector)
├── configs/      # backtest_*.json (A.2/A.3/C/B/B.2-longcandidates)
├── results/      # salida de backtests (JSON, CSV resumen, evidencia)
├── tests/        # test_repo_integrity, test_portfolio_d, test_carry_backtest
├── PROJECT.md · STATUS.md · decision_log.md · SETUP.md · README.md
├── requirements.txt · .gitignore · LICENSE (MIT)
```
> **Datos NO versionados:** klines Coinbase 2h en `/opt/freqtrade/user_data/data/coinbase/`. El raw `results/trades_B.json` y `results/funding_raw.json` son regenerables y están en `.gitignore`.

## Principios
- Sin apalancamiento para inflar PF · Sin overfit (OOS obligatorio) · Sin $ real hasta gate de staging.
- **GitHub = fuente de verdad** (canónica). Si discrepa con copias locales/contenedores, manda GitHub.
- Repo público; datos de mercado públicos, sin credenciales.
