"""
Path 1 — Local MCP server for Claude Desktop (stdio transport).

Claude Desktop starts this as a subprocess. It calls the running FastAPI service
over HTTP and exposes two tools: analyze_stock and get_price.

Configure via environment variable:
    EGX_API_URL   Base URL of the FastAPI service (default: http://localhost:2552)

Claude Desktop config entry (~\\AppData\\Roaming\\Claude\\claude_desktop_config.json):
    {
      "mcpServers": {
        "egx-trading": {
          "command": "uv",
          "args": ["run", "mcp_server.py"],
          "cwd": "C:\\\\Users\\\\voom-ai\\\\Desktop\\\\egx-trading-analysis",
          "env": { "EGX_API_URL": "http://localhost:2552" }
        }
      }
    }
"""

import json
import os

import httpx
from mcp.server.fastmcp import FastMCP

API_BASE = os.getenv("EGX_API_URL", "http://localhost:2552").rstrip("/")

mcp = FastMCP(
    "EGX Trading Analysis",
    instructions=(
        "Tools for analyzing Egyptian Stock Exchange (EGX) stocks. "
        "Ticker symbols must be provided WITHOUT the .CA suffix (e.g. FWRY, COMI, HRHO, ETEL). "
        "Use analyze_stock for full technical analysis; use get_price for a quick real-time quote."
    ),
)


@mcp.tool()
async def analyze_stock(symbol: str, period: str = "2y") -> str:
    """
    Run full technical analysis on an Egyptian stock (EGX).

    Returns indicators (RSI, RMI, MACD, EMA20, EMA50, SMA200, ATR, ADX, OBV, MFI),
    trend direction (bullish / bearish / neutral), and risk level (low / medium / high).

    Args:
        symbol: EGX ticker WITHOUT .CA suffix — e.g. FWRY, COMI, HRHO, ETEL, EFIH
        period: Historical window for indicator calculation.
                Options: 1mo, 3mo, 6mo, 1y, 2y (default: 2y).
                Use 2y for best SMA200 accuracy.
    """
    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await client.get(
            f"{API_BASE}/analyze/{symbol.upper().strip()}",
            params={"period": period},
        )

    if resp.status_code == 404:
        return json.dumps({"error": f"No market data found for {symbol}. Check the ticker symbol."})
    if resp.status_code == 422:
        detail = resp.json().get("detail", resp.text)
        return json.dumps({"error": f"Invalid input: {detail}"})
    if not resp.is_success:
        return json.dumps({"error": f"API error {resp.status_code}: {resp.text}"})

    return json.dumps(resp.json(), indent=2, ensure_ascii=False)


@mcp.tool()
async def get_price(symbol: str) -> str:
    """
    Get a real-time price quote for an Egyptian stock (EGX).

    Returns the last traded price, day high, day low, and last volume.

    Args:
        symbol: EGX ticker WITHOUT .CA suffix — e.g. FWRY, COMI, HRHO, ETEL, EFIH
    """
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{API_BASE}/price/{symbol.upper().strip()}")

    if resp.status_code == 422:
        detail = resp.json().get("detail", resp.text)
        return json.dumps({"error": f"Invalid input: {detail}"})
    if not resp.is_success:
        return json.dumps({"error": f"API error {resp.status_code}: {resp.text}"})

    return json.dumps(resp.json(), indent=2, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()  # stdio transport — Claude Desktop manages the process lifecycle
