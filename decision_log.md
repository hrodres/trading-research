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
