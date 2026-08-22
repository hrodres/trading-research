#!/usr/bin/env python3
"""Fase A.3 — Walk-forward OOS por par (freqtrade como harness).

Valida BaselineTrend fuera de muestra, POR PAR, en ventanas anuales
(2021-2025). Sizing ACOTADO (stake fijo 100 USDT) -> el PF es honesto
(sin el artefacto de drawdown por sizing 100% que vimos en A.2).

freqtrade 2026.7 exporta a un zip auto-nombrado; su contenido principal
tiene d["strategy"]["BaselineTrend"]["trades"] (lista con pair, profit_abs).
Leemos eso inmediatamente tras cada año (el .last_result.json apunta al zip
mas reciente) para no depender de nombres de archivo.

GATE (PROJECT.md): un par pasa si PF_agregado >= 1.5 Y n_trades >= 30 Y
historia larga (BTC/ETH/SOL/DOGE/DOT/AVAX/ADA/LINK). XRP (desde 2023-07)
se reporta pero queda fuera del gate de historia.

NO se ajusta ningun parametro en IS -> toda la ventana es OOS valido por
construccion (no hubo fitting). Esto evita overfit.
"""
import subprocess, json, os, zipfile
from collections import defaultdict

USERDIR = "/freqtrade/user_data"
DATADIR = "/freqtrade/user_data/data/coinbase"
CONFIG = "/freqtrade/user_data/configs/backtest_walkforward.json"
STRATEGY = "BaselineTrend"
RESULTS_DIR = "/freqtrade/user_data/backtest_results"
YEARS = [2021, 2022, 2023, 2024, 2025]
GATE_PF = 1.5
GATE_MIN_TRADES = 30
# Pares con ~4+ anos de datos (cumplen gate de historia del PROJECT.md)
LONG_HISTORY = {"BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT",
                "DOT/USDT", "AVAX/USDT", "ADA/USDT", "LINK/USDT"}


def run_year(year):
    tr = f"{year}0101-{year}1231"
    cmd = ["freqtrade", "backtesting",
           "--userdir", USERDIR, "--datadir", DATADIR,
           "--config", CONFIG, "--strategy", STRATEGY,
           "--timerange", tr, "--export", "trades"]
    print(f"[run] {year}", flush=True)
    subprocess.run(cmd, check=True)
    # leer el zip mas reciente apuntado por .last_result.json
    last = json.load(open(os.path.join(RESULTS_DIR, ".last_result.json")))
    zpath = os.path.join(RESULTS_DIR, last["latest_backtest"])
    z = zipfile.ZipFile(zpath)
    main = [n for n in z.namelist()
            if n.endswith(".json") and "config" not in n and "comparison" not in n][0]
    d = json.loads(z.read(main))
    return d["strategy"][STRATEGY]["trades"]


def main():
    agg = defaultdict(lambda: {"gp": 0.0, "gl": 0.0, "n": 0, "wins": 0,
                               "by_year": defaultdict(lambda: {"gp": 0.0, "gl": 0.0, "n": 0})})
    per_year = {}
    for year in YEARS:
        trades = run_year(year)
        gp_y = gl_y = n_y = 0.0
        for t in trades:
            pair = t.get("pair")
            prof = t.get("profit_abs")
            if pair is None or prof is None:
                continue
            b = agg[pair]
            b["n"] += 1
            if prof >= 0:
                b["gp"] += prof
                b["wins"] += 1
            else:
                b["gl"] += -prof
            yb = b["by_year"][year]
            yb["n"] += 1
            if prof >= 0:
                yb["gp"] += prof
            else:
                yb["gl"] += -prof
            gp_y += max(prof, 0.0)
            gl_y += max(-prof, 0.0)
            n_y += 1
        per_year[year] = {"gp": round(gp_y, 2), "gl": round(gl_y, 2), "n": int(n_y),
                          "pf": round(gp_y / gl_y, 3) if gl_y > 0 else None}

    report = {}
    for pair, b in agg.items():
        pf = (b["gp"] / b["gl"]) if b["gl"] > 0 else None
        win = (b["wins"] / b["n"]) if b["n"] else 0.0
        long_hist = pair in LONG_HISTORY
        passes = (pf is not None and pf >= GATE_PF and b["n"] >= GATE_MIN_TRADES and long_hist)
        report[pair] = {
            "gross_profit": round(b["gp"], 2), "gross_loss": round(b["gl"], 2),
            "n_trades": b["n"], "win_pct": round(win * 100, 1),
            "pf": round(pf, 3) if pf is not None else None,
            "long_history": long_hist, "passes_gate": passes,
            "by_year": {str(y): {"gp": round(v["gp"], 2), "gl": round(v["gl"], 2),
                                 "n": v["n"],
                                 "pf": round(v["gp"] / v["gl"], 3) if v["gl"] > 0 else None}
                         for y, v in b["by_year"].items()},
        }

    out = {
        "method": "walk-forward anual 2021-2025, sizing fijo 100 USDT, sin fitting (OOS por construccion)",
        "strategy": STRATEGY,
        "gate": {"pf_min": GATE_PF, "min_trades": GATE_MIN_TRADES, "long_history_required": True},
        "per_year_allpairs": per_year,
        "by_pair": report,
        "pairs_passing_gate": sorted([p for p, r in report.items() if r["passes_gate"]]),
    }
    os.makedirs("/freqtrade/user_data/results", exist_ok=True)
    with open("/freqtrade/user_data/results/walkforward_A3.json", "w") as fh:
        json.dump(out, fh, indent=2)

    print("\n=== WALK-FORWARD A.3 — PF por par (agregado 2021-2025) ===")
    print(f"{'PAR':10} {'PF':>7} {'n':>5} {'win%':>6} {'4+yr':>5} {'GATE':>6}")
    for pair in sorted(report, key=lambda p: -(report[p]["pf"] or 0)):
        r = report[pair]
        print(f"{pair:10} {str(r['pf']):>7} {r['n_trades']:>5} {r['win_pct']:>6} "
              f"{str(r['long_history']):>5} {str(r['passes_gate']):>6}")
    print(f"\nPares que pasan el gate: {out['pairs_passing_gate']}")


if __name__ == "__main__":
    main()
