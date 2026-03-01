"""S&P 500 Signal Scanner — batch scans all S&P 500 stocks for signals."""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

import aiosqlite
import yfinance as yf

from app.analysis.indicators import calculate_indicators
from app.analysis.scoring import calculate_confidence, get_confidence_label
from app.analysis.signals import generate_signals
from app.data.cache import DB_PATH
from app.utils.logger import get_logger

logger = get_logger("scanner")

SP500_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "sp500_tickers.json"
BATCH_SIZE = 50


def _load_sp500() -> list[dict]:
    """Load the S&P 500 ticker list."""
    if not SP500_FILE.exists():
        logger.error(f"S&P 500 ticker file not found: {SP500_FILE}")
        return []
    with open(SP500_FILE) as f:
        return json.load(f)


async def _init_scanner_tables():
    """Create scanner tables if they don't exist."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scanner_results (
                symbol      TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                sector      TEXT,
                price       REAL,
                change_pct  REAL,
                signal      TEXT NOT NULL,
                confidence  INTEGER NOT NULL,
                indicators  TEXT NOT NULL,
                reasons     TEXT NOT NULL,
                scanned_at  REAL NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scanner_meta (
                id          INTEGER PRIMARY KEY CHECK (id = 1),
                last_scan   REAL,
                scan_status TEXT,
                progress    INTEGER,
                total       INTEGER,
                buy_count   INTEGER,
                sell_count  INTEGER,
                error_count INTEGER
            )
        """)
        # Insert default row if not exists
        await db.execute("""
            INSERT OR IGNORE INTO scanner_meta (id, last_scan, scan_status, progress, total, buy_count, sell_count, error_count)
            VALUES (1, 0, 'idle', 0, 0, 0, 0, 0)
        """)
        await db.commit()


async def _update_meta(**kwargs):
    """Update the scanner_meta singleton row."""
    if not kwargs:
        return
    sets = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values())
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(f"UPDATE scanner_meta SET {sets} WHERE id = 1", vals)
        await db.commit()


async def _save_result(result: dict):
    """Save a single scanner result to the database."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            INSERT OR REPLACE INTO scanner_results
            (symbol, name, sector, price, change_pct, signal, confidence, indicators, reasons, scanned_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result["symbol"], result["name"], result["sector"],
            result["price"], result["change_pct"],
            result["signal"], result["confidence"],
            json.dumps(result["indicators"], default=str),
            json.dumps(result["reasons"]),
            time.time(),
        ))
        await db.commit()


def _scan_batch_sync(symbols: list[str], ticker_info: dict) -> list[dict]:
    """Synchronously download and analyze a batch of tickers.

    Args:
        symbols: List of ticker symbols to scan.
        ticker_info: Dict mapping symbol -> {name, sector}.

    Returns:
        List of result dicts.
    """
    results = []

    try:
        # Batch download
        data = yf.download(
            symbols, period="1y", interval="1d",
            group_by="ticker", progress=False, threads=True,
        )
    except Exception as e:
        logger.error(f"Batch download failed: {e}")
        return results

    for sym in symbols:
        try:
            if len(symbols) == 1:
                df = data
            else:
                df = data[sym] if sym in data.columns.get_level_values(0) else None

            if df is None or df.empty or len(df) < 30:
                continue

            df = df.dropna(subset=["Close"])
            if len(df) < 30:
                continue

            # Build history list
            history = []
            for date, row in df.iterrows():
                history.append({
                    "date": str(date.date()) if hasattr(date, 'date') else str(date)[:10],
                    "open": round(float(row.get("Open", 0)), 2),
                    "high": round(float(row.get("High", 0)), 2),
                    "low": round(float(row.get("Low", 0)), 2),
                    "close": round(float(row.get("Close", 0)), 2),
                    "volume": int(row.get("Volume", 0)),
                })

            if not history:
                continue

            # Calculate indicators and signals
            indicators = calculate_indicators(history)
            if not indicators:
                continue

            sig = generate_signals(indicators)
            conf = calculate_confidence(
                sig["signal"], indicators, sig["buy_signals"], sig["sell_signals"]
            )

            current = float(df["Close"].iloc[-1])
            prev = float(df["Close"].iloc[-2]) if len(df) > 1 else current
            change_pct = ((current - prev) / prev * 100) if prev else 0

            info = ticker_info.get(sym, {})
            results.append({
                "symbol": sym,
                "name": info.get("name", sym),
                "sector": info.get("sector", ""),
                "price": round(current, 2),
                "change_pct": round(change_pct, 2),
                "signal": sig["signal"],
                "confidence": conf,
                "indicators": indicators,
                "reasons": sig.get("reasons", []),
                "buy_signals": sig.get("buy_signals", []),
                "sell_signals": sig.get("sell_signals", []),
            })

        except Exception as e:
            logger.debug(f"Scanner error for {sym}: {e}")

    return results


async def run_full_scan():
    """Run a full S&P 500 scan. This is a long-running operation (~10-15 min)."""
    await _init_scanner_tables()

    # Check if already running
    status = await get_scan_status()
    if status.get("scan_status") == "running":
        logger.warning("Scan already running, skipping")
        return

    tickers = _load_sp500()
    if not tickers:
        logger.error("No tickers to scan")
        return

    total = len(tickers)
    logger.info(f"Starting S&P 500 scan: {total} tickers")

    await _update_meta(scan_status="running", progress=0, total=total,
                       buy_count=0, sell_count=0, error_count=0)

    # Build lookup
    ticker_info = {t["symbol"]: t for t in tickers}
    symbols = [t["symbol"] for t in tickers]

    # Split into batches
    batches = [symbols[i:i + BATCH_SIZE] for i in range(0, len(symbols), BATCH_SIZE)]

    progress = 0
    buy_count = 0
    sell_count = 0
    error_count = 0
    consecutive_failures = 0

    for batch_idx, batch in enumerate(batches):
        try:
            results = await asyncio.to_thread(_scan_batch_sync, batch, ticker_info)

            for r in results:
                await _save_result(r)
                if r["signal"] == "BUY":
                    buy_count += 1
                elif r["signal"] == "SELL":
                    sell_count += 1

            batch_errors = len(batch) - len(results)
            error_count += batch_errors
            progress += len(batch)

            await _update_meta(progress=progress, buy_count=buy_count,
                               sell_count=sell_count, error_count=error_count)

            # Rate limit check
            if batch_errors > len(batch) * 0.2:
                consecutive_failures += 1
                if consecutive_failures >= 2:
                    logger.warning("High error rate, adding 30s cooldown")
                    await asyncio.sleep(30)
            else:
                consecutive_failures = 0

            logger.info(f"Scan progress: {progress}/{total} ({len(results)} results in batch {batch_idx + 1})")

            # Sleep between batches
            if batch_idx < len(batches) - 1:
                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f"Batch {batch_idx + 1} failed: {e}")
            error_count += len(batch)
            progress += len(batch)
            await _update_meta(progress=progress, error_count=error_count)

    await _update_meta(scan_status="complete", last_scan=time.time(),
                       progress=total)

    logger.info(f"Scan complete: {total} stocks, {buy_count} BUY, {sell_count} SELL, {error_count} errors")


async def get_scan_status() -> dict:
    """Get current scan status."""
    await _init_scanner_tables()
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute("SELECT * FROM scanner_meta WHERE id = 1")
            row = await cursor.fetchone()
            if row:
                return {
                    "last_scan": datetime.fromtimestamp(row[1]).isoformat() if row[1] else None,
                    "scan_status": row[2] or "idle",
                    "progress": row[3] or 0,
                    "total": row[4] or 0,
                    "buy_count": row[5] or 0,
                    "sell_count": row[6] or 0,
                    "error_count": row[7] or 0,
                }
    except Exception:
        pass
    return {"scan_status": "idle", "progress": 0, "total": 0,
            "buy_count": 0, "sell_count": 0, "error_count": 0, "last_scan": None}


async def get_scan_results(
    signal_filter: str = None,
    sector_filter: str = None,
    min_confidence: int = 50,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """Query scanner results from the database."""
    await _init_scanner_tables()

    conditions = []
    params = []

    if signal_filter:
        conditions.append("signal = ?")
        params.append(signal_filter.upper())

    if sector_filter:
        conditions.append("sector = ?")
        params.append(sector_filter)

    conditions.append("confidence >= ?")
    params.append(min_confidence)

    where = " AND ".join(conditions)

    async with aiosqlite.connect(str(DB_PATH)) as db:
        # Total count
        cursor = await db.execute(
            f"SELECT COUNT(*) FROM scanner_results WHERE {where}", params
        )
        total = (await cursor.fetchone())[0]

        # Results
        cursor = await db.execute(
            f"""SELECT symbol, name, sector, price, change_pct, signal, confidence,
                       indicators, reasons, scanned_at
                FROM scanner_results
                WHERE {where}
                ORDER BY confidence DESC
                LIMIT ? OFFSET ?""",
            params + [limit, offset],
        )
        rows = await cursor.fetchall()

    results = []
    for r in rows:
        conf_label = get_confidence_label(r[6])
        results.append({
            "symbol": r[0],
            "name": r[1],
            "sector": r[2],
            "price": r[3],
            "change_pct": r[4],
            "signal": r[5],
            "confidence": r[6],
            "confidence_label": conf_label,
            "reasons": json.loads(r[8]) if r[8] else [],
            "scanned_at": datetime.fromtimestamp(r[9]).isoformat() if r[9] else None,
        })

    meta = await get_scan_status()

    return {
        "results": results,
        "total_results": total,
        "page": {"limit": limit, "offset": offset},
        "scan_meta": meta,
    }


async def get_sectors() -> list[dict]:
    """Get list of sectors with counts from scanner results."""
    await _init_scanner_tables()
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                "SELECT sector, COUNT(*) FROM scanner_results GROUP BY sector ORDER BY COUNT(*) DESC"
            )
            rows = await cursor.fetchall()
            return [{"sector": r[0], "count": r[1]} for r in rows if r[0]]
    except Exception:
        return []
