# EGX Trading Analysis API

A FastAPI-powered technical analysis engine for the Egyptian Stock Exchange (EGX). Real-time OHLCV data, momentum indicators, trend analysis, and risk assessment designed for algorithmic trading systems.

## Features

- **Real-time Data**: Fetch OHLCV data and current price information from yfinance
- **Technical Indicators**: RSI, MACD, ADX, ATR, EMA20, EMA50, SMA200, RMI
- **Trend Interpretation**: AI-ready trend signals based on price action, momentum, and trend strength
- **Risk Assessment**: Risk scoring combining RSI extremes, ADX magnitude, and volatility
- **Robust Error Handling**: Graceful degradation — one failed indicator doesn't crash the entire response
- **Type Safety**: Fully typed with Pydantic schemas for predictable API responses
- **Docker Ready**: Containerized deployment with optimized Dockerfile

## Quick Start

### Installation

**Requirements**: Python 3.12–3.13, pip or uv

```bash
# Install dependencies
pip install -r pyproject.toml

# Or with uv (recommended for faster installs)
uv pip install -r pyproject.toml
```

### Run Locally

```bash
# Start the FastAPI server
python -m uvicorn main:app --reload

# Server runs on http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Docker

```bash
# Build the image
docker build -t egx-app .

# Run the container
docker run -p 8000:8000 egx-app
```

## API Endpoints

### `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### `/analyze/{symbol}`

Main analysis endpoint. Returns full technical analysis for a stock symbol.

**Parameters:**
- `symbol` (path): Stock symbol, 2–6 uppercase letters (e.g., `FWRY`, `COMI`)
- `period` (query): Data lookback period. Default: `2y`. Options: `1mo`, `3mo`, `6mo`, `1y`, `2y`

**Response:**
```json
{
  "symbol": "FWRY",
  "period": "2y",
  "price": {
    "current": 123.45,
    "change": 2.3,
    "change_percent": 1.9,
    "market_cap": null,
    "pe_ratio": 12.5,
    "dividend_yield": null
  },
  "indicators": {
    "rsi": 65.3,
    "macd": 0.45,
    "macd_signal": 0.42,
    "adx": 28.5,
    "atr": 1.2,
    "ema_20": 120.5,
    "ema_50": 119.3,
    "sma_200": 115.2,
    "rmi": 58.7
  },
  "trend": {
    "direction": "bullish",
    "strength": "moderate",
    "confidence": 0.75
  },
  "risk": {
    "level": "moderate",
    "score": 0.55,
    "volatility_pct": 2.1
  }
}
```

**Status Codes:**
- `200`: Success
- `404`: Symbol not found or no data available
- `422`: Invalid symbol or period format
- `502`: Upstream data provider error
- `500`: Computation or data processing error

## Architecture

### File Structure

```
app/
├── __init__.py
├── models.py      ← Pydantic schemas (type-safe responses)
├── data.py        ← yfinance layer (OHLCV + price info)
├── indicators.py  ← all indicator computations
└── analysis.py    ← trend/risk interpretation logic
main.py            ← FastAPI app (routes only)
```

### Data Flow

1. **API Request** → `main.py` validates symbol & period
2. **Data Layer** → `data.py` fetches OHLCV and price info from yfinance
3. **Indicators** → `indicators.py` computes 8+ technical indicators in parallel
4. **Analysis** → `analysis.py` interprets trend/risk from indicator scores
5. **Response** → `models.py` Pydantic schemas ensure type safety

## Recent Improvements

### Bug Fixes

- **Fast Info Attributes**: Replaced dict-style `get("lastPrice")` with safe `getattr(info, "last_price")` using correct snake_case yfinance attributes
- **RMI Division by Zero**: Added `avg_down.replace(0, np.nan)` before dividing to prevent crashes
- **SMA200 Warmup**: Each indicator now computes independently; only `Close` NaN rows are dropped instead of killing recent rows
- **Error Responses**: Structured HTTP status codes — data errors → 404, upstream failures → 502, computation errors → 500

### New Features

- **Pydantic Models**: `StockAnalysis`, `Indicators`, `PriceResponse`, `HealthResponse` with full type hints
- **Safe Indicator Computation**: Each indicator wrapped in try/except; failures return `null` instead of crashing
- **Trend Scoring**: Score-based interpretation using price vs EMA20/EMA50, RSI zones, MACD crossover, ADX strength
- **Risk Scoring**: Combines RSI extremes, ADX magnitude, and ATR volatility percentage
- **Request Logging**: Structured logs on every request/error for debugging and monitoring

## Usage Examples

### Python

```python
import requests

response = requests.get(
    "http://localhost:8000/analyze/FWRY",
    params={"period": "1y"}
)
analysis = response.json()

print(f"Trend: {analysis['trend']['direction']}")
print(f"Risk Level: {analysis['risk']['level']}")
print(f"RSI: {analysis['indicators']['rsi']}")
```

### curl

```bash
# Fetch 2-year analysis for FWRY
curl "http://localhost:8000/analyze/FWRY?period=2y"

# Quick 1-month snapshot
curl "http://localhost:8000/analyze/COMI?period=1mo"

# Check API health
curl "http://localhost:8000/health"
```

### JavaScript/Node.js

```javascript
const response = await fetch('http://localhost:8000/analyze/FWRY?period=2y');
const data = await response.json();

console.log(`${data.symbol} trend: ${data.trend.direction}`);
console.log(`Current price: ${data.price.current}`);
```

## Indicators

| Indicator | Type | Interpretation |
|-----------|------|-----------------|
| **RSI** | Momentum | 0–30 oversold, 70–100 overbought, 30–70 neutral |
| **MACD** | Momentum | Signal crossover = trend change; histogram = momentum |
| **ADX** | Trend Strength | >20 strong, <20 weak trend |
| **ATR** | Volatility | Higher = more volatility; normalized by price |
| **EMA20/50** | Short-term Trend | Price > EMA = bullish; Price < EMA = bearish |
| **SMA200** | Long-term Trend | Major support/resistance; >200-bar setup |
| **RMI** | Risk-adjusted Momentum | Alternative to RSI; smoother response |

## Trend Signal Interpretation

**Direction**: `bullish`, `bearish`, or `neutral`  
**Strength**: `weak`, `moderate`, or `strong`  
**Confidence**: 0.0–1.0 based on indicator alignment

Scoring considers:
- Price position vs EMA20/EMA50/SMA200
- RSI zone (oversold/neutral/overbought)
- MACD crossover and histogram direction
- ADX strength amplifier

## Risk Assessment

**Risk Level**: `low`, `moderate`, or `high`  
**Score**: 0.0–1.0  
**Volatility %**: ATR as percentage of current price

Risk combines:
- RSI extremes (< 30 or > 70 = elevated risk)
- ADX magnitude (higher = more volatile)
- ATR volatility metric

## Development

### Project Structure

- `pyproject.toml`: Dependencies and project metadata
- `Dockerfile`: Multi-stage build for production
- `main.py`: FastAPI app, routes, validation
- `app/models.py`: Pydantic schemas
- `app/data.py`: yfinance data layer
- `app/indicators.py`: Technical indicator calculations
- `app/analysis.py`: Trend and risk interpretation

### Testing

Run the interactive API docs:

```bash
# Swagger UI
http://localhost:8000/docs

# ReDoc
http://localhost:8000/redoc
```

### Logging

All requests and errors are logged with timestamps and context:

```
2025-06-03 10:15:22,123 INFO app: GET /analyze/FWRY?period=2y
2025-06-03 10:15:23,456 INFO app: Computed 8 indicators in 1.33s
```

## Error Handling

The API provides descriptive error messages:

```json
{
  "detail": "Invalid symbol 'XY'. Expected 2-6 uppercase letters (e.g. FWRY, COMI)."
}
```

Common errors:
- **422**: Invalid symbol format or unsupported period
- **404**: Symbol not found or no historical data
- **502**: yfinance or upstream provider unavailable
- **500**: Internal computation error (logged for debugging)

## Performance Notes

- **SMA200 Warmup**: Default 2-year lookback ensures sufficient bars for SMA200
- **Indicator Caching**: Consider caching responses for frequently requested symbols
- **Timeout**: yfinance requests timeout after 30 seconds
- **Data Lag**: End-of-day OHLCV updates after market close; intraday quotes have ~15-min lag

## Supported EGX Symbols

Common Egyptian stocks (2–6 uppercase letters):
- `FWRY` – Futuristic Furnishing & Wooden Industries
- `COMI` – Commercial International Bank
- `CLCH` – Cleopatra Hospitals
- `AUTO` – Egyptian American Vehicles Company
- And many more...

## License

This project is provided as-is for educational and trading analysis purposes.

## Support

For issues, feature requests, or questions, please open an issue in the repository.

---

**Version**: 1.0.0  
**Last Updated**: June 3, 2026