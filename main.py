import logging
import re
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Path, Query

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

# EGX ticker symbols are 2-6 uppercase letters
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
        "Provides OHLCV data, momentum/trend indicators, and AI-ready signal interpretation."
    ),
    version=VERSION,
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=VERSION)


@app.get("/price/{symbol}", response_model=PriceResponse, tags=["market"])
def price(
    symbol: Annotated[str, Path(description="EGX ticker without the .CA suffix")],
) -> PriceResponse:
    symbol = _validate_symbol(symbol)
    try:
        data = get_price_info(symbol)
        return PriceResponse(**data)
    except Exception as exc:
        logger.error("Price fetch failed for %s: %s", symbol, exc)
        raise HTTPException(status_code=502, detail=f"Failed to fetch price for {symbol}: {exc}")


@app.get("/analyze/{symbol}", response_model=StockAnalysis, tags=["analysis"])
def analyze_stock(
    symbol: Annotated[str, Path(description="EGX ticker without the .CA suffix")],
    period: Annotated[
        str,
        Query(description="Historical data window. More data improves SMA200 accuracy."),
    ] = "2y",
) -> StockAnalysis:
    symbol = _validate_symbol(symbol)

    if period not in VALID_PERIODS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid period '{period}'. Choose from: {sorted(VALID_PERIODS)}",
        )

    try:
        df = get_ohlcv(symbol, period=period)
    except ValueError as exc:
        logger.warning("Data unavailable for %s: %s", symbol, exc)
        raise HTTPException(status_code=404, detail=str(exc))
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
