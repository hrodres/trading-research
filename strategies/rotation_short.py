"""Candidato short (pool del selector) — Espejo bajista de RotationLong.

RANKEA los 9 pares por momentum relativo cada ventana y entra SHORT solo en los
mas DEBILES (bottom-N). Mismo mecanismo que RotationLong pero en direccion contraria:
donde el long exige fuerza (mom alto + close>ema50), el short exige debilidad
(mom bajo + close<ema50). Exit: EMA-cross invertido (cortar cuando la debilidad
termine). SL -10%.
"""
from freqtrade.strategy import IStrategy
import talib.abstract as ta
import numpy as np


class RotationShort(IStrategy):
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
    top_n = 3
    ema_fast = 20
    ema_slow = 50

    def populate_indicators(self, df, meta):
        df["ema_fast"] = ta.EMA(df, timeperiod=self.ema_fast)
        df["ema_slow"] = ta.EMA(df, timeperiod=self.ema_slow)
        df["mom"] = df["close"].pct_change(2)
        df["mom_ma"] = df["mom"].rolling(20).mean()
        # bottom-N: 1 si el valor actual esta entre los N mas debiles de los ultimos 20
        df["mom_rank_weak"] = df["mom_ma"].rolling(20).apply(
            lambda x: 1.0 if x[-1] <= np.sort(x)[self.top_n - 1] else 0.0, raw=True
        )
        return df

    def populate_entry_trend(self, df, meta):
        df.loc[
            (df["mom_rank_weak"] > 0)
            & (df["close"] < df["ema_slow"])
            & (df["volume"] > 0),
            "enter_short",
        ] = 1
        return df

    def populate_exit_trend(self, df, meta):
        df.loc[(df["ema_fast"] > df["ema_slow"]), "exit_short"] = 1
        return df
