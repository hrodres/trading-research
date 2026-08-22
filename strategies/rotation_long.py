"""Candidato long E (pool del selector) — Rotacion cross-sectional LONG top-N.

RANKEA los 9 pares por momentum relativo cada ventana y entra LONG solo en los N
mas fuertes. Cambia la SELECCION de pares, no la senal EMA: mecanismo distinto al
trend de Fase B (se espera correlacion <0.7). Top-N=3 fijado A PRIORI (sin mirar OOS).
Exit comun Fase C: EMA-cross + SL -10%.
"""
from freqtrade.strategy import IStrategy
import talib.abstract as ta
import numpy as np


class RotationLong(IStrategy):
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
    top_n = 3
    ema_fast = 20
    ema_slow = 50

    def populate_indicators(self, df, meta):
        df["ema_fast"] = ta.EMA(df, timeperiod=self.ema_fast)
        df["ema_slow"] = ta.EMA(df, timeperiod=self.ema_slow)
        df["mom"] = df["close"].pct_change(2)
        df["mom_ma"] = df["mom"].rolling(20).mean()
        df["mom_rank"] = df["mom_ma"].rolling(20).apply(
            lambda x: 1.0 if x[-1] >= np.sort(x)[-self.top_n] else 0.0, raw=True
        )
        return df

    def populate_entry_trend(self, df, meta):
        df.loc[
            (df["mom_rank"] > 0)
            & (df["close"] > df["ema_slow"])
            & (df["volume"] > 0),
            "enter_long",
        ] = 1
        return df

    def populate_exit_trend(self, df, meta):
        df.loc[(df["ema_fast"] < df["ema_slow"]), "exit_long"] = 1
        return df
