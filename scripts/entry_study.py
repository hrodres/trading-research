#!/usr/bin/env python3
"""Fase B — Estudio de senales de ENTRADA (freqtrade como harness).

Mismo exit que el mejor de Fase C (dejar correr hasta EMA-cross + SL -10%,
sin TP fijo corto). Lo unico que varia es la ENTRADA. Corremos las 6 variants
en UNA pasada por ano via `--strategy-list`.

VARIANTS (ver strategies/entry_study.py) — ESTUDIO CANONICO Fase B (6 senales reales):
  EntryTrend     : EMA20>EMA50 (referencia)
  EntryTrendADX  : EMA20>EMA50 + ADX>25 (solo tendencia fuerte)
  EntryBreakout  : ruptura maximo 20v (Donchian)
  EntryPullback  : EMA20>EMA50 + pullback a EMA20 + RSI gira up
  EntryVolConfirm: EMA20>EMA50 + volumen > 1.5x media
  EntryMeanRev   : RSI<30 en rango (contra-tendencia, contraste)

NOTA FORENSE: `EntryV9Style` (estilo de entrada del bot v9) fue anadida a peticion
 del usuario (03:46 UTC) para cerrar una duda, y queda FUERA del estudio canonico.
 No forma parte de la busqueda de edge del proyecto. Si se quiere re-ejecutar como
 curiosidad, usar FORENSIC_VARIANTS = ["EntryV9Style"] y un backtest aparte; el
 resultado ya esta en results/entrystudy_v9style.json (casi inerte: 5 trades/5 anos, PF 0.0).

Metodo OOS: 5 ventanas anuales (2021-2025), 9 pares, sizing fijo 100 USDT,
fees 0.001. Sin fitting en IS -> todo OOS por construccion (evita overfit).

GATE (PROJECT.md): un (variant, par) pasa si PF_agregado >= 1.5 Y n >= 30 Y
historia larga (8 pares de ~4+ anos; XRP queda fuera por historia corta).
Reportamos tambien PF agregado POR VARIANT (todas las monedas) para ver cual
entrada es mejor en conjunto.
"""
import subprocess, json, os, zipfile
from collections import defaultdict

USERDIR = "/opt/freqtrade/user_data"
DATADIR = "/opt/freqtrade/user_data/data/coinbase"
CONFIG = "/opt/freqtrade/user_data/configs/backtest_entrystudy.json"
VARIANTS = ["EntryTrend", "EntryTrendADX", "EntryBreakout",
            "EntryPullback", "EntryVolConfirm", "EntryMeanRev"]
# FORENSIC_VARIANTS = ["EntryV9Style"]  # fuera del estudio canonico (ver nota arriba)
RESULTS_DIR = "/opt/freqtrade/user_data/backtest_results"
YEARS = [2021, 2022, 2023, 2024, 2025]
GATE_PF = 1.5
GATE_MIN_TRADES = 30
LONG_HISTORY = {"BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT",
                "DOT/USDT", "AVAX/USDT", "ADA/USDT", "LINK/USDT"}


def run_year(year):
    tr = f"{year}0101-{year}1231"
    cmd = ["freqtrade", "backtesting",
           "--userdir", USERDIR, "--datadir", DATADIR,
           "--config", CONFIG, "--strategy-list", *VARIANTS,
           "--timerange", tr, "--export", "trades"]
    print(f"[run] {year}", flush=True)
    subprocess.run(cmd, check=True)
    last = json.load(open(os.path.join(RESULTS_DIR, ".last_result.json")))
    zpath = os.path.join(RESULTS_DIR, last["latest_backtest"])
    z = zipfile.ZipFile(zpath)
    main = [n for n in z.namelist()
            if n.endswith(".json") and "config" not in n and "comparison" not in n][0]
    return json.loads(z.read(main))


def main():
    agg = defaultdict(lambda: defaultdict(lambda: {"gp": 0.0, "gl": 0.0, "n": 0,
                                                   "wins": 0, "by_year": defaultdict(lambda: {"gp": 0.0, "gl": 0.0, "n": 0})}))

    for year in YEARS:
        data = run_year(year)
        strat = data["strategy"]
        for variant in VARIANTS:
            trades = strat.get(variant, {}).get("trades", [])
            for t in trades:
                pair = t.get("pair")
                prof = t.get("profit_abs")
                if pair is None or prof is None:
                    continue
                b = agg[variant][pair]
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

    report = {}
    for variant in VARIANTS:
        vgp = vgl = vn = vwins = 0.0
        by_pair = {}
        for pair, b in agg[variant].items():
            pf = (b["gp"] / b["gl"]) if b["gl"] > 0 else None
            win = (b["wins"] / b["n"]) if b["n"] else 0.0
            long_hist = pair in LONG_HISTORY
            passes = (pf is not None and pf >= GATE_PF and b["n"] >= GATE_MIN_TRADES and long_hist)
            by_pair[pair] = {
                "gross_profit": round(b["gp"], 2), "gross_loss": round(b["gl"], 2),
                "n_trades": b["n"], "win_pct": round(win * 100, 1),
                "pf": round(pf, 3) if pf is not None else None,
                "long_history": long_hist, "passes_gate": passes,
                "by_year": {str(y): {"gp": round(v["gp"], 2), "gl": round(v["gl"], 2),
                                     "n": v["n"],
                                     "pf": round(v["gp"] / v["gl"], 3) if v["gl"] > 0 else None}
                            for y, v in b["by_year"].items()},
            }
            vgp += b["gp"]; vgl += b["gl"]; vn += b["n"]; vwins += b["wins"]
        vpf = (vgp / vgl) if vgl > 0 else None
        pairs_ok = sorted([p for p, r in by_pair.items() if r["passes_gate"]])
        best = max(by_pair.items(), key=lambda kv: (kv[1]["pf"] or 0))
        report[variant] = {
            "overall": {"gross_profit": round(vgp, 2), "gross_loss": round(vgl, 2),
                        "n_trades": int(vn), "win_pct": round(100 * vwins / vn, 1) if vn else 0,
                        "pf": round(vpf, 3) if vpf is not None else None},
            "best_pair": {"pair": best[0], "pf": best[1]["pf"]},
            "pairs_passing_gate": pairs_ok,
            "by_pair": by_pair,
        }

    out = {
        "method": "walk-forward anual 2021-2025, --strategy-list (6 entry variants, mismo exit de C), sizing fijo 100 USDT, sin fitting (OOS por construccion)",
        "gate": {"pf_min": GATE_PF, "min_trades": GATE_MIN_TRADES, "long_history_required": True},
        "variants": report,
        "best_overall_variant": max(report.items(), key=lambda kv: (kv[1]["overall"]["pf"] or 0))[0],
    }
    os.makedirs("/opt/freqtrade/user_data/results", exist_ok=True)
    with open("/opt/freqtrade/user_data/results/entrystudy_B.json", "w") as fh:
        json.dump(out, fh, indent=2)

    print("\n=== FASE B — PF agregado por VARIANT (todas las monedas, 2021-2025) ===")
    print(f"{'VARIANT':14} {'PF':>7} {'n':>5} {'win%':>6} {'best_pair':>10} {'PF_best':>8} {'#gate':>5}")
    for variant, r in sorted(report.items(), key=lambda kv: -(kv[1]["overall"]["pf"] or 0)):
        o = r["overall"]
        print(f"{variant:14} {str(o['pf']):>7} {o['n_trades']:>5} {o['win_pct']:>6} "
              f"{r['best_pair']['pair']:>10} {str(r['best_pair']['pf']):>8} {len(r['pairs_passing_gate']):>5}")

    print("\n=== Mejor PF por (variant, par) — top del estudio ===")
    rows = []
    for variant, r in report.items():
        for pair, pr in r["by_pair"].items():
            rows.append((variant, pair, pr["pf"], pr["n_trades"], pr["passes_gate"]))
    rows.sort(key=lambda x: -(x[2] or 0))
    print(f"{'VARIANT':14} {'PAR':10} {'PF':>7} {'n':>5} {'GATE':>6}")
    for variant, pair, pf, n, gate in rows[:14]:
        print(f"{variant:14} {pair:10} {str(pf):>7} {n:>5} {str(gate):>6}")


if __name__ == "__main__":
    main()
