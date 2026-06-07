import logging
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

EGX_SUFFIX = ".CA"
MIN_ROWS = 30

# EGX symbols whose plain <SYMBOL>.CA Yahoo listing is unusable for analysis:
#   - ORAS: <SYM>.CA is a DIFFERENT instrument (EGP 71 vs the real EGP 742 equity)
#   - TWSA, EAGL: <SYM>.CA does not exist on Yahoo at all
# The correct company is only reachable via its ISIN-style ticker, which Yahoo
# serves as an INTRADAY-ONLY quote symbol (validRanges ['1d','5d'], no daily
# backfill). So for these we use the ISIN for the live quote and skip technical
# analysis — there is no reliable daily history on Yahoo for them.
#
# Do NOT add a symbol here just because its quoteType is MUTUALFUND or its name
# looks generic — that is a universal Yahoo quirk for EGX and those <SYM>.CA
# tickers DO carry full daily history (e.g. FWRY, COMI, ORHD, MFPC, MPCI). Only
# add a symbol whose <SYM>.CA last close does not match the real share price, or
# whose <SYM>.CA listing is missing. Map it to "<ISIN>.CA".
_QUOTE_ONLY_OVERRIDES: dict[str, str] = {
    "ORAS": "EGS95001C011.CA",
    "TWSA": "EGS7D231C010.CA",
    "EAGL": "EGS3E181C010.CA",
}


def resolve_history_ticker(symbol: str) -> str:
    """Ticker to use for daily OHLCV history. Always the short <SYM>.CA form —
    EGX daily history on Yahoo lives only under this symbol, never the ISIN."""
    return f"{symbol.upper()}{EGX_SUFFIX}"


def resolve_quote_ticker(symbol: str) -> str:
    """Ticker to use for the live price quote. Uses the ISIN override where the
    plain <SYM>.CA listing is the wrong instrument or missing."""
    s = symbol.upper()
    return _QUOTE_ONLY_OVERRIDES.get(s, f"{s}{EGX_SUFFIX}")


def get_ohlcv(symbol: str, period: str = "2y") -> pd.DataFrame:
    sym = symbol.upper()

    if sym in _QUOTE_ONLY_OVERRIDES:
        # Yahoo has no daily history for these (quote-only ISIN symbol), and the
        # plain <SYM>.CA listing is a different instrument. Refuse rather than
        # silently analyze the wrong data — the caller falls back to price-only.
        raise ValueError(
            f"No reliable daily history on Yahoo for {sym}: quote-only symbol"
        )

    ticker_symbol = resolve_history_ticker(sym)
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
    ticker_symbol = resolve_quote_ticker(symbol)
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
