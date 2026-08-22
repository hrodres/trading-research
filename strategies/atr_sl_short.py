"""Candidato short (pool del selector) — Espejo bajista de AtrSlLong.

Entrada EMA-trend invertida (precio por DEBAJO de EMA20 y EMA20<EMA50) y SL
adaptativo 2*ATR por ENCIMA del precio de entrada (en short, el riesgo esta arriba).
Exit: EMA-cross invertido.
"""
from freqtrade.strategy import IStrategy
import talib.abstract as ta


class AtrSlShort(IStrategy):
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
            (df["close"] < df["ema_fast"])
            & (df["ema_fast"] < df["ema_slow"])
            & (df["volume"] > 0),
            "enter_short",
        ] = 1
        return df

    def populate_exit_trend(self, df, meta):
        df.loc[(df["ema_fast"] > df["ema_slow"]), "exit_short"] = 1
        return df

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        df, _ = self.dp.get_analyzed_dataframe(pair, self.timeframe)
        if df.empty:
            return -0.10
        last = df.iloc[-1]
        if last["atr"] <= 0:
            return -0.10
        # En short el SL va POR ENCIMA del precio de entrada
        sl_price = trade.open_rate * (1 + self.atr_mult * last["atr"] / last["close"])
        return (current_rate / sl_price) - 1
