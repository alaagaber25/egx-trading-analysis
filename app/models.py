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
    indicators: Optional[Indicators] = None
    trend_analysis: Optional[Literal["bullish", "bearish", "neutral"]] = None
    risk_level: Optional[Literal["low", "medium", "high"]] = None
    message: Optional[str] = None


class PriceResponse(BaseModel):
    symbol: str
    price: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    volume: Optional[float] = None


class HealthResponse(BaseModel):
    status: str
    version: str
