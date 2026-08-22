"""Candidato long E (pool del selector) — Trend entry + SL adaptativo 2*ATR.

Misma entrada EMA-trend que Fase C pero el SL NO es fijo -10%: es 2*ATR respecto al
precio de entrada (stoploss dinamico). Cambia la relacion riesgo/beneficio sin mirar OOS.
"""
from freqtrade.strategy import IStrategy
import talib.abstract as ta


class AtrSlLong(IStrategy):
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
    atr_mult = 2.0

    def populate_indicators(self, df, meta):
        df["ema_fast"] = ta.EMA(df, timeperiod=self.ema_fast)
        df["ema_slow"] = ta.EMA(df, timeperiod=self.ema_slow)
        df["atr"] = ta.ATR(df, timeperiod=14)
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
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df.empty:
            return -0.10
        last = df.iloc[-1]
        if last["atr"] <= 0:
            return -0.10
        sl_price = trade.open_rate * (1 - self.atr_mult * last["atr"] / last["close"])
        return (sl_price / current_rate) - 1
