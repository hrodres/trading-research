# trading-research

![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Status](https://img.shields.io/badge/status-research-yellow)
![Exchange](https://img.shields.io/badge/exchange-Coinbase-blue)
![Engine](https://img.shields.io/badge/engine-freqtrade-orange)

Búsqueda de **edge experto/pro** en crypto (Profit Factor ≥ 1.5 sostenido out-of-sample).

Proyecto de I&D de trading cuantitativo en crypto: usa **freqtrade** como andamiaje (backtest OOS, hyperopt) y construye la capa de valor propia — señales (edge), orquestador adaptativo y aprendizaje por acción/omisión.

## Estado
- Infra: contenedor Docker `freqtrade` en homelab.
- Datos: 9 pares candidatos Coinbase 2h (2020→2026), **sin credenciales**.
- Edge actual: frontera (~PF 1.2). Objetivo: ≥ 1.5.

## Cómo funciona
1. **Fase A** — Medir bien (walk-forward OOS, fees + slippage).
2. **Fase B-D** — Señal de entrada, salida, y diversificación (trend + mean-reversion + funding carry).
3. **Fase F** — Reevaluar. Solo si OOS ≥ 1.5 → staging real (mínimo).

## Documentación
- `PROJECT.md` — propósito, criterios de éxito, guardarraíles, fases.
- `decision_log.md` — decisiones y su justificación (auditable).

## Principios
- Sin apalancamiento para inflar el PF.
- Sin overfit (OOS obligatorio).
- Sin dinero real hasta el gate de staging.

> Repo público. Datos de mercado públicos, sin credenciales.
