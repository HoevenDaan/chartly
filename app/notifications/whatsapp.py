"""WhatsApp notifications via CallMeBot API."""

import time
import urllib.parse
from typing import Optional

import requests

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("whatsapp")

_last_send_time = 0.0


def _rate_limit():
    """Ensure at least 3 seconds between messages."""
    global _last_send_time
    elapsed = time.time() - _last_send_time
    if elapsed < 3:
        time.sleep(3 - elapsed)
    _last_send_time = time.time()


def send_whatsapp(message: str) -> bool:
    """Send a WhatsApp message via CallMeBot API.

    Returns True if sent successfully, False otherwise.
    """
    settings = get_settings()
    if not settings.notifications.whatsapp.enabled:
        return False

    phone = settings.whatsapp_phone
    api_key = settings.callmebot_api_key

    if not phone or not api_key:
        logger.warning("WhatsApp not configured: missing phone or API key in .env")
        return False

    try:
        _rate_limit()
        encoded_msg = urllib.parse.quote_plus(message)
        url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_msg}&apikey={api_key}"

        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            logger.info("WhatsApp message sent successfully")
            return True
        else:
            logger.warning(f"WhatsApp API returned status {resp.status_code}: {resp.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"WhatsApp send failed: {e}")
        return False


def send_signal_alert(report: dict, dashboard_url: str = "http://127.0.0.1:8000"):
    """Send a signal alert for a stock that hits the confidence threshold."""
    settings = get_settings()
    if not settings.notifications.whatsapp.enabled or not settings.notifications.whatsapp.signal_alerts:
        return

    min_conf = settings.notifications.whatsapp.min_alert_confidence
    confidence = report.get("confidence", 0)
    if confidence < min_conf:
        return

    symbol = report.get("symbol", "?")
    signal = report.get("signal", "HOLD")
    if signal == "HOLD":
        return

    msg = (
        f"📊 *StockPulse Alert*\n\n"
        f"{report.get('summary', f'{symbol}: {signal}')}\n\n"
        f"Dashboard: {dashboard_url}\n\n"
        f"⚠️ This is algorithmic analysis only. Not financial advice."
    )

    send_whatsapp(msg)


def send_daily_summary(reports: list[dict], dashboard_url: str = "http://127.0.0.1:8000"):
    """Send a daily summary of all watched stocks."""
    settings = get_settings()
    if not settings.notifications.whatsapp.enabled or not settings.notifications.whatsapp.daily_summary:
        return

    lines = ["📊 *StockPulse Daily Summary*\n"]
    for r in reports:
        symbol = r.get("symbol", "?")
        price = r.get("price", 0)
        change_pct = r.get("change_percent", 0)
        signal = r.get("signal", "HOLD")
        confidence = r.get("confidence", 0)
        arrow = "▲" if change_pct >= 0 else "▼"
        lines.append(f"{symbol}: ${price:.2f} {arrow}{abs(change_pct):.1f}% | {signal} ({confidence}/100)")

    lines.append(f"\nDashboard: {dashboard_url}")
    lines.append("\n⚠️ Not financial advice. Educational purposes only.")

    send_whatsapp("\n".join(lines))


def send_scanner_summary(
    buy_results: list[dict],
    sell_results: list[dict],
    scan_meta: dict,
    dashboard_url: str = "http://127.0.0.1:8000/scanner",
):
    """Send a summary of the S&P 500 scanner results via WhatsApp."""
    settings = get_settings()
    if not settings.notifications.whatsapp.enabled:
        return
    if not settings.notifications.whatsapp.scanner_summary:
        return

    total = scan_meta.get("total", 0)
    buy_count = scan_meta.get("buy_count", 0)
    sell_count = scan_meta.get("sell_count", 0)

    lines = [f"📡 *S&P 500 Scan Complete*\n"]

    if buy_results:
        lines.append("🟢 Top BUY signals today:")
        for r in buy_results[:5]:
            reasons_str = ", ".join(r.get("reasons", [])[:2])
            lines.append(f"• {r['symbol']} — {r['confidence']}/100 ({reasons_str})")

    if sell_results:
        lines.append("\n🔴 Top SELL signals today:")
        for r in sell_results[:5]:
            reasons_str = ", ".join(r.get("reasons", [])[:2])
            lines.append(f"• {r['symbol']} — {r['confidence']}/100 ({reasons_str})")

    lines.append(f"\n{total} stocks scanned · {buy_count} BUY · {sell_count} SELL")
    lines.append(f"Dashboard: {dashboard_url}")
    lines.append("\n⚠️ Not financial advice.")

    send_whatsapp("\n".join(lines))
