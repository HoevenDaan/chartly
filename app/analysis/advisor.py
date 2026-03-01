"""Main advisor engine combining all analysis into recommendations."""

from datetime import datetime

from app.analysis.indicators import calculate_indicators
from app.analysis.scoring import calculate_confidence, get_confidence_label
from app.analysis.signals import generate_signals
from app.utils.logger import get_logger

logger = get_logger("advisor")

DISCLAIMER = (
    "DISCLAIMER: StockPulse is a technical analysis tool for educational and informational "
    "purposes only. It does NOT constitute financial advice, investment recommendations, or "
    "solicitations to buy or sell securities. Technical indicators are based on historical "
    "data and mathematical formulas — they cannot predict future market movements. Past "
    "performance does not guarantee future results. Always conduct your own research and "
    "consult with a qualified financial advisor before making any investment decisions. "
    "The creators of StockPulse assume no liability for any financial losses incurred "
    "through the use of this application."
)


def analyze_stock(stock_data: dict) -> dict:
    """Run full analysis on a stock and return a complete report.

    Args:
        stock_data: Dict with 'info', 'price', and 'history' keys.

    Returns:
        Dict with full analysis including indicators, signal, confidence, and advisor text.
    """
    info = stock_data.get("info", {})
    price_data = stock_data.get("price", {})
    history = stock_data.get("history", [])
    symbol = info.get("symbol", "???")
    name = info.get("name", symbol)
    price = price_data.get("price", 0)

    # Calculate indicators
    indicators = calculate_indicators(history)

    # Generate signals
    signal_result = generate_signals(indicators)

    # Calculate confidence
    confidence = calculate_confidence(
        signal_result["signal"],
        indicators,
        signal_result["buy_signals"],
        signal_result["sell_signals"],
    )
    signal_result["confidence"] = confidence

    confidence_info = get_confidence_label(confidence)

    # Key levels
    key_levels = _calculate_key_levels(indicators, price)

    # Build summary text
    summary = _build_summary(
        symbol, name, price, signal_result, indicators, key_levels, confidence_info
    )

    report = {
        "symbol": symbol,
        "name": name,
        "price": price,
        "change": price_data.get("change", 0),
        "change_percent": price_data.get("change_percent", 0),
        "volume": price_data.get("volume", 0),
        "market_open": price_data.get("market_open", True),
        "signal": signal_result["signal"],
        "confidence": confidence,
        "confidence_label": confidence_info,
        "buy_signals": signal_result["buy_signals"],
        "sell_signals": signal_result["sell_signals"],
        "reasons": signal_result["reasons"],
        "indicators": indicators,
        "key_levels": key_levels,
        "summary": summary,
        "info": info,
        "disclaimer": DISCLAIMER,
        "timestamp": datetime.now().isoformat(),
        "_stale": stock_data.get("_stale", False),
        "_error": stock_data.get("_error"),
    }

    logger.info(f"{symbol}: {signal_result['signal']} ({confidence}/100 {confidence_info['emoji']})")
    return report


def _calculate_key_levels(indicators: dict, current_price: float) -> dict:
    """Calculate support, resistance, and stop loss levels."""
    levels = {
        "support": None,
        "support_label": "",
        "resistance": None,
        "resistance_label": "",
        "stop_loss": None,
    }

    sma_200 = indicators.get("sma_200")
    sma_50 = indicators.get("sma_50")
    sma_20 = indicators.get("sma_20")
    bb_lower = indicators.get("bb_lower")
    bb_upper = indicators.get("bb_upper")
    atr = indicators.get("atr")

    # Support: nearest SMA below price, or BB lower
    support_candidates = []
    if sma_200 and sma_200 < current_price:
        support_candidates.append((sma_200, "SMA 200"))
    if sma_50 and sma_50 < current_price:
        support_candidates.append((sma_50, "SMA 50"))
    if sma_20 and sma_20 < current_price:
        support_candidates.append((sma_20, "SMA 20"))
    if bb_lower and bb_lower < current_price:
        support_candidates.append((bb_lower, "Lower Bollinger Band"))

    if support_candidates:
        # Nearest support (highest value below price)
        best = max(support_candidates, key=lambda x: x[0])
        levels["support"] = round(best[0], 2)
        levels["support_label"] = best[1]

    # Resistance: nearest SMA above price, or BB upper
    resist_candidates = []
    if sma_200 and sma_200 > current_price:
        resist_candidates.append((sma_200, "SMA 200"))
    if sma_50 and sma_50 > current_price:
        resist_candidates.append((sma_50, "SMA 50"))
    if sma_20 and sma_20 > current_price:
        resist_candidates.append((sma_20, "SMA 20"))
    if bb_upper and bb_upper > current_price:
        resist_candidates.append((bb_upper, "Upper Bollinger Band"))

    if resist_candidates:
        best = min(resist_candidates, key=lambda x: x[0])
        levels["resistance"] = round(best[0], 2)
        levels["resistance_label"] = best[1]

    # Stop loss: below ATR range
    if atr and current_price:
        levels["stop_loss"] = round(current_price - (atr * 2), 2)

    return levels


def _build_summary(symbol, name, price, signal_result, indicators, key_levels, confidence_info):
    """Build a human-readable advisor summary."""
    sig = signal_result["signal"]
    conf = signal_result["confidence"]
    emoji = confidence_info["emoji"]

    lines = [f"{symbol} — {name} — ${price:.2f}"]
    lines.append(f"Signal: {sig} | Confidence: {conf}/100 {emoji}")
    lines.append("")

    # Why
    reasons = signal_result.get("reasons", [])
    if reasons:
        lines.append("Why: " + ". ".join(reasons[:4]) + ".")

    # Additional context
    context_parts = []
    vol_ratio = indicators.get("volume_ratio")
    if vol_ratio:
        context_parts.append(f"Volume is {vol_ratio:.1f}x the 20-day average")

    w52 = indicators.get("week_52_position")
    if w52 is not None:
        w52_high = indicators.get("week_52_high")
        if w52_high and price:
            pct_below = round(((w52_high - price) / w52_high) * 100, 1)
            if pct_below > 0:
                context_parts.append(f"Price is {pct_below}% below 52-week high")

    if context_parts:
        lines.append(" ".join(context_parts) + ".")

    # Key levels
    lines.append("")
    lines.append("Key Levels:")
    if key_levels.get("support"):
        lines.append(f"  Support: ${key_levels['support']:.2f} ({key_levels['support_label']})")
    if key_levels.get("resistance"):
        lines.append(f"  Resistance: ${key_levels['resistance']:.2f} ({key_levels['resistance_label']})")
    if key_levels.get("stop_loss"):
        lines.append(f"  Stop Loss suggestion: ${key_levels['stop_loss']:.2f} (below ATR range)")

    return "\n".join(lines)


def analyze_all(stocks_data: list[dict]) -> list[dict]:
    """Analyze all stocks and return list of reports."""
    reports = []
    for stock in stocks_data:
        try:
            report = analyze_stock(stock)
            reports.append(report)
        except Exception as e:
            logger.error(f"Analysis failed for {stock.get('info', {}).get('symbol', '?')}: {e}")
            reports.append({
                "symbol": stock.get("info", {}).get("symbol", "?"),
                "name": stock.get("info", {}).get("name", "?"),
                "price": stock.get("price", {}).get("price", 0),
                "signal": "HOLD",
                "confidence": 0,
                "confidence_label": get_confidence_label(0),
                "reasons": [f"Analysis error: {str(e)}"],
                "indicators": {},
                "key_levels": {},
                "summary": "Analysis unavailable",
                "disclaimer": DISCLAIMER,
                "timestamp": datetime.now().isoformat(),
                "_error": str(e),
                "buy_signals": [],
                "sell_signals": [],
            })
    return reports
