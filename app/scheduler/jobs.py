"""Background scheduled tasks for data refresh and signal checks."""

import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.analysis.advisor import analyze_all
from app.api.routes import _get_watchlist_symbols
from app.config import get_settings
from app.data.fetcher import fetch_all_stocks
from app.notifications.whatsapp import send_daily_summary, send_scanner_summary, send_signal_alert
from app.scanner.scanner import get_scan_results, get_scan_status, run_full_scan
from app.utils.logger import get_logger

logger = get_logger("scheduler")

scheduler = AsyncIOScheduler()


async def refresh_data_job():
    """Periodic job to refresh stock data."""
    try:
        watchlist = await _get_watchlist_symbols()
        stocks_data = await fetch_all_stocks(watchlist)
        logger.info(f"Refreshed data for {len(stocks_data)} stocks")
    except Exception as e:
        logger.error(f"Data refresh job failed: {e}")


async def check_signals_job():
    """Periodic job to check for new signals and send alerts."""
    try:
        watchlist = await _get_watchlist_symbols()
        stocks_data = await fetch_all_stocks(watchlist)
        reports = analyze_all(stocks_data)

        settings = get_settings()
        for report in reports:
            if report.get("signal") != "HOLD" and report.get("confidence", 0) >= settings.notifications.whatsapp.min_alert_confidence:
                dashboard_url = f"http://{settings.app.host}:{settings.app.port}"
                send_signal_alert(report, dashboard_url)

        logger.info(f"Signal check complete: {len(reports)} stocks analyzed")
    except Exception as e:
        logger.error(f"Signal check job failed: {e}")


async def daily_summary_job():
    """Send daily summary via WhatsApp."""
    try:
        watchlist = await _get_watchlist_symbols()
        stocks_data = await fetch_all_stocks(watchlist)
        reports = analyze_all(stocks_data)

        settings = get_settings()
        dashboard_url = f"http://{settings.app.host}:{settings.app.port}"
        send_daily_summary(reports, dashboard_url)

        logger.info("Daily summary sent")
    except Exception as e:
        logger.error(f"Daily summary job failed: {e}")


async def sp500_scan_job():
    """Daily S&P 500 scan job."""
    try:
        await run_full_scan()

        # Send WhatsApp scanner summary
        settings = get_settings()
        if settings.notifications.whatsapp.enabled and settings.notifications.whatsapp.scanner_summary:
            buy_results = await get_scan_results(signal_filter="BUY", min_confidence=65, limit=5)
            sell_results = await get_scan_results(signal_filter="SELL", min_confidence=65, limit=5)
            status = await get_scan_status()
            dashboard_url = f"http://{settings.app.host}:{settings.app.port}/scanner"
            send_scanner_summary(
                buy_results.get("results", []),
                sell_results.get("results", []),
                status,
                dashboard_url,
            )

        logger.info("S&P 500 scan job complete")
    except Exception as e:
        logger.error(f"S&P 500 scan job failed: {e}")


def start_scheduler():
    """Start the background scheduler with configured intervals."""
    settings = get_settings()

    scheduler.add_job(
        refresh_data_job,
        "interval",
        minutes=settings.scheduler.data_refresh_minutes,
        id="data_refresh",
        replace_existing=True,
    )

    scheduler.add_job(
        check_signals_job,
        "interval",
        minutes=settings.scheduler.signal_check_minutes,
        id="signal_check",
        replace_existing=True,
    )

    # Daily summary
    hour, minute = settings.scheduler.daily_summary_time.split(":")
    scheduler.add_job(
        daily_summary_job,
        "cron",
        hour=int(hour),
        minute=int(minute),
        id="daily_summary",
        replace_existing=True,
    )

    # Daily S&P 500 scan at 06:00
    scheduler.add_job(
        sp500_scan_job,
        "cron",
        hour=6,
        minute=0,
        id="sp500_scan",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        f"Scheduler started: data refresh every {settings.scheduler.data_refresh_minutes}m, "
        f"signal check every {settings.scheduler.signal_check_minutes}m, "
        f"daily summary at {settings.scheduler.daily_summary_time}, "
        f"S&P 500 scan daily at 06:00"
    )


def stop_scheduler():
    """Stop the background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
