#!/usr/bin/env python3
"""Analiza los resultados de backtests de long-candidates (4 estrategias x 5 ventanas).

Lee los JSON completos exportados por freqtrade (results/longcandidates/extracted/),
extrae metricas por estrategia/ventana y genera:
  - results/longcandidates_summary.csv
  - tabla markdown por consola
  - resumen por estrategia (estabilidad OOS: PF medio/mediana/min, DD max)
"""
import csv
import glob
import json
import os
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTED = os.path.join(ROOT, "results", "longcandidates", "extracted")
OUT_CSV = os.path.join(ROOT, "results", "longcandidates_summary.csv")

WINDOWS = {
    "20210101-20211231": "2021",
    "20220101-20221231": "2022",
    "20230101-20231231": "2023",
    "20240101-20241231": "2024",
    "20250101-20260601": "2025-26",
}


def load_results():
    rows = []
    files = sorted(glob.glob(os.path.join(EXTRACTED, "*", "backtest-result-*.json")))
    if not files:
        raise SystemExit(f"No hay JSON en {EXTRACTED}")
    for f in files:
        with open(f) as fh:
            d = json.load(fh)
        # Cada zip = 1 estrategia x 1 ventana; el timerange vive en strategy[<nombre>]
        strat_inner = d.get("strategy") or {}
        # strategy_comparison: 1 entrada x estrategia (solo hay 1 por archivo)
        cmp = d.get("strategy_comparison") or []
        for s in cmp:
            name = s.get("key")
            if not name or name == "TOTAL" or name not in strat_inner:
                continue
            trange = strat_inner.get(name, {}).get("timerange", "") or s.get("timerange", "")
            rows.append(
                {
                    "strategy": name,
                    "window_key": trange,
                    "window": WINDOWS.get(trange, trange),
                    "trades": s.get("trades", 0),
                    "profit_total_pct": s.get("profit_total_pct", 0.0),
                    "profit_total_abs": s.get("profit_total_abs", 0.0),
                    "winrate": s.get("winrate", 0.0),
                    "profit_factor": s.get("profit_factor"),
                    "expectancy": s.get("expectancy", 0.0),
                    "sharpe": s.get("sharpe"),
                    "sortino": s.get("sortino"),
                    "calmar": s.get("calmar"),
                    "sqn": s.get("sqn"),
                    "p_value": s.get("p_value"),
                    "max_dd_pct": s.get("max_drawdown_account", 0.0) * 100,
                    "max_dd_abs": s.get("max_drawdown_abs", 0.0),
                    "cagr": s.get("cagr", 0.0),
                }
            )
    if not rows:
        raise SystemExit("strategy_comparison vacio en todos los JSON")
    return rows


def fmt(v, nd=2):
    if v is None:
        return "-"
    try:
        fv = float(v)
    except (TypeError, ValueError):
        return str(v)
    return f"{fv:.{nd}f}"


def main():
    rows = load_results()
    # CSV
    with open(OUT_CSV, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Tabla markdown
    print("### Resumen por estrategia x ventana")
    print(f"| Estrategia | Ventana | Trades | PF | Win% | Profit% | DD max% | Sharpe | SQN |")
    print(f"|---|---|---|---|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: (x["strategy"], x["window_key"])):
        pf = fmt(r["profit_factor"])
        print(
            f"| {r['strategy']} | {r['window']} | {r['trades']} | {pf} | "
            f"{r['winrate']*100:.1f} | {r['profit_total_pct']:.2f} | "
            f"{r['max_dd_pct']:.2f} | {fmt(r['sharpe'])} | {fmt(r['sqn'])} |"
        )

    # Estabilidad por estrategia (OOS)
    print("\n### Estabilidad OOS por estrategia (5 ventanas)")
    print("| Estrategia | Ventanas PF>1 | PF mediana | PF media | PF min | PF max | DD max% peor |")
    print("|---|---|---|---|---|---|---|")
    by_strat = {}
    for r in rows:
        by_strat.setdefault(r["strategy"], []).append(r)
    for name in sorted(by_strat):
        rs = by_strat[name]
        pfs = [r["profit_factor"] for r in rs if r["profit_factor"] is not None]
        dds = [r["max_dd_pct"] for r in rs]
        n_ok = sum(1 for p in pfs if p and p > 1.0)
        med = statistics.median(pfs) if pfs else 0.0
        avg = statistics.mean(pfs) if pfs else 0.0
        print(
            f"| {name} | {n_ok}/5 | {med:.2f} | {avg:.2f} | {min(pfs):.2f} | {max(pfs):.2f} | {max(dds):.2f} |"
        )

    print(f"\nCSV guardado: {OUT_CSV}")


if __name__ == "__main__":
    main()
