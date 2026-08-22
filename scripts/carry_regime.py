#!/usr/bin/env python3
"""Fase D.2 — Funding carry filtrado por régimen (selector aplicado al carry).

Mismo modelo de simulacion que carry_backtest.py (Fase D):
  - Estrategia: LONG SPOT + SHORT PERP 1:1, notional 1, hold continuo 2021-2025.
  - Cashflow por evento de funding: +rate_i (al ser SHORT perp, cobras si rate>0).
  - Fees round-trip: 4 laminas * 0.001 (taker), descontados una vez al cierre.
  - PF = GP / GL de la corriente de funding; net = GP - GL - fees.

Novedad (componente selector, componente 1 validado en B.3):
  El filtro apaga el carry fuera de regimen bull. Tres variantes comparadas:
    ALL    : carry continuo (referencia, = carry_D.json)
    GLOBAL : solo mantener carry cuando close BTC/USDT 2h > SMA200 (bull de mercado)
    PERPAR : solo cuando el PROPIO par esta en bull (BNB no listado en Coinbase
             -> usa proxy global BTC, documentado como caveat).
  Decision en t usa SOLO la ultima vela 2h cerrada <= funding_ts (bisect, sin
  lookahead). Regimen indefinido (<200 velas de historia o sin vela previa)
  = no operar ese evento (conservador, igual que regime_filter.py).

Salida:
  - stdout: PF agregado y por anio en las 3 variantes + veredicto
  - results/carry_regime_summary.csv (evidencia versionable)
Uso:
  python3 scripts/carry_regime.py
"""
import csv
import json
import os
import sys
from bisect import bisect_left
from collections import defaultdict
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import regime_filter as rf  # noqa: E402  (build_regime, load_regular_csv, make_lookup, regime_at)

FEE_RATE = 0.001
RAW_PATH = os.path.join(REPO, "results", "funding_raw.json")
BTC_CSV = os.path.join(REPO, "results", "btc_2h.csv")
PAIRS_CSV = os.path.join(REPO, "results", "pairs_2h.csv")
OUT_CSV = os.path.join(REPO, "results", "carry_regime_summary.csv")

# funding Binance perp -> par del universo Coinbase (para per-par)
SYM2PAIR = {"BTCUSDT": "BTC/USDT", "ETHUSDT": "ETH/USDT", "SOLUSDT": "SOL/USDT",
            "BNBUSDT": "BNB/USDT", "XRPUSDT": "XRP/USDT", "ADAUSDT": "ADA/USDT",
            "DOGEUSDT": "DOGE/USDT", "AVAXUSDT": "AVAX/USDT", "LINKUSDT": "LINK/USDT"}


def regime_at_ts(funding_ms, dates, regime):
    """Regimen vigente en funding_ts: ultima vela 2h cerrada ANTES/igual que ts."""
    dt = datetime.fromtimestamp(funding_ms / 1000, tz=timezone.utc)
    idx = bisect_left(dates, dt) - 1
    if idx < 0 or regime[idx] is None:
        return None  # sin vela previa o historia insuficiente -> no operar
    return regime[idx]


def main():
    with open(RAW_PATH) as fh:
        raw = json.load(fh)

    # Lookups de regimen
    global_lu = rf.make_lookup(rf.load_regular_csv(BTC_CSV))
    g_dates, _g_closes, g_regime = global_lu["GLOBAL"]
    perpar_lu = rf.make_lookup(rf.load_regular_csv(PAIRS_CSV, pair_col="pair"))
    print(f"regimen GLOBAL: {len(g_dates)} velas BTC; PERPAR: {len(perpar_lu)} pares")

    # Acumuladores por (variante, simbolo-perp) y por (variante, anio)
    cash = {v: defaultdict(list) for v in ("ALL", "GLOBAL", "PERPAR")}   # [ts, cashflow]
    counts = {v: defaultdict(int) for v in ("ALL", "GLOBAL", "PERPAR")}  # activo / total
    by_year = {v: defaultdict(lambda: {"gp": 0.0, "gl": 0.0}) for v in ("ALL", "GLOBAL", "PERPAR")}

    for sym, series in sorted(raw.items()):
        pair = SYM2PAIR[sym]
        p_dates, _c, p_regime = perpar_lu.get(pair, (None, None, None))
        for ts, rate in series:
            yr = str(datetime.fromtimestamp(ts / 1000, tz=timezone.utc).year)
            # ALL: siempre activo
            for v in ("ALL",):
                cash[v][sym].append((ts, rate))
                counts[v][sym] += 1
                _acc(cash[v][sym], by_year[v][yr], rate)
            # GLOBAL: activo solo si bull BTC
            r_g = regime_at_ts(ts, g_dates, g_regime)
            if r_g is True:
                cash["GLOBAL"][sym].append((ts, rate))
                counts["GLOBAL"][sym] += 1
                _acc(cash["GLOBAL"][sym], by_year["GLOBAL"][yr], rate)
            # PERPAR: activo solo si bull del propio par (BNB -> proxy global)
            if p_dates is None:
                r_p = r_g
            else:
                r_p = regime_at_ts(ts, p_dates, p_regime)
            if r_p is True:
                cash["PERPAR"][sym].append((ts, rate))
                counts["PERPAR"][sym] += 1
                _acc(cash["PERPAR"][sym], by_year["PERPAR"][yr], rate)

    # Metricas agregadas por variante
    print(f"\n{'variante':<8}{'n_ev':>7}{'n_pos':>7}{'GP':>10}{'GL':>10}{'PF':>8}{'net(+fees)':>12}")
    rows = []
    for v in ("ALL", "GLOBAL", "PERPAR"):
        all_cf = [cf for s in cash[v].values() for _ts, cf in s]
        gp = sum(c for c in all_cf if c > 0)
        gl = sum(-c for c in all_cf if c < 0)
        n = len(all_cf)
        n_pos = sum(1 for c in all_cf if c > 0)
        fees = 4 * FEE_RATE * len(cash[v])  # 1 round-trip por simbolo presente
        net = sum(all_cf) - fees
        pf = (gp / gl) if gl > 0 else float("inf")
        print(f"{v:<8}{n:>7}{n_pos:>7}{gp:>10.4f}{gl:>10.4f}{pf:>8.3f}{net:>12.4f}")
        rows.append({"variante": v, "n_eventos": n, "n_positivos": n_pos,
                     "gross_profit": round(gp, 4), "gross_loss": round(gl, 4),
                     "pf": round(pf, 3), "net_pnl": round(net, 4),
                     "fees_round_trip": round(fees, 4)})

    print("\n=== PF por anio (agregado todos los simbolos) ===")
    print(f"{'anio':<6}{'PF ALL':>9}{'PF GLOBAL':>11}{'PF PERPAR':>11}")
    for yr in sorted(set(y for v in by_year.values() for y in v)):
        line = f"{yr:<6}"
        for v in ("ALL", "GLOBAL", "PERPAR"):
            d = by_year[v].get(yr, {"gp": 0.0, "gl": 0.0})
            pf = (d["gp"] / d["gl"]) if d["gl"] > 0 else float("inf")
            line += f"{pf:>11.3f}"
        print(line)

    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nCSV -> {OUT_CSV}")


def _acc(series, year_acc, rate):
    """Acumula cashflow (positivo/negativo) y anade a la serie."""
    year_acc["gp"] += rate if rate > 0 else 0.0
    year_acc["gl"] += -rate if rate < 0 else 0.0


if __name__ == "__main__":
    main()
