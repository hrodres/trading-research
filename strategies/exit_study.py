"""Fase C — Estudio de mecánicas de SALIDA (freqtrade).

OBJETIVO: aislar el efecto del EXIT. Todas las variants comparten EXACTAMENTE
la misma entrada (close > EMA20 > EMA50, igual que la baseline de A.3) y el
mismo SL base de -10%. Lo unico que cambia es como se sale cuando el trade
esta en ganancia.

Por que existe esta fase: en A.3 la baseline (SL -10% + TP cap +8%) dio PF ~0.3
en todos los pares. El diagnostico fue asimetria R:R (el gain se capa en +8%
pero el SL es -10% + fees). Aqui probamos salidas que deberian corregir eso:

  - ExitFixedWide : TP mas ancho (+10/5/3%) + SL -10% + EMA-cross. Baseline "reparada".
  - ExitTrailing  : trailing asimetrico (offset +10%, positivo +2%) + SL -10%. Protege
                    ganancias: deja correr el trade pero nunca pierde mas de -10% tras
                    haber pasado +10%.
  - ExitEmaCross  : SOLO EMA-cross + SL -10% (sin ROI). Deja correr hasta que la
                    tendencia se invierte. Aisla "let winners run".
  - ExitTimeStop  : combo (TP+SL+EMA-cross) + tope temporal duro (48 velas = 4 dias).
                    Evita trades muertos atrapados en rango.

Sizing y datos: idem A.3 (stake fijo 100 USDT, fees 0.001, 9 pares, Coinbase 2h).
NO hay fitting en IS -> todo OOS por construccion (evita overfit).

Referencia oficial freqtrade (stoploss.md) usada para trailing:
  trailing_stop=True; trailing_stop_positive=0.02; trailing_stop_positive_offset=0.10;
  trailing_only_offset_is_reached=True  => SL fijo en -10% hasta +10%, luego protege +2%.
"""
from freqtrade.strategy import IStrategy
import talib.abstract as ta


class ExitStudyBase(IStrategy):
    timeframe = "2h"
    can_short = False
    process_only_new_candles = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    max_open_trades = 9

    # SL base comun a todas las variants (sin apalancamiento)
    stoploss = -0.10

    ema_fast = 20
    ema_slow = 50

    def populate_indicators(self, dataframe, metadata):
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=self.ema_fast)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=self.ema_slow)
        return dataframe

    def populate_entry_trend(self, dataframe, metadata):
        # MISMA entrada que la baseline de A.3 (para aislar el efecto del exit)
        dataframe.loc[
            (dataframe["close"] > dataframe["ema_fast"])
            & (dataframe["ema_fast"] > dataframe["ema_slow"])
            & (dataframe["volume"] > 0),
            "enter_long",
        ] = 1
        return dataframe

    def populate_exit_trend(self, dataframe, metadata):
        # Senal EMA-cross (la usan las variants que la quieran via use_exit_signal)
        dataframe.loc[(dataframe["ema_fast"] < dataframe["ema_slow"]), "exit_long"] = 1
        return dataframe


class ExitFixedWide(ExitStudyBase):
    """TP mas ancho que la baseline (+10/5/3%) + SL -10% + EMA-cross.
    Baseline 'reparada' (ataque directo a la asimetria SL/TP de A.3)."""
    name = "ExitFixedWide"
    minimal_roi = {"0": 0.10, "48": 0.05, "96": 0.03}
    trailing_stop = False
    use_exit_signal = True

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        return None


class ExitTrailing(ExitStudyBase):
    """Trailing asimetrico: SL fijo -10% hasta +10%, luego protege ganancias a +2%.
    Deja correr tendencias sin cap duro de TP."""
    name = "ExitTrailing"
    minimal_roi = {"0": 1.0}          # ROI desactivado en la practica (solo trailing/SL)
    trailing_stop = True
    trailing_stop_positive = 0.02
    trailing_stop_positive_offset = 0.10
    trailing_only_offset_is_reached = True
    use_exit_signal = False           # la salida la manda el trailing, no la EMA-cross

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        return None


class ExitEmaCross(ExitStudyBase):
    """SOLO EMA-cross + SL -10% (sin ROI). Deja correr hasta que la tendencia
    se invierte. Aisla el efecto de 'let winners run'."""
    name = "ExitEmaCross"
    minimal_roi = {"0": 1.0}          # ROI desactivado
    trailing_stop = False
    use_exit_signal = True

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        return None


class ExitTimeStop(ExitStudyBase):
    """Combo (TP+SL+EMA-cross) + tope temporal duro de 48 velas (4 dias).
    Evita trades muertos atrapados en rango lateral."""
    name = "ExitTimeStop"
    minimal_roi = {"0": 0.10, "48": 0.05, "96": 0.03}
    trailing_stop = False
    use_exit_signal = True
    TIME_LIMIT_CANDLES = 48           # 48 * 2h = 4 dias

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        open_candles = int(
            (current_time - trade.open_date_utc).total_seconds() // (self.timeframe_minutes() * 60)
        )
        if open_candles >= self.TIME_LIMIT_CANDLES:
            return "time_exit_4d"
        return None

    @staticmethod
    def timeframe_minutes():
        return 120  # "2h"
