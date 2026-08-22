"""Fase A.2 — Estrategia baseline de tendencia/momentum (freqtrade).

Baseline HONESTO: referencia mínima para validar el harness OOS y tener un
número de comparación real. NO es edge ni promesa de rentabilidad: solo prueba
que el backtest corre, es reproducible y da métricas con fees + stoploss.

Lógica (largo solo, sin apalancamiento):
  - Entrada: close > EMA20 > EMA50  (tendencia alcista, fuera de pullback profundo)
  - Salida:  EMA20 cruza por debajo de EMA50
  - Stop:    -10% (stoploss fijo). Sin trailing todavía (eso es Fase C).

El edge real (si existe) se busca en B/C/D. Esto es la línea base.
"""
from freqtrade.strategy import IStrategy
import talib.abstract as ta


class BaselineTrend(IStrategy):
    timeframe = "2h"
    can_short = False

    # Riesgo fijo y simple (sin leverage, sin trailing todavía)
    stoploss = -0.10
    minimal_roi = {"0": 0.08, "48": 0.04, "96": 0.02}
    trailing_stop = False

    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    max_open_trades = 1

    ema_fast = 20
    ema_slow = 50

    def populate_indicators(self, dataframe, metadata):
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=self.ema_fast)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=self.ema_slow)
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        dataframe.loc[
            (dataframe["close"] > dataframe["ema_fast"])
            & (dataframe["ema_fast"] > dataframe["ema_slow"])
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        dataframe.loc[
            (dataframe["ema_fast"] < dataframe["ema_slow"]),
            "exit_long",
        ] = 1
        return dataframe
