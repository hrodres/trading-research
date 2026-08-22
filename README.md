# trading-research

> ⚠️ **Proyecto ARCHIVADO (2026-08-22).** Investigación completa; sin staging a producción por decisión explícita. El veredicto vivo está en `STATUS.md` (Fase F).

Búsqueda de **edge sistemático** en crypto (Profit Factor ≥ 1.5 OOS). Proyecto de I+D
cuantitativo: usa **freqtrade** como andamiaje (backtest OOS) y construye la capa de valor propia.

## Índice
- Estado (resumen)
- Documentación
- Estructura
- Datos NO versionados
- Principios
- Glosario
- Provenancia

## Estado (resumen)
- **Infra:** freqtrade NATIVO en un contenedor LXC dedicado (Debian 13, Proxmox). Ver `SETUP.md`.
- **Datos:** 9 pares Coinbase 2h spot (2020–2026) + klines perp Binance `results/perp_klines/`, **sin credenciales**.
- **Fases:** A ✅ · B ✅ · B.2 (long-candidates) ✅ · B.3 (filtro régimen) ✅ · B.4 (short-candidates) ✅ · C ✅ · D (combinatoria + carry en seco) ✅ / carry staging ⬜ · E ⬜ · F ✅ (archivado).
- **Veredicto honesto:** ninguna señal direccional — ni long ni short — alcanza PF≥1.5 OOS (techo ~1.2–1.3; el short es espejo exacto del long: gana en bear 2022, pierde en bull). El funding carry + filtro de régimen lo rompe en backtest en seco (PF agregado 7.55, mínimo 3.08 en todas las ventanas 2021–2026) pero es mecanismo de funding, no señal direccional, y no está validado en vivo (requiere credenciales + OK). Ver `STATUS.md` y `decision_log.md`.

## Documentación (números vivos en `results/*.json`)
- `PROJECT.md` — propósito, criterios de éxito, guardarraíles.
- `STATUS.md` — checklist de fases (done / pending).
- `decision_log.md` — registro cronológico de decisiones y veredictos (apunta a los JSON).
- `SETUP.md` — instalación freqtrade nativo + cómo correr backtests.

## Estructura
```
trading-research/
├── scripts/      # screening, walkforward, exit/entry_study, portfolio_d, carry_backtest, carry_regime, regime_filter, selector_v1, inspect_export, analyze_longcandidates
├── strategies/   # freqtrade: baseline_trend, exit_study, entry_study, *_long/*_short (pool selector)
├── configs/      # backtest_*.json (A.2/A.3/C/B/B.2-longcandidates/B.4-shortcandidates)
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

## Glosario
- **Edge:** ventaja estadística sostenible buscada aquí como PF ≥ 1.5 OOS.
- **OOS (out-of-sample):** datos no usados en el diseño; validación honesta (sin look-ahead).
- **PF (Profit Factor):** beneficio bruto / pérdida bruta.
- **Gate:** umbral de aceptación (PF ≥ 1.5, DD ≤ 20%, Sharpe ≥ 1.0).
- **Carry:** captura de funding rate de perpetuos (edge de estructura, no direccional).
- **Régimen (regime):** bull/bear según close 2h vs SMA200; entra en el selector.
- **Walk-forward:** validación donde la decisión en t usa solo datos ≤ t.
- **Selector / meta-controlador:** elige la mejor candidata por régimen/ventana.
- **Staging:** despliegue en vivo con capital mínimo tras pasar el gate.
- **Feather:** formato columnar (PyArrow) de klines.
- **CCXT:** librería de acceso a exchanges.
- **Harness:** andamiaje (freqtrade) usado para backtest, no el producto.

## Provenancia (nota, 2026-08-22)
Este repositorio fue concebido, planeado y ejecutado por un **LLM** operando dentro de
**OpenClaw** (runtime de agente). El LLM definió el plan del proyecto (fases A–F, guardarraíles
 de no-overfit y sin apalancamiento), decidió qué estudios y qué **tests** ejecutar, y corrió los
backtests y la agregación sobre freqtrade en un entorno nativo. Los datos, las estrategias y las
conclusiones son del proyecto; la autoría de la ejecución y las decisiones de diseño corresponde
al asistente. (Sesión de revisión documental: modelo `opencode-zen/hy3-free`.)
