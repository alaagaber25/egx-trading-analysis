from typing import Literal, Optional
from pydantic import BaseModel


class Indicators(BaseModel):
    rsi: Optional[float] = None
    rmi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    ema20: Optional[float] = None
    ema50: Optional[float] = None
    sma200: Optional[float] = None
    atr: Optional[float] = None
    adx: Optional[float] = None
    obv: Optional[float] = None
    mfi: Optional[float] = None


class StockAnalysis(BaseModel):
    symbol: str
    price: float
    indicators: Indicators
    trend_analysis: Literal["bullish", "bearish", "neutral"]
    risk_level: Literal["low", "medium", "high"]


class PriceResponse(BaseModel):
    symbol: str
    price: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    version: str
