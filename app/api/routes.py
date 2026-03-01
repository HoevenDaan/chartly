"""REST API endpoints for StockPulse."""

import asyncio
import csv
import io
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.analysis.advisor import DISCLAIMER, analyze_all, analyze_stock
from app.analysis.backtester import run_backtest
from app.config import get_settings
from app.data import cache
from app.data.fetcher import fetch_all_stocks, fetch_stock_data
from app.scanner.scanner import (
    get_scan_results, get_scan_status, get_sectors, run_full_scan,
)
from app.utils.logger import get_logger

logger = get_logger("api")
router = APIRouter(prefix="/api")


def _response(data, status="success"):
    return {
        "status": status,
        "data": data,
        "timestamp": datetime.now().isoformat(),
    }


def _error(message: str, code: int = 400):
    return {
        "status": "error",
        "message": message,
        "code": code,
    }


@router.get("/health")
async def health_check():
    return _response({"healthy": True, "version": "1.0.0"})


@router.get("/stocks")
async def get_stocks():
    """List all watched stocks with current data and analysis."""
    try:
        watchlist = await _get_watchlist_symbols()
        stocks_data = await fetch_all_stocks(watchlist)
        reports = analyze_all(stocks_data)
        return _response(reports)
    except Exception as e:
        logger.error(f"Error fetching stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks/{symbol}")
async def get_stock(symbol: str):
    """Detailed data for one stock."""
    try:
        data = await fetch_stock_data(symbol.upper())
        report = analyze_stock(data)
        return _response(report)
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        raise HTTPException(status_code=404, detail=f"Stock '{symbol}' not found or unavailable: {e}")


@router.get("/stocks/{symbol}/history")
async def get_stock_history(symbol: str):
    """Historical price data for charts."""
    try:
        data = await fetch_stock_data(symbol.upper())
        return _response({
            "symbol": symbol.upper(),
            "history": data.get("history", []),
        })
    except Exception as e:
        logger.error(f"Error fetching history for {symbol}: {e}")
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/stocks/{symbol}/analysis")
async def get_stock_analysis(symbol: str):
    """Full technical analysis + signals for one stock."""
    try:
        data = await fetch_stock_data(symbol.upper())
        report = analyze_stock(data)
        report["disclaimer"] = DISCLAIMER
        return _response(report)
    except Exception as e:
        logger.error(f"Error analyzing {symbol}: {e}")
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/signals")
async def get_all_signals():
    """All current signals across watchlist."""
    try:
        watchlist = await _get_watchlist_symbols()
        stocks_data = await fetch_all_stocks(watchlist)
        reports = analyze_all(stocks_data)
        signals = [{
            "symbol": r["symbol"],
            "name": r.get("name", r["symbol"]),
            "price": r.get("price", 0),
            "signal": r["signal"],
            "confidence": r["confidence"],
            "confidence_label": r.get("confidence_label", {}),
            "reasons": r.get("reasons", []),
        } for r in reports]
        return _response({"signals": signals, "disclaimer": DISCLAIMER})
    except Exception as e:
        logger.error(f"Error fetching signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals/active")
async def get_active_signals():
    """Only actionable signals above confidence threshold."""
    try:
        settings = get_settings()
        min_conf = settings.analysis.signals.min_confidence
        watchlist = await _get_watchlist_symbols()
        stocks_data = await fetch_all_stocks(watchlist)
        reports = analyze_all(stocks_data)
        active = [r for r in reports if r["signal"] != "HOLD" and r["confidence"] >= min_conf]
        active.sort(key=lambda x: x["confidence"], reverse=True)
        return _response({
            "signals": [{
                "symbol": r["symbol"],
                "name": r.get("name", r["symbol"]),
                "price": r.get("price", 0),
                "signal": r["signal"],
                "confidence": r["confidence"],
                "confidence_label": r.get("confidence_label", {}),
                "reasons": r.get("reasons", []),
                "summary": r.get("summary", ""),
            } for r in active],
            "disclaimer": DISCLAIMER,
        })
    except Exception as e:
        logger.error(f"Error fetching active signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_stocks(q: str = ""):
    """Search for stocks by symbol or name using Yahoo Finance."""
    query = q.strip()
    if len(query) < 1:
        return _response([])

    try:
        import asyncio
        import requests as req

        def _search():
            url = "https://query1.finance.yahoo.com/v1/finance/search"
            params = {
                "q": query,
                "quotesCount": 8,
                "newsCount": 0,
                "listsCount": 0,
            }
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = req.get(url, params=params, headers=headers, timeout=5)
            data = resp.json()
            results = []
            for quote in data.get("quotes", []):
                if quote.get("quoteType") in ("EQUITY", "ETF"):
                    results.append({
                        "symbol": quote.get("symbol", ""),
                        "name": quote.get("longname") or quote.get("shortname") or quote.get("symbol", ""),
                        "exchange": quote.get("exchDisp", ""),
                        "type": quote.get("quoteType", ""),
                    })
            return results

        results = await asyncio.to_thread(_search)
        return _response(results)
    except Exception as e:
        logger.warning(f"Stock search failed: {e}")
        return _response([])


class WatchlistAdd(BaseModel):
    symbol: str
    name: str = ""


@router.post("/watchlist")
async def add_watchlist(item: WatchlistAdd):
    """Add a stock to the watchlist."""
    symbol = item.symbol.upper().strip()
    if not symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")

    name = item.name or symbol
    # Verify the symbol exists by fetching data
    try:
        data = await fetch_stock_data(symbol)
        name = data.get("info", {}).get("name", name)
    except Exception:
        logger.warning(f"Could not verify symbol {symbol}, adding anyway")

    await cache.add_to_watchlist(symbol, name)
    return _response({"symbol": symbol, "name": name, "added": True})


@router.delete("/watchlist/{symbol}")
async def remove_watchlist(symbol: str):
    """Remove a stock from the watchlist."""
    await cache.remove_from_watchlist(symbol.upper())
    return _response({"symbol": symbol.upper(), "removed": True})


@router.get("/config")
async def get_config():
    """Current config (safe fields only, no API keys)."""
    settings = get_settings()
    return _response({
        "app": settings.app.model_dump(),
        "watchlist": settings.watchlist.model_dump(),
        "data": settings.data.model_dump(),
        "analysis": settings.analysis.model_dump(),
        "scheduler": settings.scheduler.model_dump(),
        "notifications": {
            "whatsapp": {
                "enabled": settings.notifications.whatsapp.enabled,
                "daily_summary": settings.notifications.whatsapp.daily_summary,
                "signal_alerts": settings.notifications.whatsapp.signal_alerts,
            }
        },
    })


@router.post("/refresh")
async def force_refresh():
    """Force data refresh for all stocks."""
    try:
        watchlist = await _get_watchlist_symbols()
        stocks_data = await fetch_all_stocks(watchlist)
        reports = analyze_all(stocks_data)
        return _response({
            "refreshed": len(reports),
            "stocks": [r["symbol"] for r in reports],
        })
    except Exception as e:
        logger.error(f"Error refreshing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _get_watchlist_symbols() -> list[dict]:
    """Get the combined watchlist from DB + config defaults."""
    settings = get_settings()
    db_watchlist = await cache.get_watchlist()

    if db_watchlist:
        return db_watchlist

    # Use defaults from config
    return [s.model_dump() for s in settings.watchlist.default_stocks]


# ─── Backtester Endpoints ───


@router.get("/stocks/{symbol}/backtest")
async def get_backtest(symbol: str, refresh: bool = False):
    """Run a backtest for a stock using historical data."""
    symbol = symbol.upper()
    try:
        # Check cache first
        if not refresh:
            cached = await cache.get_backtest_cached(symbol)
            if cached:
                return _response(cached)

        # Fetch data and run backtest
        data = await fetch_stock_data(symbol)
        history = data.get("history", [])

        result = await asyncio.to_thread(run_backtest, symbol, history)

        if "error" not in result or not result.get("error"):
            await cache.set_backtest_cached(symbol, result)

        return _response(result)
    except Exception as e:
        logger.error(f"Backtest error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stocks/{symbol}/backtest/export")
async def export_backtest_csv(symbol: str):
    """Export backtest trades as CSV."""
    symbol = symbol.upper()
    try:
        cached = await cache.get_backtest_cached(symbol)
        if not cached:
            data = await fetch_stock_data(symbol)
            cached = await asyncio.to_thread(run_backtest, symbol, data.get("history", []))

        trades = cached.get("trades", [])
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "entry_date", "exit_date", "entry_price", "exit_price",
            "return_pct", "return_dollars", "holding_days", "exit_reason",
        ])
        writer.writeheader()
        for t in trades:
            writer.writerow(t)

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=backtest_{symbol}.csv"},
        )
    except Exception as e:
        logger.error(f"Backtest export error for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── Scanner Endpoints ───


@router.get("/scanner/status")
async def scanner_status():
    """Get current scan status."""
    status = await get_scan_status()
    return _response(status)


@router.get("/scanner/results")
async def scanner_results(
    signal: str = Query(None, description="Filter by signal: BUY, SELL, HOLD"),
    sector: str = Query(None, description="Filter by GICS sector"),
    min_confidence: int = Query(50, ge=0, le=100),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get scanner results with filters."""
    data = await get_scan_results(
        signal_filter=signal,
        sector_filter=sector,
        min_confidence=min_confidence,
        limit=limit,
        offset=offset,
    )
    return _response(data)


@router.get("/scanner/sectors")
async def scanner_sectors():
    """Get list of sectors from scanner results."""
    sectors = await get_sectors()
    return _response(sectors)


@router.post("/scanner/run")
async def trigger_scan():
    """Trigger a full S&P 500 scan. Returns immediately."""
    status = await get_scan_status()
    if status.get("scan_status") == "running":
        raise HTTPException(status_code=409, detail="Scan already running")

    # Run in background
    asyncio.create_task(run_full_scan())
    return _response({"message": "Scan started", "status": "running"}, status="success")
