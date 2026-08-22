#!/usr/bin/env python3
"""Filtro de régimen (meta-controlador, componente 1 del selector).

Regla DECLARADA A PRIORI (antes de mirar resultados, evita selection bias):
  - Proxy de régimen, dos modos:
      GLOBAL : bull regime <=> close BTC/USDT 2h > SMA200  (proxy de mercado)
      PERPAR : bull regime <=> close <PROPIO PAR>/USDT 2h > SMA200
  - SMA200 en velas 2h ≈ 16.7 días. Decisión en t usa SOLO la última vela cerrada
    ANTES del open_date del trade (bisect sobre fechas, sin lookahead).
  - Con menos de 200 velas de historia el régimen NO está definido -> no operar
    (conservador).

Aplica el filtro a los trades ya exportados de los 20 backtests B.2
(results/longcandidates/extracted/backtest-result-*/...json) y compara
PF agregado (suma wins/losses) y por ventana: sin filtro vs global vs per-par.

Salida:
  - stdout: tabla comparativa + veredicto
  - results/regime_filter_summary.csv  (evidencia agregada, se versiona)
"""
import argparse
import csv
import json
import os
import sys
from bisect import bisect_left
from collections import defaultdict
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTED = os.path.join(REPO, "results", "longcandidates", "extracted")
SMA_N = 200


# ── Datasets ──────────────────────────────────────────────────────────────────
def load_regular_csv(path, pair_col=None):
    """→ list[(datetime, str, float)] (fecha aware UTC, pair|None, close)."""
    rows = []
    with open(path) as f:
        for r in csv.DictReader(f):
            dt = datetime.fromisoformat(r["date"]).replace(tzinfo=timezone.utc)
            p = r[pair_col] if pair_col else None
            rows.append((dt, p, float(r["close"])))
    return rows


def build_regime(closes, n=SMA_N):
    """→ list[bool|None]: bull[i] = close[i] > SMA(n) hasta i (sin lookahead)."""
    regime, acc = [], 0.0
    for i in range(len(closes)):
        acc += closes[i]
        if i >= n:
            acc -= closes[i - n]
        if i + 1 < n:
            regime.append(None)
        else:
            regime.append(closes[i] > acc / n)
    return regime


def make_lookup(rows):
    """→ dict[pair|'GLOBAL'] = (dates, closes, regime)."""
    by = defaultdict(list)
    for dt, p, close in rows:
        by[p if p else "GLOBAL"].append((dt, close))
    out = {}
    for k, pairs in by.items():
        pairs.sort()
        dates = [dt for dt, _ in pairs]
        closes = [c for _, c in pairs]
        out[k] = (dates, closes, build_regime(closes))
    return out


def regime_at(open_date, dates, regime):
    """Régimen vigente al abrir: última vela cerrada ANTES del open_date."""
    idx = bisect_left(dates, open_date) - 1
    if idx < 0 or regime[idx] is None:
        return False  # régimen no definido -> no operar (conservador)
    return regime[idx]


# ── Trades B.2 ────────────────────────────────────────────────────────────────
def iter_backtests():
    """Yields (estrategia, ventana, trade)."""
    for d in sorted(os.listdir(EXTRACTED)):
        dpath = os.path.join(EXTRACTED, d)
        if not os.path.isdir(dpath):
            continue
        jpath = next(
            (os.path.join(dpath, p) for p in os.listdir(dpath)
             if p.endswith(".json") and "config" not in p),
            None,
        )
        if not jpath:
            continue
        with open(jpath) as f:
            data = json.load(f)
        for sname, sdata in data.get("strategy", {}).items():
            ventana = str(sdata.get("timerange", "?"))
            for t in sdata.get("trades", []):
                yield sname, ventana, t


# ── Métricas ──────────────────────────────────────────────────────────────────
def metrics(trades):
    if not trades:
        return dict(n=0, pf=float("nan"), win=0.0, profit=0.0, wins=0.0, losses=0.0)
    wins = sum(t["profit_abs"] for t in trades if t["profit_abs"] > 0)
    losses = -sum(t["profit_abs"] for t in trades if t["profit_abs"] <= 0)
    return dict(
        n=len(trades),
        pf=(wins / losses if losses > 0 else float("inf")),
        win=round(100.0 * sum(1 for t in trades if t["profit_abs"] > 0) / len(trades), 1),
        profit=round(sum(t["profit_abs"] for t in trades), 2),
        wins=round(wins, 2),
        losses=round(losses, 2),
    )


def fmt_pf(x):
    return "inf" if x == float("inf") else (round(x, 3) if x == x else "NaN")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--btc", default=os.path.join(REPO, "results", "btc_2h.csv"))
    ap.add_argument("--pairs", default=os.path.join(REPO, "results", "pairs_2h.csv"))
    ap.add_argument("--out", default=os.path.join(REPO, "results", "regime_filter_summary.csv"))
    args = ap.parse_args()

    global_lu = make_lookup(load_regular_csv(args.btc)) if os.path.exists(args.btc) else None
    perpar_lu = make_lookup(load_regular_csv(args.pairs, pair_col="pair")) if os.path.exists(args.pairs) else None
    if global_lu:
        print(f"GLOBAL: BTC {len(global_lu['GLOBAL'][1])} velas, bull en "
              f"{sum(1 for r in global_lu['GLOBAL'][2] if r is True)}")
    if perpar_lu:
        print(f"PERPAR: {len(perpar_lu)} pares cargados "
              f"({min(len(v[1]) for v in perpar_lu.values())}-{max(len(v[1]) for v in perpar_lu.values())} velas)")

    groups = defaultdict(list)
    for sname, ventana, t in iter_backtests():
        groups[(sname, ventana)].append(t)

    rows = []
    for (sname, ventana), trades in sorted(groups.items()):
        m_all = metrics(trades)
        if global_lu:
            dts, cls, reg = global_lu["GLOBAL"]
            kept_g = [t for t in trades
                      if regime_at(datetime.fromisoformat(t["open_date"]), dts, reg)]
            m_g = metrics(kept_g)
        else:
            m_g = m_all
        if perpar_lu:
            kept_p = []
            for t in trades:
                key = t["pair"]
                if key not in perpar_lu:
                    continue  # par sin klines -> no operar
                dts, cls, reg = perpar_lu[key]
                if regime_at(datetime.fromisoformat(t["open_date"]), dts, reg):
                    kept_p.append(t)
            m_p = metrics(kept_p)
        else:
            m_p = m_all
        rows.append({
            "estrategia": sname, "ventana": ventana,
            "n_all": m_all["n"], "n_global": m_g["n"], "n_perpar": m_p["n"],
            "pf_all": fmt_pf(m_all["pf"]), "pf_global": fmt_pf(m_g["pf"]),
            "pf_perpar": fmt_pf(m_p["pf"]),
            "win_all": m_all["win"], "win_global": m_g["win"], "win_perpar": m_p["win"],
            "profit_all": m_all["profit"], "profit_global": m_g["profit"],
            "profit_perpar": m_p["profit"],
            "wins_all": m_all["wins"], "losses_all": m_all["losses"],
            "wins_global": m_g["wins"], "losses_global": m_g["losses"],
            "wins_perpar": m_p["wins"], "losses_perpar": m_p["losses"],
        })

    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    hdr = (f"{'Estrategia':<16}{'Ventana':<22}{'n':>5}{'PF all':>8}{'PF glob':>9}"
           f"{'PF par':>9}{'profA':>9}{'profG':>9}{'profP':>9}")
    print("\n" + hdr)
    for r in rows:
        print(f"{r['estrategia']:<16}{r['ventana']:<22}{r['n_all']:>5}"
              f"{str(r['pf_all']):>8}{str(r['pf_global']):>9}{str(r['pf_perpar']):>9}"
              f"{r['profit_all']:>9}{r['profit_global']:>9}{r['profit_perpar']:>9}")

    # Resumen por estrategia: PF agregado (gate del proceso) en las 3 variantes
    print("\n=== PF AGREGADO por estrategia (gate del proceso) ===")
    agg = defaultdict(lambda: dict(a=[0.0, 0.0], g=[0.0, 0.0], p=[0.0, 0.0]))
    for r in rows:
        A = agg[r["estrategia"]]
        A["a"][0] += r["wins_all"]; A["a"][1] += r["losses_all"]
        A["g"][0] += r["wins_global"]; A["g"][1] += r["losses_global"]
        A["p"][0] += r["wins_perpar"]; A["p"][1] += r["losses_perpar"]
    for s, A in sorted(agg.items()):
        pf = lambda v: v[0] / v[1] if v[1] > 0 else float("inf")  # noqa: E731
        print(f"{s:<16} all={pf(A['a']):.3f}  global={pf(A['g']):.3f}  perpar={pf(A['p']):.3f}")

    # Ventanas ganadoras per-par
    print("\n=== ventanas PF per-par > 1 / >= 1.5 ===")
    by_s = defaultdict(list)
    for r in rows:
        p = r["pf_perpar"]
        by_s[r["estrategia"]].append(p if p not in ("inf", "NaN") else float("nan"))
    for s, pfs in sorted(by_s.items()):
        valid = [p for p in pfs if p == p]
        if not valid:
            continue
        med = sorted(valid)[len(valid) // 2]
        gt1 = sum(1 for p in valid if p > 1)
        gt15 = sum(1 for p in valid if p >= 1.5)
        print(f"{s:<16} mediana PF_perpar={med:.3f}  PF>1: {gt1}/{len(valid)}  PF>=1.5: {gt15}/{len(valid)}")

    print(f"\nCSV guardado: {args.out}")


if __name__ == "__main__":
    main()
