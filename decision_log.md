# Decision Log — trading-research

Registro auditable de decisiones y su justificación. (Criterio del PROJECT.md: cada cambio/ajuste se documenta.)

---

## 2026-08-22 — Setup inicial del proyecto

**Decisión:** Crear proyecto nuevo `trading-research` (clean slate, no basado en v9) para buscar edge experto/pro (PF ≥ 1.5 OOS).

**Justificación:**
- v9 tiene edge frontera (~PF 1.2) que no compensa el riesgo del perfil 2x (28% capital por SL). Mejor buscar edge mejor con disciplina que operar ciego.
- No construir backtester desde cero: usar **freqtrade** (OSS maduro: backtest OOS, hyperopt). Trabajo propio = señales (edge) + orquestador adaptativo.
- **Sin credenciales**: Fase A usa datos públicos de Coinbase.

**Infra montada:**
- Contenedor Docker `freqtrade` (imagen `freqtradeorg/freqtrade:stable`) en CT 112 (`docker-apps`, Proxmox 192.168.1.222). Límites `--cpus 2 --memory 2g`. Volumen `/docker/freqtrade/user_data`.
- Exchange para Fase A: **Coinbase** (spot, klines públicas, sin API key). Kraken descartado para Fase A (no sirve klines directos → `--dl-trades` muy lento); reservado para funding carry (Fase D).
- 9 pares candidatos descargados (Coinbase 2h, 2020→2026): BTC, ETH, SOL, XRP, ADA, DOGE, DOT, AVAX, LINK. BNB/MATIC/LTC no listados en Coinbase spot USDT → descartados. **Son candidatos a screening, NO pares elegidos** (la selección final es data-driven: liquidez + matriz de correlación + backtest individual OOS, según PROJECT.md §8.1).

**Repo GitHub:** `hrodres/trading-research` (**público** — contenido no-sensible, datos de mercado públicos, sin credenciales). Token de GitHub usado vía variable de entorno y limpiado del remote local tras el push.

**No hecho aún:** estrategias, backtests. Primero verificar entorno (hecho) y luego screening de pares + Fase A (walk-forward OOS de la señal simple).

**Riesgo conocido:** contención de CPU con chromium si se corre backtest grande en CT 112 (mitigado con `--cpus 2`).

---

## 2026-08-22 — Fase A.1: Screening de pares (CORREGIDO)

**Contexto:** La 1ª versión de `screening.py` alineaba precios por POSICIÓN en vez de por FECHA → correlaciones espurias ~0 para pares con distinto inicio. Bug confirmado y corregido (alineación por fecha + liquidez en USDT). Ver commit de `screening.py`.

**Datos:** Coinbase 2h. Cobertura por par:
- BTC/ETH: 2021-05 → 2026-01 (20528 velas)
- SOL 2021-06, DOGE 2021-06, DOT 2021-06, AVAX 2021-09, ADA/LINK 2022-02, **XRP 2023-07** (10906 velas, el más corto).
- **Periodo común (todos los pares): 2023-07-13 → 2026-01-08 = 10113 velas (~2.5 años).**

**Matriz de correlación (log-returns, periodo común):** rango 0.58–0.80. BTC↔ETH = 0.80 (la más alta, pero NO redundante: corte ≥0.80 no saltó). ETH↔LINK 0.75, DOT↔ADA 0.76, DOT↔LINK 0.74. **0 pares con corr ≥0.80 → no hay redundancia total; hay margen real para diversificar** (lección aplicada vs v9, que tenía todo amontonado).

**Liquidez (mediana USDT / vela 2h):** BTC $1.68M · ETH $1.13M · SOL $210K · XRP $120K · DOGE $57K · ADA $25K · AVAX $25K · LINK $14K · DOT $8.5K.

**Conclusiones (observación, NO elección de pares aún):**
1. Crypto es un mercado correlacionado de verdad (no ruido). Diversificación real ayuda pero no elimina el riesgo común (BTC mueve a casi todos).
2. **Caveat de historia:** el periodo común es solo ~2.5 años porque XRP arranca en 2023-07. BTC/ETH/SOL/etc. tienen ~4.6 años. Para el gate de 4+ años del PROJECT.md, **XRP queda fuera del gate final** (solo 2.5y) aunque se mida en el común.
3. **Liquidez fina** (DOT/LINK/AVAX/ADA <$30K/2h): riesgo de slippage real. Válidos para medir OOS; en staging habrá que acotar tamaño posición.

**Siguiente:** A.2 (estrategia baseline trend/momentum) + A.3 (walk-forward OOS por par). La elección de universo de pares se hace tras A.3, no ahora.

