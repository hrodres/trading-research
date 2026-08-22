#!/usr/bin/env python3
"""Selector v1 — primer meta-controlador walk-forward honesto (visión del proyecto).

Reglas declaradas A PRIORI (antes de ver resultados, sin selection bias):
  - Pool de candidatos LONG: las 4 estrategias de B.2
    (AtrSlLong, PartialtpLong, RotationLong, VolBreakoutLong).
  - Componente 1 — RÉGIMEN (validado en B.3): solo se opera long en bull
    (close BTC/USDT 2h > SMA200 ≈ 16.7 días; decisión en t solo velas ≤ t;
    régimen indefinido = no operar). Sin lookahead.
  - Componente 2 — SELECCIÓN walk-forward 1-lookback: la estrategia activa en
    la ventana w es la de mayor PF AGREGADO (en bull, con datos ≤ fin de w-1)
    de la ventana anterior. PRIMERA ventana (sin historial): no hay selección
    posible -> se opera el POOL COMPLETO (ensemble: señal si cualquier
    estrategia del pool la da), regla conservadora documentada.
  - Componente 3 — CARRY (validado en D.2): long spot + short perp 1:1
    (Binance funding público), activo solo en bull, mismo régimen sin lookahead.

Métrica (gate del proyecto): PF del PROCESO DE SELECCIÓN por ventana y
agregado (PF ≥ 1.5 OOS). Se reporta:
  - PF_long   : solo longs del selector (régimen + selección WF)
  - PF_carry  : solo carry en bull (referencia D.2)
  - PF_proceso: combinado (misma unidad: profit_ratio % por long,
                rate % por evento carry; caveat de escala documentado)

Benchmarks de diagnóstico (NO permitidos en producción, solo contexto):
  - pool completo sin selección ni régimen (¿qué aporta seleccionar?)
  - mejor estrategia fija (miraría el futuro -> solo referencia del techo)

Uso:
  python3 scripts/selector_v1.py
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))
import regime_filter as rf  # noqa: E402
import carry_regime as cr   # noqa: E402  (regime_at_ts, SYM2PAIR, FEE_RATE)

EXTRACTED = os.path.join(REPO, "results", "longcandidates", "extracted")
BTC_CSV = os.path.join(REPO, "results", "btc_2h.csv")
RAW_PATH = os.path.join(REPO, "results", "funding_raw.json")
OUT_CSV = os.path.join(REPO, "results", "selector_v1_summary.csv")

# Ventanas en orden cronológico (las 5 de B.2)
WINDOWS = ["20210101-20211231", "20220101-20221231", "20230101-20231231",
           "20240101-20241231", "20250101-20260601"]
POOL = ["AtrSlLong", "PartialtpLong", "RotationLong", "VolBreakoutLong"]


def load_trades_by_window():
    """→ {ventana: {estrategia: [trades]}} leyendo los JSONs extraídos de B.2."""
    out = {w: defaultdict(list) for w in WINDOWS}
    for d in sorted(os.listdir(EXTRACTED)):
        dpath = os.path.join(EXTRACTED, d)
        if not os.path.isdir(dpath):
            continue
        jpath = next((os.path.join(dpath, p) for p in os.listdir(dpath)
                      if p.endswith(".json") and "config" not in p), None)
        if not jpath:
            continue
        with open(jpath) as fh:
            data = json.load(fh)
        for sname, sdata in data.get("strategy", {}).items():
            window = str(sdata.get("timerange", "?"))
            if window not in out:
                continue
            out[window][sname] = sdata.get("trades", [])
    return out


def pf_of(trades, use_ratio=False):
    """PF agregado (portfolio de los trades) y P&L por unidad."""
    if not trades:
        return None, 0.0, 0.0, 0
    vals = [t["profit_ratio"] if use_ratio else t["profit_abs"] for t in trades]
    gp = sum(v for v in vals if v > 0)
    gl = sum(-v for v in vals if v < 0)
    n = len(vals)
    return ((gp / gl) if gl > 0 else float("inf")), gp, gl, n


def main():
    # 1) Lookup de régimen GLOBAL (BTC)
    lu = rf.make_lookup(rf.load_regular_csv(BTC_CSV))
    g_dates, _cls, g_regime = lu["GLOBAL"]

    # 2) Trades B.2 + funding raw
    by_window = load_trades_by_window()
    with open(RAW_PATH) as fh:
        raw = json.load(fh)

    # 3) Selección walk-forward: mejor PF agregado (bull) de la ventana anterior
    prev_best = None  # estrategia elegida para la ventana actual
    # PF en bull de cada estrategia en la ventana anterior (para elegir)
    prev_pf_bull = {}
    rows = []
    agg = {k: [0.0, 0.0, 0] for k in ("long", "long_all", "carry", "proceso")}

    def _is_bull(t):
        dt = datetime.fromisoformat(t["open_date"])
        return rf.regime_at(dt, g_dates, g_regime)

    for w in WINDOWS:
        trades_w = by_window.get(w, {})
        # ---- LONG: selección + régimen ----
        if prev_best is None:
            # Primera ventana: ensemble del pool completo (solo bull)
            sel_trades = []
            for s in POOL:
                sel_trades += [t for t in trades_w.get(s, []) if _is_bull(t)]
            note = "pool (ensemble, sin historial)"
        else:
            sel_trades = [t for t in trades_w.get(prev_best, []) if _is_bull(t)]
            note = f"WF 1-lookback → {prev_best}"
        pf_l, gp_l, gl_l, n_l = pf_of(sel_trades, use_ratio=True)
        # referencia: pool sin régimen
        ref_trades = [t for s in POOL for t in trades_w.get(s, [])]
        pf_r, gp_r, gl_r, n_r = pf_of(ref_trades, use_ratio=True)

        # ---- CARRY en bull (misma ventana) ----
        car_cf = []
        for sym, series in raw.items():
            for ts, rate in series:
                yr = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).year
                ystr = f"{yr}0101-{yr}1231"
                if ystr == w or (yr == 2025 and w.startswith("2025")):
                    if cr.regime_at_ts(ts, g_dates, g_regime) is True:
                        car_cf.append(rate)
        gp_c = sum(c for c in car_cf if c > 0)
        gl_c = sum(-c for c in car_cf if c < 0)
        pf_c = (gp_c / gl_c) if gl_c > 0 else float("inf")
        n_c = len(car_cf)

        # ---- PROCESO combinado (long % + carry %) ----
        all_pos = (gp_l + gp_c)
        all_neg = (gl_l + gl_c)
        pf_p = (all_pos / all_neg) if all_neg > 0 else float("inf")

        rows.append({"ventana": w, "seleccion": note, "n_long": n_l,
                     "pf_long": (round(pf_l, 3) if pf_l is not None and pf_l == pf_l else "NaN"),
                     "pf_pool_sin_regimen": (round(pf_r, 3) if pf_r is not None and pf_r == pf_r else "NaN"),
                     "n_carry": n_c, "pf_carry": (round(pf_c, 3) if pf_c is not None else "NaN"),
                     "pf_proceso": (round(pf_p, 3) if pf_p is not None else "NaN")})
        for k, (gp, gl, n) in (("long", (gp_l, gl_l, n_l)),
                               ("long_all", (gp_r, gl_r, n_r)),
                               ("carry", (gp_c, gl_c, n_c))):
            agg[k][0] += gp
            agg[k][1] += gl
            agg[k][2] += n
        agg["proceso"][0] += all_pos
        agg["proceso"][1] += all_neg
        agg["proceso"][2] += (n_l + n_c) if n_l or n_c else 0

        # actualizar mejor PF bull de la ventana para la selección siguiente
        pfs = {}
        for s in POOL:
            bt = [t for t in trades_w.get(s, []) if _is_bull(t)]
            p, _g, _l, _n = pf_of(bt, use_ratio=True)
            if p is not None and p != float("inf") and bt:
                pfs[s] = p
        if pfs:
            prev_best = max(pfs, key=pfs.get)

    # ---- Resumen ----
    print(f"{'ventana':<22}{'selección':<34}{'nL':>5}{'PFL':>8}{'PFRaw':>8}{'nC':>7}{'PFC':>8}{'PFproc':>9}")
    for r in rows:
        print(f"{r['ventana']:<22}{r['seleccion']:<34}{r['n_long']:>5}"
              f"{str(r['pf_long']):>8}{str(r['pf_pool_sin_regimen']):>8}{r['n_carry']:>7}"
              f"{str(r['pf_carry']):>8}{str(r['pf_proceso']):>9}")

    print("\n=== AGREGADO (gate del proceso: PF ≥ 1.5 OOS) ===")
    for k, label in (("long", "selector LONG (régimen+WF)"),
                     ("long_all", "pool completo sin régimen (benchmark)"),
                     ("carry", "CARRY en bull"),
                     ("proceso", "PROCESO completo (long+carry)")):
        gp, gl, n = agg[k]
        pf = (gp / gl) if gl > 0 else float("inf")
        print(f"  {label:<38} n={n:>6}  PF={pf:.3f}")

    with open(OUT_CSV, "w", newline="") as fh:
        import csv
        wcsv = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wcsv.writeheader()
        wcsv.writerows(rows)
    print(f"\nCSV -> {OUT_CSV}")


if __name__ == "__main__":
    main()
