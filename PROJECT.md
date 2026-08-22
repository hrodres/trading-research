# trading-research

Búsqueda de **edge sistemático en crypto** con **Profit Factor (PF) ≥ 1.5** sostenido
out-of-sample (OOS), neto de fees + slippage + compuesto, con drawdown acotado.

## Propósito
El entregable NO es "una estrategia long con PF≥1.5". Es un **sistema de señales /
meta-controlador** que decide qué hacer en cada momento: mantiene un **pool de
estrategias candidatas** y selecciona la mejor según el régimen de mercado (regime /
online selection), con **walk-forward estricto** (la decisión en `t` usa solo datos
≤ `t`; el PF se mide en datos `> t`). El backtesting con freqtrade es el harness de
validación, no el producto.

## Criterios de éxito
| Métrica | ÉXITO | EXCELENCIA |
|---|---|---|
| PF del PROCESO de selección OOS (walk-forward 2-3 años, neto fees+slip+compuesto) | ≥ 1.5 | ≥ 2.0 |
| Max drawdown (backtest) | ≤ 20% | ≤ 12% |
| Sharpe anualizado | ≥ 1.0 | ≥ 1.5 |

El gate se aplica al **proceso de selección completo** (selector), NO al PF suelto de
cada candidata: comparar PF individuales y quedarse con la mayor = selection bias /
look-ahead. Solo si el selector cumple ÉXITO en OOS → staging con capital mínimo.
Por encima de 2.0 suele ser overfit o cola de riesgo escondida; 1.5 es ambicioso
pero honesto.

## Guardarraíles (no negociables)
- ❌ Sin apalancamiento para inflar el PF.
- ❌ Sin overfit: validación OOS obligatoria; prohibido ajustar parámetros mirando el OOS.
- ❌ Sin dinero real hasta pasar el gate de staging.
- ❌ Sin perseguir velocidad / retorno reciente (receta de blow-up).

## Alcance técnico
- **Datos sin credenciales**: Coinbase spot 2h (Fases A–C, D combinatoria). El funding
  carry (Fase D) usa funding público de perpetuos; su staging requiere credenciales.
- **Harness**: freqtrade (backtest OOS, `--strategy-list`). Scripts de agregación en
  stdlib puro (sin freqtrade/numpy) para validar en cualquier host.
- **Estrategias objetivo**: trend-following, mean-reversion (no correlacionada), y
  captura de funding rate (carry, casi alpha por estructura).
- **Sizing**: Kelly fraccionado + cap de riesgo por régimen (1–2% capital por trade).
- **Repo público** (contenido 100% no-sensible). **GitHub = fuente de verdad**: las
  copias locales/contenedor son artefactos de despliegue; si discrepan, manda GitHub.

## Fases (gates en STATUS.md)
- **A** Cimientos de medida (harness OOS reproducible).
- **B** Señal de entrada · **B.2** Pool del selector (long-candidates) · **B.3** Filtro de régimen (selector, componente 1) · **B.4** Pool del selector (short-candidates, brazo bear) · **C** Salida.
- **D** Diversificación (combinatoria + carry) · **E** Sizing/ejecución · **F** Reevaluar con evidencia.

## Gobernanza
- Calidad: `py_compile` + tests antes de cada cambio; nunca commitear sin validar.
- GitHub = fuente de verdad (canónica). Verificar contra la API tras cada push.
- Estructura: `scripts/` (análisis), `strategies/` (freqtrade), `tests/` (unitarios).
- Commits de código y documentación por separado.
- Ritual de push: token real en URL (nunca placeholder), limpiado tras el push; scan
  anti-secret antes de cada commit.
