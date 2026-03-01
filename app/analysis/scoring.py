"""Composite confidence scoring system for signals."""

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("scoring")


def calculate_confidence(signal_type: str, indicators: dict, buy_signals: list, sell_signals: list) -> int:
    """Calculate a confidence score (0-100) for a signal.

    Based on:
    - Number of agreeing indicators
    - Strength of each indicator
    - Trend alignment
    - Volume confirmation
    """
    if signal_type == "HOLD":
        # For HOLD signals, give a low score based on the strongest side
        max_signals = max(len(buy_signals), len(sell_signals))
        return min(max_signals * 15, 49)

    settings = get_settings()
    cfg = settings.analysis.indicators
    score = 0

    active_signals = buy_signals if signal_type == "BUY" else sell_signals

    # Base score: number of agreeing indicators (up to 42 points)
    signal_count = len(active_signals)
    score += min(signal_count * 14, 42)

    # Indicator strength bonus (up to 30 points)
    rsi = indicators.get("rsi")
    if rsi is not None:
        if signal_type == "BUY" and rsi < cfg.rsi.oversold:
            # The lower the RSI, the stronger the signal
            strength = (cfg.rsi.oversold - rsi) / cfg.rsi.oversold
            score += int(strength * 15)
        elif signal_type == "SELL" and rsi > cfg.rsi.overbought:
            strength = (rsi - cfg.rsi.overbought) / (100 - cfg.rsi.overbought)
            score += int(strength * 15)

    macd_hist = indicators.get("macd_histogram")
    if macd_hist is not None:
        if (signal_type == "BUY" and macd_hist > 0) or (signal_type == "SELL" and macd_hist < 0):
            score += 5

    week_52_pos = indicators.get("week_52_position")
    if week_52_pos is not None:
        if signal_type == "BUY" and week_52_pos < 30:
            score += 5
        elif signal_type == "SELL" and week_52_pos > 70:
            score += 5

    stoch_k = indicators.get("stoch_k")
    if stoch_k is not None:
        if signal_type == "BUY" and stoch_k < 20:
            score += 5
        elif signal_type == "SELL" and stoch_k > 80:
            score += 5

    # Trend alignment bonus (up to 15 points)
    price_above_sma_200 = indicators.get("price_above_sma_200")
    if price_above_sma_200 is not None:
        if signal_type == "BUY" and price_above_sma_200:
            score += 8  # Buying in an uptrend
        elif signal_type == "SELL" and not price_above_sma_200:
            score += 8  # Selling in a downtrend

    price_above_sma_50 = indicators.get("price_above_sma_50")
    if price_above_sma_50 is not None:
        if signal_type == "BUY" and not price_above_sma_50:
            score += 4  # Buying below SMA50 = potential bounce
        elif signal_type == "SELL" and price_above_sma_50:
            score += 4  # Selling above SMA50 = potential reversal

    golden_cross = indicators.get("golden_cross", False)
    death_cross = indicators.get("death_cross", False)
    if signal_type == "BUY" and golden_cross:
        score += 3
    elif signal_type == "SELL" and death_cross:
        score += 3

    # Volume confirmation bonus (up to 13 points)
    volume_ratio = indicators.get("volume_ratio")
    if volume_ratio is not None and volume_ratio > 1.0:
        vol_bonus = min(int((volume_ratio - 1.0) * 10), 13)
        score += vol_bonus

    # Clamp to 0-100
    score = max(0, min(100, score))

    logger.debug(f"Confidence score for {signal_type}: {score}/100 ({signal_count} signals)")
    return score


def get_confidence_label(confidence: int) -> dict:
    """Return the confidence level label and color."""
    if confidence >= 80:
        return {"level": "Strong", "color": "green", "emoji": "🟢"}
    elif confidence >= 65:
        return {"level": "Moderate", "color": "yellow", "emoji": "🟡"}
    elif confidence >= 50:
        return {"level": "Weak", "color": "orange", "emoji": "🟠"}
    else:
        return {"level": "None", "color": "grey", "emoji": "⚪"}
