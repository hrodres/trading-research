#!/usr/bin/env python3
"""Filtro de régimen global (meta-controlador, punto 1 del selector).

Regla DECLARADA A PRIORI (antes de mirar resultados, evita selection bias):
  - Proxy de régimen: BTC/USDT 2h (spot Coinbase, mismo datadir que los backtests).
  - Bull regime  <=>  close_BTC > SMA200(close_BTC, 2h)   (200 velas 2h ≈ 16.7 días)
  - La decisión en t usa SOLO la última vela BTC cerrada ANTES del open_date del
    trade (sin lookahead: bisect sobre fechas, sin datos futuros).
  - Con menos de 200 velas de historia (inicio del dataset) el régimen NO está
    definido -> se trata como no-bull (conservador: el selector no opera sin régimen
    calculable).

Aplica el filtro a los trades ya exportados de los 20 backtests B.2
(results/longcandidates/extracted/backtest-result-*/...json) y recalculan PF, win%,
n y profit con/sin filtro por (estrategia, ventana).

Salida:
  - stdout: tabla comparativa + veredicto
  - results/regime_filter_summary.csv  (evidencia agregada, sí se versiona)
"""
import csv
import json
import os
import sys
from bisect import bisect_left
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTRACTED = os.path.join(REPO, "results", "longcandidates", "extracted")
BTC_CSV = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "results", "btc_2h.csv")
OUT_CSV = os.path.join(REPO, "results", "regime_filter_summary.csv")
SMA_N = 200


# ── Dataset BTC (proxy de régimen) ────────────────────────────────────────────
def load_btc(path):
    """→ (list[datetime], list[float]) velas 2h ordenadas asc."""
    dates, closes = [], []
    with open(path) as f:
        for row in csv.DictReader(f):
            dates.append(datetime.fromisoformat(row["date"]).replace(tzinfo=timezone.utc))
            closes.append(float(row["close"]))
    return dates, closes


def sma_at(idx, closes, n):
    """Media de closes[idx-n+1 .. idx] (ventana estricta hacia atrás)."""
    if idx + 1 < n:
        return None
    return sum(closes[idx - n + 1: idx + 1]) / n


def build_regime(dates, closes, n=SMA_N):
    """→ list[bool|None]: bull[idx] = close > SMA200, None si historia insuficiente."""
    regime = []
    for i in range(len(closes)):
        s = sma_at(i, closes, n)
        regime.append(None if s is None else closes[i] > s)
    return regime


def regime_at(open_date, dates, regime):
    """Régimen vigente al abrir un trade: última vela BTC cerrada ANTES de open_date."""
    idx = bisect_left(dates, open_date) - 1  # última vela con date < open_date
    if idx < 0 or regime[idx] is None:
        return False  # régimen no definido -> no operar (conservador)
    return regime[idx]


# ── Trades de los backtests B.2 ───────────────────────────────────────────────
def iter_backtests():
    """Yields (estrategia, ventana, trade) de todos los JSON extraídos."""
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
    """PF, win%, n, profit sum, wins/losses brutos sobre una lista de trades."""
    if not trades:
        return dict(n=0, pf=float("nan"), win=0.0, profit=0.0, wins=0.0, losses=0.0)
    wins = sum(t["profit_abs"] for t in trades if t["profit_abs"] > 0)
    losses = -sum(t["profit_abs"] for t in trades if t["profit_abs"] <= 0)
    n = len(trades)
    win = 100.0 * sum(1 for t in trades if t["profit_abs"] > 0) / n
    return dict(n=n, pf=(wins / losses if losses > 0 else float("inf")),
                win=round(win, 1), profit=round(sum(t["profit_abs"] for t in trades), 2),
                wins=round(wins, 2), losses=round(losses, 2))


def main():
    dates, closes = load_btc(BTC_CSV)
    regime = build_regime(dates, closes)
    print(f"BTC: {len(closes)} velas {dates[0]} → {dates[-1]} (SMA{SMA_N} 2h, régimen "
          f"bull en {sum(1 for r in regime if r is True)} velas)")

    # Agrupar: (estrategia, ventana) → [trade, ...] con y sin filtro
    groups = {}
    for sname, ventana, t in iter_backtests():
        key = (sname, ventana)
        groups.setdefault(key, []).append(t)

    rows = []
    for (sname, ventana), trades in sorted(groups.items()):
        m_all = metrics(trades)
        kept = [t for t in trades
                if regime_at(datetime.fromisoformat(t["open_date"]), dates, regime)]
        m_f = metrics(kept)
        rows.append({
            "estrategia": sname, "ventana": ventana,
            "n_all": m_all["n"], "n_bull": m_f["n"],
            "pf_all": round(m_all["pf"], 3) if m_all["pf"] != float("inf") else "inf",
            "pf_bull": round(m_f["pf"], 3) if m_f["pf"] != float("inf") else "inf",
            "win_all": m_all["win"], "win_bull": m_f["win"],
            "profit_all": m_all["profit"], "profit_bull": m_f["profit"],
            "wins_all": m_all["wins"], "losses_all": m_all["losses"],
            "wins_bull": m_f["wins"], "losses_bull": m_f["losses"],
        })

    # Salida CSV
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Tabla
    print(f"\n{'Estrategia':<16}{'Ventana':<22}{'n':>5}{'PF all':>8}{'PF bull':>9}"
          f"{'winA':>7}{'winB':>7}{'profA':>9}{'profB':>9}")
    for r in rows:
        print(f"{r['estrategia']:<16}{r['ventana']:<22}{r['n_all']:>5}"
              f"{str(r['pf_all']):>8}{str(r['pf_bull']):>9}"
              f"{r['win_all']:>7}{r['win_bull']:>7}"
              f"{r['profit_all']:>9}{r['profit_bull']:>9}")

    # Resumen por estrategia: mediana PF, PF AGREGADO (suma wins/losses) y nº ventanas
    print("\n=== Resumen por estrategia (con filtro bull) ===")
    from collections import defaultdict
    by_s = defaultdict(list)
    agg = defaultdict(lambda: dict(w=0.0, l=0.0, wa=0.0, la=0.0))
    for r in rows:
        pf = r["pf_bull"]
        by_s[r["estrategia"]].append(pf if pf != "inf" else float("nan"))
        a = agg[r["estrategia"]]
        a["w"] += r["wins_all"]; a["l"] += r["losses_all"]
        a["wa"] += r["wins_bull"]; a["la"] += r["losses_bull"]
    for s, pfs in sorted(by_s.items()):
        valid = [p for p in pfs if p == p]
        if not valid:
            continue
        med = sorted(valid)[len(valid) // 2]
        gt1 = sum(1 for p in valid if p > 1)
        gt15 = sum(1 for p in valid if p >= 1.5)
        a = agg[s]
        pfA = a["w"] / a["l"] if a["l"] > 0 else float("inf")
        pfB = a["wa"] / a["la"] if a["la"] > 0 else float("inf")
        print(f"{s:<16} mediana PF_bull={med:<6} PF>1: {gt1}/{len(valid)}  PF≥1.5: {gt15}/{len(valid)}"
              f"  |  PF AGREGADO: all={pfA:.3f} bull={pfB:.3f}")

    print(f"\nCSV guardado: {OUT_CSV}")


if __name__ == "__main__":
    main()
