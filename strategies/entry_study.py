"""Fase B — Estudio de senales de ENTRADA (freqtrade).

OBJETIVO: aislar el efecto de la ENTRADA. Todas las variants comparten el MISMO
exit ganador de Fase C (SaleEmaCross: dejar correr hasta EMA-cross + SL -10%,
sin TP fijo corto). Lo unico que cambia es la CONDICION DE ENTRADA.

Por que existe: en C, arreglar solo el exit subio el PF de ~0.3 a 0.65, pero
ni el mejor exit llega a 1.5 -> el bottleneck es la ENTRADA (EMA20>EMA50 no
tiene edge). Aqui probamos entradas alternativas para ver cual SI aporta.

Exit comun (SaleEmaCross base):
  - stoploss -10%, sin minimal_roi (deja correr), sale en EMA20<EMA50.

Variants de ENTRADA (mismos indicadores base cuando aplica):
  - EntryTrend     : EMA20>EMA50 (baseline de referencia, igual que A.3/C)
  - EntryTrendADX  : EMA20>EMA50 + ADX>25 (solo en tendencia fuerte)
  - EntryBreakout  : cierre rompe maximo de 20 velas (Donchian)
  - EntryPullback  : EMA20>EMA50 + precio cerca de EMA20 (pullback) + RSI gira up
  - EntryVolConfirm: EMA20>EMA50 + volumen > 1.5x media 20v
  - EntryMeanRev   : RSI<30 en rango (cierre < EMA50)  [contraste: contra-tendencia]

  [NOTA FORENSE] EntryV9Style es UNA SOLA variant aislada, anadida a peticion del
  usuario (03:46 UTC) para cerrar la duda sobre la senal de entrada de v9. NO es
  parte de la busqueda de edge del proyecto y queda FUERA de VARIANTS por defecto
  (ver scripts/entry_study.py). Resultado: casi inerte (5 trades/5 anos, PF 0.0).
  No usar como candidata en Fase D ni en ningun estudio canonico.

Metodo OOS: 5 ventanas anuales (2021-2025), 9 pares, sizing fijo 100 USDT,
fees 0.001. Sin fitting en IS -> todo OOS por construccion (evita overfit).

Referencia oficial freqtrade usada: populate_entry_trend vectorizado, ADX/RSI
de talib. Nada de repos de comunidad se copia directo; se reimplementa y pasa
el mismo gate.
"""
from freqtrade.strategy import IStrategy
import talib.abstract as ta
import numpy as np


class EntryStudyBase(IStrategy):
    timeframe = "2h"
    can_short = False
    process_only_new_candles = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    max_open_trades = 9

    # EXIT comun ganador de Fase C: dejar correr, SL -10%, sin TP fijo corto
    stoploss = -0.10
    minimal_roi = {"0": 1.0}   # desactivado en la practica; sale en EMA-cross
    trailing_stop = False
    use_exit_signal = True

    ema_fast = 20
    ema_slow = 50

    def populate_indicators(self, dataframe, metadata):
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=self.ema_fast)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=self.ema_slow)
        dataframe["adx"] = ta.ADX(dataframe, timeperiod=14)
        dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
        dataframe["vol_ma"] = dataframe["volume"].rolling(20).mean()
        dataframe["hh20"] = dataframe["high"].rolling(20).max().shift(1)
        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        dataframe.loc[(dataframe["ema_fast"] < dataframe["ema_slow"]), "exit_long"] = 1
        return dataframe


class EntryTrend(EntryStudyBase):
    """Referencia: EMA20>EMA50 (igual que baseline A.3 / ExitEmaCross de C)."""
    name = "EntryTrend"

    def populate_entry_trend(self, dataframe, metadata):
        dataframe.loc[
            (dataframe["close"] > dataframe["ema_fast"])
            & (dataframe["ema_fast"] > dataframe["ema_slow"])
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1
        return dataframe


class EntryTrendADX(EntryStudyBase):
    """EMA20>EMA50 solo cuando ADX>25 (tendencia fuerte, filtra chop)."""
    name = "EntryTrendADX"

    def populate_entry_trend(self, dataframe, metadata):
        dataframe.loc[
            (dataframe["close"] > dataframe["ema_fast"])
            & (dataframe["ema_fast"] > dataframe["ema_slow"])
            & (dataframe["adx"] > 25)
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1
        return dataframe


class EntryBreakout(EntryStudyBase):
    """Breakout: cierre rompe el maximo de 20 velas (Donchian)."""
    name = "EntryBreakout"

    def populate_entry_trend(self, dataframe, metadata):
        dataframe.loc[
            (dataframe["close"] > dataframe["hh20"])
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1
        return dataframe


class EntryPullback(EntryStudyBase):
    """Pullback en tendencia: EMA20>EMA50 + precio cerca de EMA20 + RSI gira up."""
    name = "EntryPullback"

    def populate_entry_trend(self, dataframe, metadata):
        near_ema = (dataframe["close"] >= dataframe["ema_fast"] * 0.98) & \
                   (dataframe["close"] <= dataframe["ema_fast"] * 1.02)
        rsi_up = dataframe["rsi"] > dataframe["rsi"].shift(1)
        dataframe.loc[
            (dataframe["ema_fast"] > dataframe["ema_slow"])
            & near_ema & rsi_up
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1
        return dataframe


class EntryVolConfirm(EntryStudyBase):
    """EMA20>EMA50 + volumen > 1.5x media 20v (confirma interes)."""
    name = "EntryVolConfirm"

    def populate_entry_trend(self, dataframe, metadata):
        dataframe.loc[
            (dataframe["close"] > dataframe["ema_fast"])
            & (dataframe["ema_fast"] > dataframe["ema_slow"])
            & (dataframe["volume"] > 1.5 * dataframe["vol_ma"])
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1
        return dataframe


class EntryMeanRev(EntryStudyBase):
    """Contra-tendencia (contraste): RSI<30 en rango (cierre < EMA50)."""
    name = "EntryMeanRev"

    def populate_entry_trend(self, dataframe, metadata):
        dataframe.loc[
            (dataframe["close"] < dataframe["ema_slow"])
            & (dataframe["rsi"] < 30)
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1
        return dataframe


class EntryV9Style(EntryStudyBase):
    """ESTILO DE ENTRADA DEL BOT v9 — VARIANT FORENSE (NO CANONICA).

    Anadida a peticion del usuario (03:46 UTC) para cerrar una duda sobre v9.
    NO forma parte de la busqueda de edge del proyecto: queda FUERA de VARIANTS
    por defecto en scripts/entry_study.py. Resultado forense ya documentado en
    results/entrystudy_v9style.json (CASI INERTE: 5 trades en 5 anos, PF 0.0, win 0%).
    No usar como candidata en Fase D ni en estudios canonicos.

    Replica el *estilo* de `evaluate_long_entry` de v9: entra LONG cuando
    >=2 de 3 senales disparan (score_bull). NO es el sistema v9 (sin OCO,
    sin testnet/Binance, sin perfiles de riesgo): solo la senal de entrada,
    corriendo en freqtrade con datos Coinbase 2h y el exit comun de Fase C.
","""
    name = "EntryV9Style"

    def populate_indicators(self, dataframe, metadata):
        dataframe = super().populate_indicators(dataframe, metadata)
        dataframe["sma20"] = ta.SMA(dataframe, timeperiod=20)
        dataframe["support50"] = dataframe["low"].rolling(50).min()
        # engulfing components
        po = dataframe["open"].shift(1)
        pc = dataframe["close"].shift(1)
        co = dataframe["open"]
        cc = dataframe["close"]
        bull_engulf = (po > pc) & (cc > co) & (co <= pc) & (cc >= po)
        avg_vol = dataframe["volume"].rolling(21).mean().shift(1)
        vol_ok = dataframe["volume"] >= avg_vol * 1.2
        dataframe["engulf"] = bull_engulf & (dataframe["rsi"] <= 40) & vol_ok
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        momentum = (
            (dataframe["close"] > dataframe["sma20"])
            & (dataframe["rsi"] >= 45)
            & (dataframe["rsi"] <= 65)
        )
        vol_support = (
            (dataframe["support50"] > 0)
            & (dataframe["close"] >= dataframe["support50"] * 0.99)
            & (dataframe["close"] <= dataframe["support50"] * 1.01)
        )
        score = momentum.astype(int) + vol_support.astype(int) + dataframe["engulf"].astype(int)
        dataframe.loc[(score >= 2) & (dataframe["volume"] > 0), "enter_long"] = 1
        return dataframe
