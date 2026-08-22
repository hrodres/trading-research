"""Candidato short (pool del selector) — Espejo bajista de VolBreakoutLong.

Entra SHORT cuando el precio rompe el minimo de 20v (ll20) CON expansion de ATR
(atr > 1.2*media20) y el precio esta por debajo de la EMA50. Espejo exacto del
breakout al alza de VolBreakoutLong, en direccion contraria. Exit: EMA-cross
invertido. SL -10%.
"""
from freqtrade.strategy import IStrategy
import talib.abstract as ta


class VolBreakoutShort(IStrategy):
    timeframe = "2h"
    can_short = True
    process_only_new_candles = True
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    max_open_trades = 9
    stoploss = -0.10
    minimal_roi = {"0": 1.0}
    trailing_stop = False
    ema_fast = 20
    ema_slow = 50

    def populate_indicators(self, df, meta):
        df["ll20"] = df["low"].rolling(20).min().shift(1)
        df["atr"] = ta.ATR(df, timeperiod=14)
        df["atr_ma"] = df["atr"].rolling(20).mean()
        df["ema_fast"] = ta.EMA(df, timeperiod=self.ema_fast)
        df["ema_slow"] = ta.EMA(df, timeperiod=self.ema_slow)
        return df

    def populate_entry_trend(self, df, meta):
        df.loc[
            (df["close"] < df["ll20"])
            & (df["atr"] > 1.2 * df["atr_ma"])
            & (df["close"] < df["ema_slow"])
            & (df["volume"] > 0),
            "enter_short",
        ] = 1
        return df

    def populate_exit_trend(self, df, meta):
        df.loc[(df["ema_fast"] > df["ema_slow"]), "exit_short"] = 1
        return df
