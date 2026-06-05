import logging
import re
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi_mcp import FastApiMCP

from app.analysis import interpret_risk, interpret_trend
from app.data import get_ohlcv, get_price_info
from app.indicators import compute_indicators
from app.models import HealthResponse, Indicators, PriceResponse, StockAnalysis

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

VERSION = "1.0.0"

_SYMBOL_RE = re.compile(r"^[A-Z]{2,6}$")
VALID_PERIODS = {"1mo", "3mo", "6mo", "1y", "2y"}


def _validate_symbol(symbol: str) -> str:
    s = symbol.upper().strip()
    if not _SYMBOL_RE.match(s):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid symbol '{symbol}'. Expected 2-6 uppercase letters (e.g. FWRY, COMI).",
        )
    return s


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("EGX Trading Analysis API v%s starting", VERSION)
    yield
    logger.info("EGX Trading Analysis API shutting down")


app = FastAPI(
    title="EGX Trading Analysis API",
    description=(
        "Technical analysis engine for the Egyptian Stock Exchange (EGX). "
        "Ticker symbols are provided WITHOUT the .CA suffix (e.g. FWRY, COMI, HRHO). "
        "Provides OHLCV data, momentum/trend indicators, and AI-ready signal interpretation."
    ),
    version=VERSION,
    lifespan=lifespan,
)


@app.get(
    "/health",
    response_model=HealthResponse,
    operation_id="health_check",
    tags=["system"],
    summary="Service liveness check",
)
def health() -> HealthResponse:
    """Returns service status and version. Use this to confirm the API is reachable."""
    return HealthResponse(status="ok", version=VERSION)


@app.get(
    "/price/{symbol}",
    response_model=PriceResponse,
    operation_id="get_price",
    tags=["market"],
    summary="Real-time price quote",
)
def price(
    symbol: Annotated[
        str,
        Path(description="EGX ticker WITHOUT .CA suffix (e.g. FWRY, COMI, HRHO, ETEL)"),
    ],
) -> PriceResponse:
    """
    Fetch the current real-time price quote for an Egyptian stock.

    Returns the last traded price, intraday high/low, and last volume.
    Data is sourced from Yahoo Finance via the .CA suffix.
    """
    symbol = _validate_symbol(symbol)
    try:
        data = get_price_info(symbol)
        return PriceResponse(**data)
    except Exception as exc:
        logger.error("Price fetch failed for %s: %s", symbol, exc)
        raise HTTPException(status_code=502, detail=f"Failed to fetch price for {symbol}: {exc}")


@app.get(
    "/analyze/{symbol}",
    response_model=StockAnalysis,
    operation_id="analyze_stock",
    tags=["analysis"],
    summary="Full technical analysis",
)
def analyze_stock(
    symbol: Annotated[
        str,
        Path(description="EGX ticker WITHOUT .CA suffix (e.g. FWRY, COMI, HRHO, ETEL)"),
    ],
    period: Annotated[
        str,
        Query(
            description=(
                "Historical data window for indicator calculation. "
                "Use 2y (default) for reliable SMA200. "
                "Options: 1mo, 3mo, 6mo, 1y, 2y."
            )
        ),
    ] = "2y",
) -> StockAnalysis:
    """
    Run full technical analysis on an Egyptian stock (EGX).

    Computes: RSI, RMI, MACD + signal line, EMA20, EMA50, SMA200, ATR, ADX, OBV, MFI.

    Returns:
    - **indicators**: all computed values (null if insufficient data)
    - **trend_analysis**: bullish / bearish / neutral based on price vs moving averages,
      RSI zone, MACD crossover, and ADX trend strength
    - **risk_level**: low / medium / high based on RSI extremes, ADX magnitude, and ATR%
    """
    symbol = _validate_symbol(symbol)

    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid period '{period}'. Choose from: {sorted(VALID_PERIODS)}",
        )

    try:
        df = get_ohlcv(symbol, period=period)
    except ValueError as exc:
        logger.warning("No historical data for %s (%s) — returning price-only", symbol, exc)
        try:
            price_data = get_price_info(symbol)
            price_val = price_data.get("price") or 0.0
        except Exception:
            price_val = 0.0
        return StockAnalysis(
            symbol=symbol,
            price=price_val,
            message=(
                "Insufficient historical data available for this stock on Yahoo Finance. "
                "Only the live price is shown. Technical analysis (indicators, trend, risk) "
                "cannot be performed."
            ),
        )
    except Exception as exc:
        logger.error("Data fetch failed for %s: %s", symbol, exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Data fetch failed: {exc}")

    try:
        price_val = round(float(df["Close"].iloc[-1]), 4)
        ind = compute_indicators(df)
        trend = interpret_trend(price_val, ind)
        risk = interpret_risk(price_val, ind)

        return StockAnalysis(
            symbol=symbol,
            price=price_val,
            indicators=Indicators(**ind),
            trend_analysis=trend,
            risk_level=risk,
        )
    except Exception as exc:
        logger.error("Analysis failed for %s: %s", symbol, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis computation failed: {exc}")


# ── Path 2: MCP HTTP endpoint at /mcp ──────────────────────────────────────
# Claude Desktop (and any MCP client) can connect to http://<host>/mcp
# fastapi-mcp auto-discovers routes tagged "analysis" and "market" and
# exposes them as MCP tools. It calls the FastAPI app internally via ASGI
# transport — no external HTTP hop required.
mcp = FastApiMCP(
    app,
    name="EGX Trading Analysis",
    description=(
        "Technical analysis tools for Egyptian Stock Exchange (EGX) stocks. "
        "Symbols must be provided WITHOUT the .CA suffix (e.g. FWRY, COMI, HRHO). "
        "Use analyze_stock for full indicator analysis; get_price for a live quote."
    ),
    include_tags=["analysis", "market"],
    describe_all_responses=True,
    describe_full_response_schema=True,
)
mcp.mount_http()  # Mounts at /mcp — Claude Desktop connects to http://<host>/mcp
