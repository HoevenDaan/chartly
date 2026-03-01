"""Stock data fetching with yfinance primary and Alpha Vantage fallback."""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from app.config import get_settings
from app.data import cache
from app.data.models import OHLCVData, StockInfo, StockPrice
from app.utils.exceptions import DataFetchError
from app.utils.logger import get_logger

logger = get_logger("fetcher")


def _is_market_open() -> bool:
    """Check if US stock market is currently open (rough check)."""
    now = datetime.utcnow()
    # Market hours: Mon-Fri 14:30-21:00 UTC (9:30 AM - 4:00 PM ET)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=14, minute=30, second=0)
    market_close = now.replace(hour=21, minute=0, second=0)
    return market_open <= now <= market_close


def _fetch_yfinance(symbol: str, period: str = "1y", interval: str = "1d") -> dict:
    """Fetch stock data from yfinance with retry logic."""
    settings = get_settings()
    max_retries = 3
    delays = [2, 4, 8]

    for attempt in range(max_retries):
        try:
            logger.debug(f"yfinance fetch attempt {attempt + 1} for {symbol}")
            ticker = yf.Ticker(symbol)

            # Get historical data
            hist = ticker.history(period=period, interval=interval)
            if hist.empty:
                raise DataFetchError(f"No data returned for {symbol}")

            # Get info
            info = ticker.info or {}

            # Build OHLCV list
            history = []
            for date, row in hist.iterrows():
                history.append({
                    "date": str(date.date()) if hasattr(date, 'date') else str(date)[:10],
                    "open": round(float(row.get("Open", 0)), 2),
                    "high": round(float(row.get("High", 0)), 2),
                    "low": round(float(row.get("Low", 0)), 2),
                    "close": round(float(row.get("Close", 0)), 2),
                    "volume": int(row.get("Volume", 0)),
                })

            # Current price data
            latest = hist.iloc[-1]
            prev_close = hist.iloc[-2]["Close"] if len(hist) > 1 else latest["Close"]
            current_price = float(latest["Close"])
            change = current_price - float(prev_close)
            change_pct = (change / float(prev_close)) * 100 if prev_close else 0

            result = {
                "info": {
                    "symbol": symbol.upper(),
                    "name": info.get("longName", info.get("shortName", symbol)),
                    "sector": info.get("sector"),
                    "market_cap": info.get("marketCap"),
                    "pe_ratio": info.get("trailingPE"),
                    "week_52_high": info.get("fiftyTwoWeekHigh"),
                    "week_52_low": info.get("fiftyTwoWeekLow"),
                },
                "price": {
                    "symbol": symbol.upper(),
                    "price": round(current_price, 2),
                    "change": round(change, 2),
                    "change_percent": round(change_pct, 2),
                    "volume": int(latest.get("Volume", 0)),
                    "timestamp": datetime.now().isoformat(),
                    "market_open": _is_market_open(),
                },
                "history": history,
            }

            logger.info(f"Successfully fetched {symbol} from yfinance ({len(history)} bars)")
            return result

        except Exception as e:
            logger.warning(f"yfinance attempt {attempt + 1} failed for {symbol}: {e}")
            if attempt < max_retries - 1:
                time.sleep(delays[attempt])

    raise DataFetchError(f"yfinance failed after {max_retries} retries for {symbol}")


def _fetch_alphavantage(symbol: str) -> dict:
    """Fetch stock data from Alpha Vantage as fallback."""
    settings = get_settings()
    api_key = settings.alpha_vantage_api_key
    if not api_key:
        raise DataFetchError("Alpha Vantage API key not configured")

    try:
        # Daily data
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=full&apikey={api_key}"
        resp = requests.get(url, timeout=30)
        data = resp.json()

        if "Time Series (Daily)" not in data:
            raise DataFetchError(f"Alpha Vantage error: {data.get('Note', data.get('Error Message', 'Unknown'))}")

        ts = data["Time Series (Daily)"]
        dates = sorted(ts.keys())[-252:]  # ~1 year

        history = []
        for d in dates:
            bar = ts[d]
            history.append({
                "date": d,
                "open": round(float(bar["1. open"]), 2),
                "high": round(float(bar["2. high"]), 2),
                "low": round(float(bar["3. low"]), 2),
                "close": round(float(bar["4. close"]), 2),
                "volume": int(float(bar["5. volume"])),
            })

        latest = history[-1]
        prev = history[-2] if len(history) > 1 else latest
        change = latest["close"] - prev["close"]
        change_pct = (change / prev["close"]) * 100 if prev["close"] else 0

        # Overview for info
        ov_url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={api_key}"
        ov_resp = requests.get(ov_url, timeout=30)
        ov = ov_resp.json()

        result = {
            "info": {
                "symbol": symbol.upper(),
                "name": ov.get("Name", symbol),
                "sector": ov.get("Sector"),
                "market_cap": float(ov["MarketCapitalization"]) if ov.get("MarketCapitalization") else None,
                "pe_ratio": float(ov["TrailingPE"]) if ov.get("TrailingPE") and ov["TrailingPE"] != "None" else None,
                "week_52_high": float(ov["52WeekHigh"]) if ov.get("52WeekHigh") else None,
                "week_52_low": float(ov["52WeekLow"]) if ov.get("52WeekLow") else None,
            },
            "price": {
                "symbol": symbol.upper(),
                "price": latest["close"],
                "change": round(change, 2),
                "change_percent": round(change_pct, 2),
                "volume": latest["volume"],
                "timestamp": datetime.now().isoformat(),
                "market_open": _is_market_open(),
            },
            "history": history,
        }
        logger.info(f"Successfully fetched {symbol} from Alpha Vantage ({len(history)} bars)")
        return result

    except DataFetchError:
        raise
    except Exception as e:
        raise DataFetchError(f"Alpha Vantage failed for {symbol}: {e}")


async def fetch_stock_data(symbol: str) -> dict:
    """Fetch stock data with caching and fallback logic."""
    settings = get_settings()
    cache_key = f"stock_data:{symbol.upper()}"

    # Try cache first
    cached = await cache.get_cached(cache_key, settings.data.cache_ttl_minutes)
    if cached:
        return cached

    # Try primary source (yfinance) in a thread
    try:
        data = await asyncio.to_thread(
            _fetch_yfinance, symbol, settings.data.history_period
        )
        await cache.set_cached(cache_key, data)
        return data
    except DataFetchError as e:
        logger.warning(f"Primary source failed for {symbol}: {e}")

    # Try fallback (Alpha Vantage)
    try:
        data = await asyncio.to_thread(_fetch_alphavantage, symbol)
        await cache.set_cached(cache_key, data)
        return data
    except DataFetchError as e:
        logger.warning(f"Fallback source failed for {symbol}: {e}")

    # Try stale cache as last resort
    stale = await cache.get_cached(cache_key, ttl_minutes=999999)
    if stale:
        stale["_stale"] = True
        logger.warning(f"Serving stale cached data for {symbol}")
        return stale

    raise DataFetchError(f"All data sources failed for {symbol}")


async def fetch_all_stocks(symbols: list[dict]) -> list[dict]:
    """Fetch data for all watched stocks, continuing even if some fail."""
    results = []
    for stock in symbols:
        try:
            data = await fetch_stock_data(stock["symbol"])
            results.append(data)
        except Exception as e:
            logger.error(f"Failed to fetch {stock['symbol']}: {e}")
            results.append({
                "info": {"symbol": stock["symbol"], "name": stock.get("name", stock["symbol"])},
                "price": {
                    "symbol": stock["symbol"],
                    "price": 0,
                    "change": 0,
                    "change_percent": 0,
                    "volume": 0,
                    "timestamp": datetime.now().isoformat(),
                    "market_open": _is_market_open(),
                },
                "history": [],
                "_error": str(e),
            })
    return results
