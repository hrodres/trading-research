#!/usr/bin/env python3
"""Inspecciona la estructura real del export de freqtrade 2026.7 (zip auto-nombrado)."""
import zipfile, json

base = "/freqtrade/user_data/backtest_results/"
last = json.load(open(base + ".last_result.json"))
zpath = base + last["latest_backtest"]
print("LATEST ZIP:", last["latest_backtest"])
z = zipfile.ZipFile(zpath)
main = [n for n in z.namelist() if n.endswith(".json")
        and "config" not in n and "comparison" not in n]
print("MAIN JSON:", main)
d = json.loads(z.read(main[0]))
strat = d["strategy"]["BaselineTrend"]
print("STRAT keys:", sorted(strat.keys()))
for k in ["trades", "results_per_pair"]:
    if k in strat:
        v = strat[k]
        print(f"  {k}: type={type(v).__name__} len={len(v) if hasattr(v, '__len__') else '?'}")
rpp = strat.get("results_per_pair")
if rpp:
    print("PER-PAIR[0] keys:", sorted(rpp[0].keys()))
    print("PER-PAIR[0]:", {k: rpp[0][k] for k in rpp[0]
          if k in ("key", "trades", "profit_factor", "profit_total_abs", "wins", "losses")})
tr = strat.get("trades")
if tr:
    print("TRADE[0] keys:", sorted(tr[0].keys()))
    print("TRADE[0]:", {k: tr[0].get(k) for k in ("pair", "profit_abs", "profit_ratio") if k in tr[0]})
