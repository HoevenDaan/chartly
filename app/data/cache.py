"""SQLite caching layer for API responses."""

import json
import time
from pathlib import Path
from typing import Optional

import aiosqlite

from app.utils.logger import get_logger

logger = get_logger("cache")

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "stockpulse.db"


async def init_db():
    """Initialize the SQLite database with required tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stock_cache (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                timestamp REAL NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                symbol TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                added_at REAL NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS backtest_cache (
                symbol TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                computed_at REAL NOT NULL
            )
        """)
        await db.commit()
    logger.info(f"Database initialized at {DB_PATH}")


async def get_cached(key: str, ttl_minutes: int = 15) -> Optional[dict]:
    """Get cached data if it exists and is not expired."""
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                "SELECT data, timestamp FROM stock_cache WHERE key = ?", (key,)
            )
            row = await cursor.fetchone()
            if row:
                data, ts = row
                age_minutes = (time.time() - ts) / 60
                if age_minutes < ttl_minutes:
                    logger.debug(f"Cache hit for {key} (age: {age_minutes:.1f}m)")
                    return json.loads(data)
                logger.debug(f"Cache expired for {key} (age: {age_minutes:.1f}m)")
            return None
    except Exception as e:
        logger.error(f"Cache read error for {key}: {e}")
        return None


async def set_cached(key: str, data: dict):
    """Store data in cache."""
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT OR REPLACE INTO stock_cache (key, data, timestamp) VALUES (?, ?, ?)",
                (key, json.dumps(data, default=str), time.time()),
            )
            await db.commit()
        logger.debug(f"Cached data for {key}")
    except Exception as e:
        logger.error(f"Cache write error for {key}: {e}")


async def get_watchlist() -> list[dict]:
    """Get all stocks in the watchlist."""
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                "SELECT symbol, name FROM watchlist ORDER BY added_at"
            )
            rows = await cursor.fetchall()
            return [{"symbol": r[0], "name": r[1]} for r in rows]
    except Exception:
        return []


async def add_to_watchlist(symbol: str, name: str):
    """Add a stock to the watchlist."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute(
            "INSERT OR REPLACE INTO watchlist (symbol, name, added_at) VALUES (?, ?, ?)",
            (symbol.upper(), name, time.time()),
        )
        await db.commit()
    logger.info(f"Added {symbol} to watchlist")


async def remove_from_watchlist(symbol: str):
    """Remove a stock from the watchlist."""
    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.execute("DELETE FROM watchlist WHERE symbol = ?", (symbol.upper(),))
        await db.commit()
    logger.info(f"Removed {symbol} from watchlist")


async def get_backtest_cached(symbol: str, ttl_seconds: int = 86400) -> Optional[dict]:
    """Get cached backtest result if not expired (default 24h TTL)."""
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            cursor = await db.execute(
                "SELECT data, computed_at FROM backtest_cache WHERE symbol = ?",
                (symbol.upper(),),
            )
            row = await cursor.fetchone()
            if row:
                data, ts = row
                if (time.time() - ts) < ttl_seconds:
                    return json.loads(data)
    except Exception as e:
        logger.error(f"Backtest cache read error for {symbol}: {e}")
    return None


async def set_backtest_cached(symbol: str, data: dict):
    """Store backtest result in cache."""
    try:
        async with aiosqlite.connect(str(DB_PATH)) as db:
            await db.execute(
                "INSERT OR REPLACE INTO backtest_cache (symbol, data, computed_at) VALUES (?, ?, ?)",
                (symbol.upper(), json.dumps(data, default=str), time.time()),
            )
            await db.commit()
    except Exception as e:
        logger.error(f"Backtest cache write error for {symbol}: {e}")
