"""Buy/sell/hold signal generation based on indicator confluence."""

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("signals")


def generate_signals(indicators: dict) -> dict:
    """Generate BUY/SELL/HOLD signals based on indicator values.

    Returns a dict with signal, buy_signals list, sell_signals list, and reasons.
    """
    if not indicators:
        return {"signal": "HOLD", "confidence": 0, "reasons": ["Insufficient data"], "buy_signals": [], "sell_signals": []}

    settings = get_settings()
    cfg = settings.analysis.indicators
    buy_signals = []
    sell_signals = []

    rsi = indicators.get("rsi")
    macd_hist = indicators.get("macd_histogram")
    macd_hist_prev = indicators.get("macd_histogram_prev")
    bb_lower = indicators.get("bb_lower")
    bb_upper = indicators.get("bb_upper")
    current_price = indicators.get("current_price")
    prev_close = indicators.get("prev_close")
    sma_50 = indicators.get("sma_50")
    price_above_sma_50 = indicators.get("price_above_sma_50")
    golden_cross = indicators.get("golden_cross", False)
    death_cross = indicators.get("death_cross", False)
    stoch_k = indicators.get("stoch_k")
    stoch_d = indicators.get("stoch_d")
    stoch_k_prev = indicators.get("stoch_k_prev")
    stoch_d_prev = indicators.get("stoch_d_prev")
    volume_spike = indicators.get("volume_spike", False)
    volume_ratio = indicators.get("volume_ratio")

    price_up = current_price and prev_close and current_price > prev_close

    # --- BUY SIGNALS ---

    # RSI oversold
    if rsi is not None and rsi < cfg.rsi.oversold:
        buy_signals.append(f"RSI is oversold ({rsi})")

    # MACD bullish crossover (histogram turning positive)
    if macd_hist is not None and macd_hist_prev is not None:
        if macd_hist > 0 and macd_hist_prev <= 0:
            buy_signals.append("MACD showing bullish crossover")
        elif macd_hist > macd_hist_prev and macd_hist > 0:
            buy_signals.append("MACD histogram strengthening")

    # Price bouncing off lower Bollinger Band
    if bb_lower is not None and current_price is not None and prev_close is not None:
        if prev_close <= bb_lower * 1.01 and current_price > prev_close:
            buy_signals.append("Price bouncing off lower Bollinger Band")

    # Price crossing above SMA 50
    if sma_50 is not None and current_price is not None and prev_close is not None:
        if prev_close < sma_50 and current_price >= sma_50:
            buy_signals.append("Price crossing above SMA 50")

    # Golden Cross
    if golden_cross:
        buy_signals.append("Golden Cross (SMA 50 crossed above SMA 200)")

    # Stochastic bullish crossover in oversold zone
    if all(v is not None for v in [stoch_k, stoch_d, stoch_k_prev, stoch_d_prev]):
        if stoch_k_prev < stoch_d_prev and stoch_k > stoch_d and stoch_k < 30:
            buy_signals.append(f"Stochastic bullish crossover in oversold zone (K={stoch_k})")

    # Volume spike on up day
    if volume_spike and price_up:
        ratio_str = f"{volume_ratio:.1f}x" if volume_ratio else ""
        buy_signals.append(f"Volume spike on up day ({ratio_str} avg)")

    # --- SELL SIGNALS ---

    # RSI overbought
    if rsi is not None and rsi > cfg.rsi.overbought:
        sell_signals.append(f"RSI is overbought ({rsi})")

    # MACD bearish crossover (histogram turning negative)
    if macd_hist is not None and macd_hist_prev is not None:
        if macd_hist < 0 and macd_hist_prev >= 0:
            sell_signals.append("MACD showing bearish crossover")
        elif macd_hist < macd_hist_prev and macd_hist < 0:
            sell_signals.append("MACD histogram weakening")

    # Price hitting upper Bollinger Band with reversal
    if bb_upper is not None and current_price is not None and prev_close is not None:
        if prev_close >= bb_upper * 0.99 and current_price < prev_close:
            sell_signals.append("Price reversing from upper Bollinger Band")

    # Price crossing below SMA 50
    if sma_50 is not None and current_price is not None and prev_close is not None:
        if prev_close > sma_50 and current_price <= sma_50:
            sell_signals.append("Price crossing below SMA 50")

    # Death Cross
    if death_cross:
        sell_signals.append("Death Cross (SMA 50 crossed below SMA 200)")

    # Stochastic bearish crossover in overbought zone
    if all(v is not None for v in [stoch_k, stoch_d, stoch_k_prev, stoch_d_prev]):
        if stoch_k_prev > stoch_d_prev and stoch_k < stoch_d and stoch_k > 70:
            sell_signals.append(f"Stochastic bearish crossover in overbought zone (K={stoch_k})")

    # Volume spike on down day
    if volume_spike and not price_up and current_price != prev_close:
        ratio_str = f"{volume_ratio:.1f}x" if volume_ratio else ""
        sell_signals.append(f"Volume spike on down day ({ratio_str} avg)")

    # --- DETERMINE SIGNAL ---
    min_agreement = settings.analysis.signals.min_agreement

    if len(buy_signals) >= min_agreement and len(buy_signals) > len(sell_signals):
        signal = "BUY"
        reasons = buy_signals
    elif len(sell_signals) >= min_agreement and len(sell_signals) > len(buy_signals):
        signal = "SELL"
        reasons = sell_signals
    else:
        signal = "HOLD"
        reasons = []
        if buy_signals:
            reasons.append(f"Some bullish signals ({len(buy_signals)}) but not enough confluence")
        if sell_signals:
            reasons.append(f"Some bearish signals ({len(sell_signals)}) but not enough confluence")
        if not buy_signals and not sell_signals:
            reasons.append("No strong directional signals detected")

    result = {
        "signal": signal,
        "buy_signals": buy_signals,
        "sell_signals": sell_signals,
        "reasons": reasons,
    }

    logger.info(f"Signal: {signal} | Buy signals: {len(buy_signals)} | Sell signals: {len(sell_signals)}")
    return result
