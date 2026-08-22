#!/usr/bin/env python3
"""Tests de Fase D (carry) — scripts/carry_backtest.py.

Validan la logica de la simulacion de funding carry SIN credenciales:
- Convencion de signo: SHORT perp COBRA funding positivo (regresion del bug
  que tuvo el proyecto: se habia modelado con signo invertido, dando PF<1 falso).
- PF de la corriente de funding = GP/GL.
- Equity curva y max DD sobre capital real (notional + P&L).
- yearly_pf agrega por ano.
"""
import importlib.util
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

spec = importlib.util.spec_from_file_location("carry_backtest", os.path.join(REPO, "scripts", "carry_backtest.py"))
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)


def mk(rate, ts=1_609_459_200_000):
    return (ts, rate)


def test_short_perp_receives_positive_funding():
    """Bug de signo: SHORT perp debe COBRAR rate>0 (cashflow positivo)."""
    res = cb.simulate_carry([mk(0.01), mk(0.02)], fee_rate=0.0)
    # cashflows = +rate*notional -> todos positivos
    assert res["gross_loss"] == 0.0
    assert res["gross_profit"] > 0.0
    assert res["pf"] is None  # sin perdidas -> PF None (no division)


def test_long_implicit_would_pay_positive_funding():
    """Comprobacion de la convencion opuesta: si fuera LONG, pagaria (cashflow neg).
    Usamos la misma funcion pero el signo de la estrategia se modela en el caller;
    aqui verificamos que la pata SHORT (base del carry) es la que da cashflow +."""
    res = cb.simulate_carry([mk(0.01)], fee_rate=0.0)
    # SHORT: cashflow = +rate = +0.01 -> profit, no loss
    assert res["gross_profit"] == pytest.approx(0.01, abs=1e-9)
    assert res["gross_loss"] == 0.0


def test_pf_calculation_mixed_funding():
    # 3 eventos positivos, 1 negativo. GP=0.01+0.02+0.03=0.06, GL=0.05
    series = [mk(0.01), mk(0.02), mk(-0.05), mk(0.03)]
    res = cb.simulate_carry(series, fee_rate=0.0)
    assert res["gross_profit"] == pytest.approx(0.06, abs=1e-9)
    assert res["gross_loss"] == pytest.approx(0.05, abs=1e-9)
    assert res["pf"] == pytest.approx(0.06 / 0.05, abs=1e-9)
    assert res["net_pnl"] == pytest.approx(0.01, abs=1e-9)  # sin fees


def test_fees_reduce_net_pnl():
    series = [mk(0.01), mk(0.02)]
    no_fee = cb.simulate_carry(series, fee_rate=0.0)
    with_fee = cb.simulate_carry(series, fee_rate=0.001)
    assert with_fee["net_pnl"] < no_fee["net_pnl"]
    # fee round-trip = 4 laminas * 0.001 = 0.004
    assert no_fee["net_pnl"] - with_fee["net_pnl"] == pytest.approx(0.004, abs=1e-9)


def test_max_drawdown_over_real_equity():
    # sube y baja: notional=1. cashflows: +0.1, +0.1, -0.15, +0.05
    series = [mk(0.1, 1), mk(0.1, 2), mk(-0.15, 3), mk(0.05, 4)]
    res = cb.simulate_carry(series, fee_rate=0.0)
    # equity: 1.1, 1.2, 1.05, 1.10 -> peak 1.2, trough 1.05 -> DD 12.5%
    assert res["max_drawdown_pct"] == pytest.approx(12.5, abs=0.1)


def test_yearly_pf_groups_by_year():
    # 2021 un rate positivo, 2022 un rate negativo
    s21 = mk(0.01, 1_609_459_200_000)      # 2021
    s22 = mk(-0.02, 1_641_099_600_000)     # 2022
    out = cb.yearly_pf({"X": [s21, s22]}, fee_rate=0.0)
    assert "2021" in out and "2022" in out
    assert out["2021"]["gross_profit"] == pytest.approx(0.01, abs=1e-9)
    assert out["2022"]["gross_loss"] == pytest.approx(0.02, abs=1e-9)
    assert out["2021"]["pf"] is None  # solo ganancias -> None


def test_simulate_empty_returns_none():
    assert cb.simulate_carry([]) is None
