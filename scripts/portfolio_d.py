#!/usr/bin/env python3
"""Fase D — Harness de agregacion de portfolio (combinatoria OOS, SIN freqtrade).

Objetivo: medir si combinar multiples estrategias/pares NO correlacionadas
levanta el PF agregado y BAJA el drawdown respecto a las partes (el multiplicador
real de la diversificacion, segun PROJECT.md Fase D).

Diseno honesto (leer antes de usar):
- Entrada: lista de trades crudos {variant, pair, open_ts, close_ts, profit_abs}
  (USD fijo por trade, sizing 100 USDT, sin compuesto — coherente con A/B/C).
  Se genera con scripts/entry_study.py -> results/trades_B.json.
- Cada "strategia" = (variant, pair). Varias estrategias se combinan en un portfolio.
- Curva de equity: E(t) = suma acumulada de profit_abs de los trades cerrados <= t.
  Sin apalancamiento, sin compuesto (unidad = 1 USDT). Es la medida conservadora:
  no asume reinversion ni multiplica riesgo.
- PF agregado = sum(profits) / sum(|losses|) sobre todos los trades del portfolio.
- Max drawdown = mayor caida pico-a-valle de la curva de equity acumulada.
- Sharpe anualizado = mean(monthly_ret)/std(monthly_ret) * sqrt(12), con monthly_ret
  = variacion de equity del mes (proxy; sin capital base, usamos retorno sobre la
  exposicion media). Documentado como aproximacion.
- Matriz de correlacion: por estrategia, serie mensual de P&L neto; Pearson por pares
  (drop de meses sin datos en ambas). Mide si realmente diversificamos o duplicamos
  la misma senal (leccion v9: BTC/ETH/SOL/LINK bailan igual).

NO requiere freqtrade ni numpy: solo stdlib. Corre en cualquier host para validar
la agregacion antes/depués de generar los trades en CT 113.

Uso:
  python3 scripts/portfolio_d.py --trades results/trades_B.json \
      --include EntryVolConfirm:ENTRYV9STYLE-NO ...  (o --auto para top-N por PF)
"""
import argparse
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime, timezone


def load_trades(path):
    with open(path) as fh:
        return json.load(fh)


def strategy_key(t):
    return f"{t['variant']}:{t['pair']}"


def profit_factor(trades):
    gp = sum(t["profit_abs"] for t in trades if t["profit_abs"] >= 0)
    gl = sum(-t["profit_abs"] for t in trades if t["profit_abs"] < 0)
    if gl <= 0:
        return None
    return gp / gl


def equity_curve(trades, unit=1.0):
    """Curva de equity acumulada ordenada por close_ts (ms epoch)."""
    pts = sorted(trades, key=lambda t: t.get("close_ts") or 0)
    curve = []
    eq = 0.0
    for t in pts:
        eq += t["profit_abs"] * unit
        curve.append((t.get("close_ts") or 0, eq))
    return curve


def max_drawdown(curve):
    """Devuelve (max_dd_fraction, peak_eq, trough_eq). dd=0 si curve vacia/creciente."""
    if not curve:
        return 0.0, 0.0, 0.0
    peak = curve[0][1]
    mdd = 0.0
    peak_at = peak
    trough_at = peak
    for _ts, eq in curve:
        if eq > peak:
            peak = eq
            peak_at = eq
        dd = (peak - eq) / peak if peak > 0 else 0.0
        if dd > mdd:
            mdd = dd
            trough_at = eq
    return mdd, peak_at, trough_at


def monthly_series(trades):
    """Serie mensual de P&L neto por estrategia. {strat: {ym: pnl}}."""
    series = defaultdict(lambda: defaultdict(float))
    for t in trades:
        ts = t.get("close_ts")
        if not ts:
            continue
        ym = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m")
        series[strategy_key(t)][ym] += t["profit_abs"]
    return series


def correlation_matrix(series):
    """Pearson por pares sobre meses comunes. Devuelve {a:{b:r}}."""
    strats = list(series.keys())
    months = {s: set(series[s].keys()) for s in strats}
    out = {s: {} for s in strats}
    for i, a in enumerate(strats):
        for b in strats[i:]:
            common = sorted(months[a] & months[b])
            if len(common) < 3:
                r = None
            else:
                xa = [series[a][m] for m in common]
                xb = [series[b][m] for m in common]
                r = _pearson(xa, xb)
            out[a][b] = r
            out[b][a] = r
    return out


def _pearson(x, y):
    n = len(x)
    if n < 2:
        return None
    mx = statistics.mean(x)
    my = statistics.mean(y)
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    dx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    dy = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def sharpe_monthly(trades, periods_per_year=12):
    """Sharpe anualizado aproximado sobre retornos mensuales de la curva de equity."""
    s = monthly_series(trades)
    # agrega todas las estrategias en una unica serie mensual de P&L
    agg = defaultdict(float)
    for strat, vals in s.items():
        for ym, v in vals.items():
            agg[ym] += v
    vals = [agg[ym] for ym in sorted(agg)]
    if len(vals) < 3:
        return None
    mean = statistics.mean(vals)
    sd = statistics.pstdev(vals)
    if sd == 0:
        return None
    return (mean / sd) * math.sqrt(periods_per_year)


def select_strategies(trades, top_n=None, min_trades=30):
    """Ranking de (variant,pair) por PF agregado OOS; filtra n>=min_trades."""
    by_strat = defaultdict(list)
    for t in trades:
        by_strat[strategy_key(t)].append(t)
    ranked = []
    for k, ts in by_strat.items():
        if len(ts) < min_trades:
            continue
        pf = profit_factor(ts)
        if pf is None:
            continue
        ranked.append((k, pf, len(ts)))
    ranked.sort(key=lambda x: -x[1])
    if top_n:
        ranked = ranked[:top_n]
    return ranked


def build_portfolio(trades, include):
    """Filtra trades al subset de estrategias incluidas (lista de 'variant:pair')."""
    wanted = set(include)
    return [t for t in trades if strategy_key(t) in wanted]


def assemble(trades):
    """Metrica resumen de un conjunto de trades."""
    pf = profit_factor(trades)
    curve = equity_curve(trades)
    mdd, peak, trough = max_drawdown(curve)
    sh = sharpe_monthly(trades)
    n = len(trades)
    wins = sum(1 for t in trades if t["profit_abs"] >= 0)
    return {
        "n_trades": n,
        "win_pct": round(100 * wins / n, 1) if n else 0.0,
        "pf": round(pf, 3) if pf is not None else None,
        "max_drawdown_pct": round(mdd * 100, 2),
        "sharpe_annualized": round(sh, 3) if sh is not None else None,
        "net_pnl_usdt": round(sum(t["profit_abs"] for t in trades), 2),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", required=True)
    ap.add_argument("--include", nargs="*", default=None,
                    help="lista 'variant:pair' a incluir. Si se omite, usa --auto.")
    ap.add_argument("--auto", type=int, default=0,
                    help="top-N estrategias por PF (alternativa a --include).")
    ap.add_argument("--min-trades", type=int, default=30)
    ap.add_argument("--out", default=None, help="volcar resumen JSON a este path.")
    args = ap.parse_args()

    trades = load_trades(args.trades)
    if args.include:
        subset = build_portfolio(trades, args.include)
        label = "manual:" + ",".join(args.include)
    elif args.auto:
        ranked = select_strategies(trades, top_n=args.auto, min_trades=args.min_trades)
        subset = build_portfolio(trades, [k for k, _, _ in ranked])
        label = f"auto-top{args.auto}"
    else:
        subset = trades
        label = "all"

    summary = assemble(subset)
    corr = correlation_matrix(monthly_series(subset))

    print(f"\n=== FASE D — Portfolio: {label} ===")
    print(f"trades={summary['n_trades']} win%={summary['win_pct']} "
          f"PF={summary['pf']} maxDD%={summary['max_drawdown_pct']} "
          f"sharpe={summary['sharpe_annualized']} netPnL={summary['net_pnl_usdt']} USDT")

    strats = list(corr.keys())
    if strats:
        print("\n-- Correlacion de P&L mensual por estrategia (matriz triangular) --")
        for i, a in enumerate(strats):
            for b in strats[i + 1:]:
                r = corr[a][b]
                print(f"  {a:34} ~ {b:34} r={r if r is None else round(r, 3)}")

    out = {
        "label": label,
        "summary": summary,
        "correlation": {a: {b: (round(corr[a][b], 3) if corr[a][b] is not None else None)
                            for b in corr[a]} for a in corr},
        "n_strategies": len(strats),
    }
    if args.out:
        with open(args.out, "w") as fh:
            json.dump(out, fh, indent=2)
        print(f"[out] resumen -> {args.out}")
    return out


if __name__ == "__main__":
    main()
