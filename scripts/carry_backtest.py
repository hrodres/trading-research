#!/usr/bin/env python3
"""Fase D (carry) — Backtest en seco de funding carry, SIN credenciales.

Objetivo: medir si el funding carry (long spot + short perp 1:1, casi
market-neutral) aporta un PF y una fuente de retorno NO correlacionada con
el trend-following de Fase B. Todo con datos PUBLICOS de Binance (fundingRate
historico, sin API key). Modo paper: no se abre cuenta ni se mueve dinero.

Diseno de la simulacion (honesto, conservador):
- Estrategia: mantener LONG SPOT + SHORT PERP del mismo par y notional 1:1,
  de forma continua durante todo el periodo (2021-2025).
- Cashflow de funding: al ser SHORT perp, recibes cuando rate>0 y pagas cuando
  rate<0. cashflow_i = -rate_i * notional (en unidad de notional=1).
- Fees: round-trip (abrir spot long + abrir perp short + cerrar ambos) =
  4 laminas * fee_rate. Usamos fee_rate taker 0.001 (0.1%) por defecto;
  tambien reportamos con maker 0.0002 para sensibilidad.
- PF del carry = sum(cashflows positivos) / sum(|cashflows negativos|).
  Es el PF de la corriente de funding en si (el alpha estructural).
- Curva de equity: acumulado de cashflows menos fees (entry al inicio,
  exit al final). Max DD y Sharpe sobre esa curva mensual.
- Correlacion: serie mensual de P&L del carry vs serie mensual del trend
  (de results/trades_B.json) -> mide si diversifica de verdad.

NOTA DE VENUE: el trend de Fase B uso Coinbase spot; el carry usa Binance
perp funding (publico). Son instrumentos distintos; el punto es comparar
corrientes de retorno, no replicar venue. Se documenta en decision_log.

Uso:
  python3 scripts/carry_backtest.py --fetch            # descarga funding a results/funding_raw.json (no versionado)
  python3 scripts/carry_backtest.py --analyze          # corre simulacion + correlacion -> results/carry_D.json
  python3 scripts/carry_backtest.py --fetch --analyze  # todo
"""
import argparse
import json
import math
import statistics
import time
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

# Universo (nombres Binance USDT-M perp). Cubre los 9 de Fase A.
SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
           "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "LINKUSDT"]
START_MS = 1609459200000   # 2021-01-01
END_MS = 1767225600000     # 2025-12-31 (coherente con Fase B OOS)
FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
KLINES_URL = "https://fapi.binance.com/fapi/v1/klines"


def _get(url, params, retries=4):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(f"{url}?{q}", headers={"User-Agent": "research"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))


def fetch_funding(symbol, start_ms, end_ms, limit=1000):
    """Pagina fundingRate historico (8h) de Binance USDT-M perp (publico)."""
    out = []
    cursor = start_ms
    while cursor < end_ms:
        data = _get(FUNDING_URL, {
            "symbol": symbol, "startTime": cursor, "endTime": end_ms, "limit": limit,
        })
        if not data:
            break
        for row in data:
            ts = row["fundingTime"]
            rate = float(row["fundingRate"])
            out.append((ts, rate))
        last = data[-1]["fundingTime"]
        if last <= cursor:
            break
        cursor = last + 1
        time.sleep(0.05)  # educado con el rate limit
    return out


def yearly_pf(raw, fee_rate=0.001):
    """PF de carry por año (agregado de todos los simbolos) para ver dependencia de regimen."""
    by_year = defaultdict(lambda: {"gp": 0.0, "gl": 0.0})
    for sym, series in raw.items():
        for ts, rate in series:
            yr = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).year
            cf = rate  # cashflow SHORT perp = +rate (notional 1)
            if cf >= 0:
                by_year[yr]["gp"] += cf
            else:
                by_year[yr]["gl"] += -cf
    n_years = len(by_year) or 1
    fee_per_year = (4 * fee_rate) / n_years
    out = {}
    for yr in sorted(by_year):
        gp = by_year[yr]["gp"]
        gl = by_year[yr]["gl"]
        net = gp - gl - fee_per_year
        pf = (gp / gl) if gl > 0 else None
        out[str(yr)] = {
            "pf": round(pf, 3) if pf is not None else None,
            "net_pnl": round(net, 4),
            "gross_profit": round(gp, 4),
            "gross_loss": round(gl, 4),
        }
    return out


def simulate_carry(funding_series, notional=1.0, fee_rate=0.001):
    """Simula hold continuo long spot + short perp 1:1. Devuelve metricas.

    Estrategia carry: SHORT perp (cobras cuando rate>0, pagas cuando rate<0).
    cashflow_i = +rate_i * notional  (SHORT recibe funding positivo).
    NOTA: el signo + es critico; confundirlo con - invierte el resultado.
    """
    if not funding_series:
        return None
    cashflows = [rate * notional for _ts, rate in funding_series]
    gp = sum(c for c in cashflows if c > 0)
    gl = sum(-c for c in cashflows if c < 0)
    fees = 4 * fee_rate * notional  # round-trip: 4 laminas
    net = sum(cashflows) - fees
    pf = (gp / gl) if gl > 0 else None
    n_pos = sum(1 for c in cashflows if c > 0)
    n_neg = sum(1 for c in cashflows if c < 0)
    n = len(cashflows)
    # curva de equity: arranca en notional (el fee se descuenta al cierre)
    curve = []
    cum = 0.0
    for c in cashflows:
        cum += c
        curve.append(cum)
    cum -= fees  # fee round-trip al cerrar
    # max dd sobre EQUITY real = notional + P&L acumulado (capital en riesgo)
    peak = notional
    mdd = 0.0
    for v in curve:
        eq = notional + v
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak if peak > 0 else 0.0
        mdd = max(mdd, dd)
    years = (funding_series[-1][0] - funding_series[0][0]) / (365.25 * 86400_000)
    ann_ret = (net / notional) / years if years > 0 else None
    # sharpe mensual aproximado
    monthly = _monthly_from_curve(curve, funding_series)
    sh = _sharpe(monthly)
    return {
        "n_funding_events": n,
        "n_positive": n_pos,
        "n_negative": n_neg,
        "pct_positive": round(100 * n_pos / n, 1) if n else 0.0,
        "gross_profit": round(gp, 4),
        "gross_loss": round(gl, 4),
        "net_pnl": round(net, 4),
        "pf": round(pf, 3) if pf is not None else None,
        "fees_round_trip": round(fees, 4),
        "annualized_return_pct": round(ann_ret * 100, 2) if ann_ret is not None else None,
        "max_drawdown_pct": round(mdd * 100, 2),
        "sharpe_annualized": round(sh, 3) if sh is not None else None,
        "years": round(years, 2),
    }


def _monthly_from_curve(curve, funding_series):
    """Agrupa cashflows por mes para serie mensual de P&L."""
    by_month = defaultdict(float)
    for (ts, _), c in zip(funding_series, curve):
        ym = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m")
        by_month[ym] += c
    return [by_month[m] for m in sorted(by_month)]


def _sharpe(vals):
    if len(vals) < 3:
        return None
    mean = statistics.mean(vals)
    sd = statistics.pstdev(vals)
    if sd == 0:
        return None
    return (mean / sd) * math.sqrt(12)


def trend_monthly(trades_b_path):
    """Serie mensual de P&L del trend (todas las variantes de Fase B)."""
    with open(trades_b_path) as fh:
        trades = json.load(fh)
    by_month = defaultdict(float)
    for t in trades:
        ts = t.get("close_ts")
        if not ts:
            continue
        ym = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m")
        by_month[ym] += t["profit_abs"]
    return by_month


def _pearson(x, y):
    if len(x) < 3:
        return None
    mx = statistics.mean(x)
    my = statistics.mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def correlate(carry_monthly_by_symbol, trend_monthly):
    """Correlacion de cada carry vs el trend agregado de Fase B."""
    trend_months = sorted(trend_monthly.keys())
    trend_vals = [trend_monthly[m] for m in trend_months]
    out = {}
    for sym, series in carry_monthly_by_symbol.items():
        common = sorted(set(series.keys()) & set(trend_months))
        if len(common) < 6:
            out[sym] = None
            continue
        x = [series[m] for m in common]
        y = [trend_monthly[m] for m in common]
        out[sym] = round(_pearson(x, y), 3)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--fee-rate", type=float, default=0.001)
    ap.add_argument("--raw-out", default="results/funding_raw.json")
    ap.add_argument("--result-out", default="results/carry_D.json")
    ap.add_argument("--trades-b", default="results/trades_B.json")
    args = ap.parse_args()

    if not (args.fetch or args.analyze):
        args.fetch = args.analyze = True

    raw = {}
    if args.fetch:
        for sym in SYMBOLS:
            print(f"[fetch] {sym}...", flush=True)
            raw[sym] = fetch_funding(sym, START_MS, END_MS)
            print(f"  {len(raw[sym])} eventos", flush=True)
        with open(args.raw_out, "w") as fh:
            json.dump(raw, fh)
        print(f"[fetch] -> {args.raw_out}")

    if args.analyze:
        if not raw:
            with open(args.raw_out) as fh:
                raw = json.load(fh)
        results = {}
        carry_monthly = {}
        for sym in SYMBOLS:
            series = raw.get(sym, [])
            if not series:
                continue
            res = simulate_carry(series, fee_rate=args.fee_rate)
            results[sym] = res
            # serie mensual para correlacion
            bm = defaultdict(float)
            for ts, rate in series:
                ym = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m")
                bm[ym] += rate  # cashflow SHORT perp = +rate (notional 1)
            carry_monthly[sym] = bm
        trend = trend_monthly(args.trades_b)
        corr = correlate(carry_monthly, trend)
        yearly = yearly_pf(raw, fee_rate=args.fee_rate)
        # agregado: suma de todas las series de carry
        agg_monthly = defaultdict(float)
        for bm in carry_monthly.values():
            for m, v in bm.items():
                agg_monthly[m] += v
        agg_curve = sorted(agg_monthly.items())
        agg_net = sum(v for _, v in agg_curve)
        # PF agregado: suma de todos los cashflows positivos / negativos
        all_pos = sum(r["gross_profit"] for r in results.values() if r)
        all_neg = sum(r["gross_loss"] for r in results.values() if r)
        agg_pf = (all_pos / all_neg) if all_neg > 0 else None
        out = {
            "method": "funding carry paper backtest (Binance USDT-M perp, public API, sin credenciales). Long spot + short perp 1:1 hold continuo 2021-2025. cashflow_i=-rate_i*notional; fees round-trip 4 laminas*taker 0.1%. PF=GP/GL de la corriente de funding.",
            "fee_rate": args.fee_rate,
            "period": {"start": START_MS, "end": END_MS},
            "per_symbol": results,
            "aggregated": {
                "gross_profit": round(all_pos, 4),
                "gross_loss": round(all_neg, 4),
                "pf": round(agg_pf, 3) if agg_pf is not None else None,
                "net_pnl": round(agg_net, 4),
            },
            "correlation_vs_trend_B": corr,
            "yearly_pf": yearly,
        }
        with open(args.result_out, "w") as fh:
            json.dump(out, fh, indent=2)
        print(f"\n=== CARRY (taker fee {args.fee_rate}) ===")
        print(f"{'SYMBOL':10} {'PF':>6} {'net':>9} {'%pos':>6} {'annRet%':>8} {'maxDD%':>8} {'corr':>6}")
        for sym in SYMBOLS:
            r = results.get(sym)
            if not r:
                continue
            c = corr.get(sym)
            print(f"{sym:10} {str(r['pf']):>6} {r['net_pnl']:>9} {r['pct_positive']:>6} "
                  f"{str(r['annualized_return_pct']):>8} {r['max_drawdown_pct']:>8} {str(c):>6}")
        print(f"\nAGGREGATED PF = {out['aggregated']['pf']}  net={out['aggregated']['net_pnl']}")
        print(f"[out] -> {args.result_out}")


if __name__ == "__main__":
    main()
