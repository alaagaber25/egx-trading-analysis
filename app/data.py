import logging
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

EGX_SUFFIX = ".CA"
MIN_ROWS = 30

# Some EGX tickers return bad data under their short symbol; map them to their ISIN ticker instead.
_SYMBOL_OVERRIDES: dict[str, str] = {
    "ORAS": "EGS95001C011",
}


def _resolve_ticker(symbol: str) -> str:
    """Return the yfinance ticker string for a given EGX symbol."""
    override = _SYMBOL_OVERRIDES.get(symbol.upper())
    return override if override else f"{symbol}{EGX_SUFFIX}"


def get_ohlcv(symbol: str, period: str = "2y") -> pd.DataFrame:
    ticker_symbol = _resolve_ticker(symbol)
    logger.info("Fetching OHLCV for %s period=%s", ticker_symbol, period)

    df = yf.download(
        ticker_symbol,
        period=period,
        interval="1d",
        progress=False,
        auto_adjust=True,
        threads=False,
    )

    if df is None or df.empty:
        raise ValueError(f"No data returned for {ticker_symbol}")

    # yfinance may return a MultiIndex when group_by or multiple tickers are used
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns for {ticker_symbol}: {missing}")

    df = df[list(required)].copy()

    # Drop rows where Close is NaN — those are unusable for any indicator
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
