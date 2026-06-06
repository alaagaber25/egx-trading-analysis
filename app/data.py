import logging
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

EGX_SUFFIX = ".CA"
MIN_ROWS = 30

# Tickers where the default <SYMBOL>.CA Yahoo Finance entry is a different company
# or has corrupt data. Map to the correct yfinance ticker (e.g. the stock's ISIN).
_SYMBOL_OVERRIDES: dict[str, str] = {
    "ORAS": "EGS95001C011",
    "ORHD": "EGS70321C012",
    "TWSA": "EGS7D231C010",
    "EAGL": "EGS3E181C010",
    "MFPC": "EGS39061C014",
    "MPCI": "EGS38351C010",
}


def _resolve_ticker(symbol: str) -> str:
    s = symbol.upper()
    return _SYMBOL_OVERRIDES.get(s, f"{s}{EGX_SUFFIX}")


def get_ohlcv(symbol: str, period: str = "2y") -> pd.DataFrame:
    ticker_symbol = _resolve_ticker(symbol)
    logger.info("Fetching OHLCV for %s period=%s", ticker_symbol, period)

    df = yf.Ticker(ticker_symbol).history(
        period=period,
        interval="1d",
        auto_adjust=True,
    )

    if df is None or df.empty:
        raise ValueError(f"No data returned for {ticker_symbol}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns for {ticker_symbol}: {missing}")

    df = df[list(required)].copy()
    df.dropna(subset=["Close"], inplace=True)

    if len(df) < MIN_ROWS:
        raise ValueError(
            f"Insufficient data for {ticker_symbol}: {len(df)} rows (need {MIN_ROWS})"
        )

    logger.info("Fetched %d rows for %s", len(df), ticker_symbol)
    return df


def get_price_info(symbol: str) -> dict:
    ticker_symbol = _resolve_ticker(symbol)
    logger.info("Fetching fast_info for %s", ticker_symbol)

    ticker = yf.Ticker(ticker_symbol)
    info = ticker.fast_info

    def _safe(attr: str) -> Optional[float]:
        try:
            val = getattr(info, attr, None)
            if val is None:
                return None
            return round(float(val), 4)
        except (TypeError, ValueError, AttributeError):
            return None

    return {
        "symbol": symbol,
        "price": _safe("last_price"),
        "high": _safe("day_high"),
        "low": _safe("day_low"),
        "volume": _safe("last_volume"),
    }
