"""Candidato long E (pool del selector) — Trend entry + breakeven tras +8%.

Misma entrada EMA-trend; el SL se mueve a break-even cuando el trade supera +8%.
Distinto al 'let winners run' de Fase C (aqui se protege el capital). Sin order-callbacks.
"""
from freqtrade.strategy import IStrategy
import talib.abstract as ta


class PartialtpLong(IStrategy):
    timeframe = "2h"
    can_short = False
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    max_open_trades = 9
    stoploss = -0.10
    minimal_roi = {"0": 1.0}
    trailing_stop = False
    use_custom_stoploss = True
    ema_fast = 20
    ema_slow = 50
    be_trigger = 0.08

    def populate_indicators(self, df, meta):
        df["ema_fast"] = ta.EMA(df, timeperiod=self.ema_fast)
        df["ema_slow"] = ta.EMA(df, timeperiod=self.ema_slow)
        return df

    def populate_entry_trend(self, df, meta):
        df.loc[
            (df["close"] > df["ema_fast"])
            & (df["ema_fast"] > df["ema_slow"])
            & (df["volume"] > 0),
            "enter_long",
        ] = 1
        return df

    def populate_exit_trend(self, df, meta):
        df.loc[(df["ema_fast"] < df["ema_slow"]), "exit_long"] = 1
        return df

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        if current_profit >= self.be_trigger:
            return 0.0
        return -0.10
