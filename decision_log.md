# Decision Log — trading-research

Registro cronológico de decisiones, resultados y cambios del repositorio.
**Los números vivos están en `results/*.json`**; aquí solo el veredicto cualitativo
y el enlace. Criterio PROJECT.md §8.2: memoria auditable de qué funcionó.

---

## 2026-08-22 — Setup inicial del proyecto
- Proyecto nuevo `trading-research` (clean slate, no basado en v9) para buscar edge experto/pro (PF ≥ 1.5 OOS).
- Infra inicial: Docker `freqtrade` en CT 112. **Posteriormente migrado a freqtrade NATIVO en CT 113** (ver `SETUP.md`); el Docker quedó `restart=no`.
- Fase A: datos públicos Coinbase spot 2h, 9 pares candidatos (sin credenciales).
- Repo GitHub público `hrodres/trading-research`.

## 2026-08-22 — Fase A.1: Screening de pares
- `scripts/screening.py` corregido (alineación por fecha, no por posición).
- Correlación log-returns 0.58–0.80; 0 pares con corr ≥0.80 (margen para diversificar). Liquidez: BTC $1.68M → DOT $8.5K/2h. XRP arranca 2023-07 (fuera del gate 4+ años).
- Detalle: `results/` + `STATUS.md`.

## 2026-08-22 — Fase A.2 / A.3: Baseline + Walk-forward OOS
- `strategies/baseline_trend.py` valida el **harness OOS** (no busca edge).
- A.3 walk-forward 2021–2025, sizing fijo 100 USDT, sin fitting → **0 pares pasan el gate PF≥1.5** (PF 0.276–0.395). La baseline NO tiene edge.
- Evidencia: `results/walkforward_A3.json`.

## 2026-08-22 — Fase C: Estudio de exits
- 4 variants (mismo exit ganador). El TP fijo corto era el asesino nº1; "let winners run" (EMA-cross) sube PF ~2x vs baseline. **0 variants/par pasan el gate** (mejor PF 0.65; mejor celda SOL 0.98).
- Conclusión: el bottleneck es la **entrada**, no el exit.
- Evidencia: `results/exitstudy_C.json`.

## 2026-08-22 — Fase B: Estudio de entradas
- 6 variants (mismo exit de C). **0 variants/par pasan el gate**. Mejor celda: EntryVolConfirm SOL/USDT PF **1.283** (techo trend-following 2h ~1.3). EntryMeanRev (contrarian) PF 0.066 → régimen confirmado trend-following.
- Anexo forense `EntryV9Style` (a petición del usuario): casi inerte (5 trades/5a, PF 0.0), aislado como registro, NO canónico.
- Evidencia: `results/entrystudy_B.json`, `results/entrystudy_v9style.json`.

## 2026-08-22 — Fase D: Diversificación (combinatoria + carry en SECO)
### D.1 Combinatoria de portfolio (scripts/portfolio_d.py)
- Agrega los 6622 trades OOS de Fase B. PF agregado top-10 = **1.063** (todas las monedas) / **0.963** (gate-compliant sin XRP) — **INFERIOR a la mejor celda aislada (1.283)**.
- Correlación intra-par trend 0.95–0.99: combinar trend correlacionado **NO** diversifica. **GATE NO ALCANZADO con spot trend 2h solo.**
- Evidencia: `results/portfolio_D.json` (escenarios + matrices de correlación).

### D.2 Funding carry en SECO (scripts/carry_backtest.py, sin credenciales)
- Funding público Binance USDT-M perp 2021–2025 (49.377 eventos). Long spot + short perp 1:1. **PF agregado 3.447** → rompe el gate ≥1.5.
- PERO correlación vs trend **+0.43/+0.55** (NO diversifica; concentra riesgo de régimen). 2022 (bajista) cae a PF 0.51 (neto negativo). 80.7% de eventos con funding positivo.
- Veredicto: el edge existe vía carry en papel, pero es **riesgo de régimen concentrado**, no diversificación mágica. Riesgos en vivo NO modelados (liquidación, basis, exchange).
- Evidencia: `results/carry_D.json`. Staging pendiente (requiere credenciales + OK Héctor).

## Cambios de infra/datos (registro)
- Migración Docker CT 112 → freqtrade nativo CT 113 (`SETUP.md`).
- `requirements.txt` → `freqtrade==2026.7`.
- Credenciales GitHub vía token en URL (limpio tras push); remote sin placeholder `***`.

## Estado final de la sesión (04:59)
- A✅ B✅ C✅ D(combinatoria+carry en seco)✅. Carry staging ⬜ · E ⬜ · F ⬜.
- **Ninguna estrategia direccional (long) alcanza PF≥1.5** (techo ~1.3). El carry lo rompe en backtest pero es mecanismo de funding, no señal direccional, y no está validado en vivo.
- Decisión del usuario: el proyecto, por su criterio (edge direccional validado), no tiene viabilidad demostrada. Repo en "punto honesto", documentación consolidada en esta rama.
