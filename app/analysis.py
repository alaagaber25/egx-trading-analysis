from typing import Literal, Optional


def interpret_trend(
    price: float,
    indicators: dict,
) -> Literal["bullish", "bearish", "neutral"]:
    """
    Score-based trend classification using price vs. moving averages,
    RSI zone, MACD crossover, and ADX trend strength.
    """
    score = 0

    rsi: Optional[float] = indicators.get("rsi")
    macd: Optional[float] = indicators.get("macd")
    macd_signal: Optional[float] = indicators.get("macd_signal")
    ema20: Optional[float] = indicators.get("ema20")
    ema50: Optional[float] = indicators.get("ema50")
    adx: Optional[float] = indicators.get("adx")

    if ema20 is not None:
        score += 1 if price > ema20 else -1

    if ema50 is not None:
        score += 1 if price > ema50 else -1

    if rsi is not None:
        if 50 < rsi <= 70:
            score += 1
        elif rsi < 40:
            score -= 1
        elif rsi > 70:
            # Overbought — not a clear bullish signal
            score += 0

    if macd is not None and macd_signal is not None:
        score += 1 if macd > macd_signal else -1

    # ADX > 25 confirms a strong trend; amplify the existing directional signal
    if adx is not None and adx > 25 and score != 0:
        score = score * 2

    if score >= 2:
        return "bullish"
    if score <= -2:
        return "bearish"
    return "neutral"


def interpret_risk(
    price: float,
    indicators: dict,
) -> Literal["low", "medium", "high"]:
    """
    Risk classification based on RSI extremes, ADX volatility, and ATR% of price.
    """
    rsi: Optional[float] = indicators.get("rsi")
    adx: Optional[float] = indicators.get("adx")
    atr: Optional[float] = indicators.get("atr")

    risk_score = 0

    if rsi is not None:
        if rsi > 75 or rsi < 25:
            risk_score += 2
        elif rsi > 65 or rsi < 35:
            risk_score += 1

    if adx is not None:
        if adx > 40:
            risk_score += 2
        elif adx > 25:
            risk_score += 1

    if atr is not None and price > 0:
        atr_pct = (atr / price) * 100
        if atr_pct > 3.0:
            risk_score += 2
        elif atr_pct > 1.5:
            risk_score += 1

    if risk_score >= 4:
        return "high"
    if risk_score >= 2:
        return "medium"
    return "low"
