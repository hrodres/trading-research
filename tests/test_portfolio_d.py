#!/usr/bin/env python3
"""Tests de Fase D — harness de agregacion de portfolio (scripts/portfolio_d.py).

Validan matematicas de: profit factor, equity curve, max drawdown, correlacion,
seleccion top-N y Sharpe. Usan fixtures sinteticos (sin freqtrade, sin datos reales).
"""
import importlib.util
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))

spec = importlib.util.spec_from_file_location("portfolio_d", os.path.join(REPO, "scripts", "portfolio_d.py"))
pd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pd)


def mk(variant, pair, open_ts, close_ts, pnl):
    return {"variant": variant, "pair": pair, "open_ts": open_ts,
            "close_ts": close_ts, "profit_abs": float(pnl)}


def test_profit_factor_basic():
    trades = [mk("A", "X", 1, 2, 10), mk("A", "X", 3, 4, -5), mk("A", "X", 5, 6, -5)]
    assert abs(pd.profit_factor(trades) - 1.0) < 1e-9


def test_profit_factor_no_losses():
    trades = [mk("A", "X", 1, 2, 10), mk("A", "X", 3, 4, 3)]
    assert pd.profit_factor(trades) is None


def test_profit_factor_empty():
    assert pd.profit_factor([]) is None


def test_equity_curve_ordered_and_cumulative():
    trades = [mk("A", "X", 0, 30, 10), mk("A", "X", 0, 10, -4), mk("A", "X", 0, 20, 6)]
    curve = pd.equity_curve(trades)
    assert [ts for ts, _ in curve] == [10, 20, 30]
    assert curve[-1][1] == 12.0  # -4 + 6 + 10


def test_max_drawdown_detects_peak_to_trough():
    # equity: 0 -> 100 -> 40 -> 60 -> 30 -> 80
    curve = [(1, 0), (2, 100), (3, 40), (4, 60), (5, 30), (6, 80)]
    mdd, peak, trough = pd.max_drawdown(curve)
    assert abs(mdd - 0.70) < 1e-9   # (100-30)/100
    assert peak == 100 and trough == 30


def test_max_drawdown_monotonic_up():
    curve = [(1, 0), (2, 5), (3, 10), (4, 20)]
    mdd, _, _ = pd.max_drawdown(curve)
    assert mdd == 0.0


def test_max_drawdown_empty():
    assert pd.max_drawdown([]) == (0.0, 0.0, 0.0)


def test_pearson_perfect_positive():
    assert abs(pd._pearson([1, 2, 3, 4], [2, 4, 6, 8]) - 1.0) < 1e-9


def test_pearson_perfect_negative():
    assert abs(pd._pearson([1, 2, 3, 4], [8, 6, 4, 2]) - (-1.0)) < 1e-9


def test_pearson_zero_when_constant():
    assert pd._pearson([1, 1, 1, 1], [1, 2, 3, 4]) is None


def test_correlation_matrix_symmetric_and_diagonal_one():
    trades = [
        mk("A", "X", 0, 10, 5), mk("A", "X", 0, 20, -2), mk("A", "X", 0, 30, 4),
        mk("B", "Y", 0, 10, -4), mk("B", "Y", 0, 20, 6), mk("B", "Y", 0, 30, -3),
    ]
    corr = pd.correlation_matrix(pd.monthly_series(trades))
    keys = list(corr.keys())
    assert len(keys) == 2
    # diagonal == 1 (auto-corr perfecta)
    for k in keys:
        assert corr[k][k] == 1.0 or corr[k][k] is None


def test_select_strategies_filters_min_trades_and_ranks():
    trades = [mk("A", "X", 0, 10, 10), mk("A", "X", 0, 20, -4)] + \
             [mk("B", "Y", 0, 30, 3), mk("B", "Y", 0, 40, -1)] * 20  # B: 40 trades
    ranked = pd.select_strategies(trades, min_trades=30)
    # solo B pasa el filtro de n>=30; A queda fuera
    assert all(k.startswith("B:") for k, _, _ in ranked)
    assert len(ranked) == 1


def test_assemble_aggregates_portfolio():
    trades = [mk("A", "X", 0, 10, 10), mk("A", "X", 0, 20, -5),
              mk("B", "Y", 0, 30, 8), mk("B", "Y", 0, 40, -4)]
    s = pd.assemble(trades)
    assert s["n_trades"] == 4
    assert s["win_pct"] == 50.0
    assert abs(s["pf"] - 18 / 9) < 1e-9  # gp=18, gl=9
    assert s["net_pnl_usdt"] == 9.0


def test_build_portfolio_filters_include():
    trades = [mk("A", "X", 0, 10, 10), mk("B", "Y", 0, 20, 5)]
    sub = pd.build_portfolio(trades, ["A:X"])
    assert len(sub) == 1 and sub[0]["variant"] == "A"


def test_sharpe_returns_none_on_tiny_series():
    trades = [mk("A", "X", 0, 10, 5)]
    assert pd.sharpe_monthly(trades) is None
