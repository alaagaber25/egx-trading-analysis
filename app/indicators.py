import logging
from typing import Optional

import numpy as np
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)


def _safe_float(val) -> Optional[float]:
    """Return a rounded float or None for NaN/Inf/non-numeric values."""
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return round(f, 4)
    except (TypeError, ValueError):
        return None


def _last(series: Optional[pd.Series]) -> Optional[float]:
    if series is None or series.empty:
        return None
    return _safe_float(series.iloc[-1])


def _calc_rmi(close: pd.Series, length: int = 14, momentum: int = 5) -> pd.Series:
    delta = close - close.shift(momentum)
    up = delta.clip(lower=0)
    down = (-delta).clip(lower=0)
    avg_up = up.ewm(alpha=1 / length, adjust=False).mean()
    avg_down = down.ewm(alpha=1 / length, adjust=False).mean()
    # Replace 0 with NaN before division to avoid inf
    rs = avg_up / avg_down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_indicators(df: pd.DataFrame) -> dict:
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    result: dict[str, Optional[float]] = {}

    # RSI
    try:
        result["rsi"] = _last(ta.rsi(close, length=14))
    except Exception as exc:
        logger.warning("RSI failed: %s", exc)
        result["rsi"] = None

    # RMI (custom)
    try:
        result["rmi"] = _last(_calc_rmi(close, length=14, momentum=5))
    except Exception as exc:
        logger.warning("RMI failed: %s", exc)
        result["rmi"] = None

    # MACD
    try:
        macd_df = ta.macd(close)
        if macd_df is not None and not macd_df.empty:
            result["macd"] = _safe_float(macd_df["MACD_12_26_9"].iloc[-1])
            result["macd_signal"] = _safe_float(macd_df["MACDs_12_26_9"].iloc[-1])
        else:
            result["macd"] = None
            result["macd_signal"] = None
    except Exception as exc:
        logger.warning("MACD failed: %s", exc)
        result["macd"] = None
        result["macd_signal"] = None

    # EMA 20 / 50
    try:
        result["ema20"] = _last(ta.ema(close, length=20))
    except Exception as exc:
        logger.warning("EMA20 failed: %s", exc)
        result["ema20"] = None

    try:
        result["ema50"] = _last(ta.ema(close, length=50))
    except Exception as exc:
        logger.warning("EMA50 failed: %s", exc)
        result["ema50"] = None

    # SMA 200 — requires ~200 rows; may be None for thin data sets
    try:
        result["sma200"] = _last(ta.sma(close, length=200))
    except Exception as exc:
        logger.warning("SMA200 failed: %s", exc)
        result["sma200"] = None

    # ATR
    try:
        result["atr"] = _last(ta.atr(high, low, close, length=14))
    except Exception as exc:
        logger.warning("ATR failed: %s", exc)
        result["atr"] = None

    # ADX
    try:
        adx_df = ta.adx(high, low, close)
        if adx_df is not None and not adx_df.empty:
            result["adx"] = _safe_float(adx_df["ADX_14"].iloc[-1])
        else:
            result["adx"] = None
    except Exception as exc:
        logger.warning("ADX failed: %s", exc)
        result["adx"] = None

    # OBV
    try:
        result["obv"] = _last(ta.obv(close, volume))
    except Exception as exc:
        logger.warning("OBV failed: %s", exc)
        result["obv"] = None

    # MFI
    try:
        result["mfi"] = _last(ta.mfi(high, low, close, volume))
    except Exception as exc:
        logger.warning("MFI failed: %s", exc)
        result["mfi"] = None

    return result
