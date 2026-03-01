"""Technical indicator calculations using ta library and pandas."""

import numpy as np
import pandas as pd
import ta

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger("indicators")


def calculate_indicators(history: list[dict]) -> dict:
    """Calculate all technical indicators from OHLCV history data.

    Returns a dict of indicator values for the most recent bar.
    """
    if not history or len(history) < 30:
        logger.warning("Insufficient data for indicator calculation")
        return {}

    settings = get_settings()
    cfg = settings.analysis.indicators

    df = pd.DataFrame(history)
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0).astype(int)
    df = df.dropna(subset=["close"])

    if len(df) < 30:
        return {}

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"].astype(float)

    result = {}

    # RSI
    try:
        rsi_indicator = ta.momentum.RSIIndicator(close=close, window=cfg.rsi.period)
        result["rsi"] = round(float(rsi_indicator.rsi().iloc[-1]), 2) if not rsi_indicator.rsi().iloc[-1] != rsi_indicator.rsi().iloc[-1] else None
        if result["rsi"] is not None and np.isnan(result["rsi"]):
            result["rsi"] = None
    except Exception as e:
        logger.debug(f"RSI calculation failed: {e}")
        result["rsi"] = None

    # MACD
    try:
        macd = ta.trend.MACD(close=close, window_slow=cfg.macd.slow, window_fast=cfg.macd.fast, window_sign=cfg.macd.signal)
        macd_line = macd.macd().iloc[-1]
        signal_line = macd.macd_signal().iloc[-1]
        histogram = macd.macd_diff().iloc[-1]
        result["macd_line"] = round(float(macd_line), 4) if not np.isnan(macd_line) else None
        result["macd_signal"] = round(float(signal_line), 4) if not np.isnan(signal_line) else None
        result["macd_histogram"] = round(float(histogram), 4) if not np.isnan(histogram) else None

        # Previous histogram for trend detection
        prev_hist = macd.macd_diff().iloc[-2] if len(macd.macd_diff()) > 1 else None
        result["macd_histogram_prev"] = round(float(prev_hist), 4) if prev_hist is not None and not np.isnan(prev_hist) else None
    except Exception as e:
        logger.debug(f"MACD calculation failed: {e}")
        result["macd_line"] = result["macd_signal"] = result["macd_histogram"] = result["macd_histogram_prev"] = None

    # SMA
    for label, period in [("sma_20", cfg.moving_averages.sma_short), ("sma_50", cfg.moving_averages.sma_long), ("sma_200", cfg.moving_averages.sma_trend)]:
        try:
            sma = ta.trend.SMAIndicator(close=close, window=period)
            val = sma.sma_indicator().iloc[-1]
            result[label] = round(float(val), 2) if not np.isnan(val) else None
        except Exception:
            result[label] = None

    # EMA
    for label, period in [("ema_12", cfg.moving_averages.ema_short), ("ema_26", cfg.moving_averages.ema_long)]:
        try:
            ema = ta.trend.EMAIndicator(close=close, window=period)
            val = ema.ema_indicator().iloc[-1]
            result[label] = round(float(val), 2) if not np.isnan(val) else None
        except Exception:
            result[label] = None

    # Bollinger Bands
    try:
        bb = ta.volatility.BollingerBands(close=close, window=cfg.bollinger_bands.period, window_dev=cfg.bollinger_bands.std_dev)
        result["bb_upper"] = round(float(bb.bollinger_hband().iloc[-1]), 2) if not np.isnan(bb.bollinger_hband().iloc[-1]) else None
        result["bb_middle"] = round(float(bb.bollinger_mavg().iloc[-1]), 2) if not np.isnan(bb.bollinger_mavg().iloc[-1]) else None
        result["bb_lower"] = round(float(bb.bollinger_lband().iloc[-1]), 2) if not np.isnan(bb.bollinger_lband().iloc[-1]) else None
    except Exception as e:
        logger.debug(f"Bollinger Bands calculation failed: {e}")
        result["bb_upper"] = result["bb_middle"] = result["bb_lower"] = None

    # ATR
    try:
        atr = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=cfg.atr.period)
        val = atr.average_true_range().iloc[-1]
        result["atr"] = round(float(val), 2) if not np.isnan(val) else None
    except Exception:
        result["atr"] = None

    # Stochastic Oscillator
    try:
        stoch = ta.momentum.StochasticOscillator(high=high, low=low, close=close, window=cfg.stochastic.k_period, smooth_window=cfg.stochastic.d_period)
        k = stoch.stoch().iloc[-1]
        d = stoch.stoch_signal().iloc[-1]
        result["stoch_k"] = round(float(k), 2) if not np.isnan(k) else None
        result["stoch_d"] = round(float(d), 2) if not np.isnan(d) else None

        # Previous values for crossover detection
        prev_k = stoch.stoch().iloc[-2] if len(stoch.stoch()) > 1 else None
        prev_d = stoch.stoch_signal().iloc[-2] if len(stoch.stoch_signal()) > 1 else None
        result["stoch_k_prev"] = round(float(prev_k), 2) if prev_k is not None and not np.isnan(prev_k) else None
        result["stoch_d_prev"] = round(float(prev_d), 2) if prev_d is not None and not np.isnan(prev_d) else None
    except Exception:
        result["stoch_k"] = result["stoch_d"] = result["stoch_k_prev"] = result["stoch_d_prev"] = None

    # Volume Analysis
    try:
        vol_avg = volume.rolling(window=cfg.volume.avg_period).mean().iloc[-1]
        current_vol = float(volume.iloc[-1])
        result["volume_avg"] = round(float(vol_avg), 0) if not np.isnan(vol_avg) else None
        result["volume_ratio"] = round(current_vol / vol_avg, 2) if vol_avg and not np.isnan(vol_avg) and vol_avg > 0 else None
        result["volume_spike"] = result["volume_ratio"] is not None and result["volume_ratio"] >= cfg.volume.spike_multiplier
    except Exception:
        result["volume_avg"] = result["volume_ratio"] = None
        result["volume_spike"] = False

    # 52-Week Position
    try:
        high_52 = float(high.tail(252).max())
        low_52 = float(low.tail(252).min())
        current = float(close.iloc[-1])
        if high_52 > low_52:
            result["week_52_position"] = round(((current - low_52) / (high_52 - low_52)) * 100, 1)
        else:
            result["week_52_position"] = 50.0
        result["week_52_high"] = round(high_52, 2)
        result["week_52_low"] = round(low_52, 2)
    except Exception:
        result["week_52_position"] = None

    # Golden Cross / Death Cross detection
    try:
        if result.get("sma_50") and result.get("sma_200"):
            sma50_series = ta.trend.SMAIndicator(close=close, window=cfg.moving_averages.sma_long).sma_indicator()
            sma200_series = ta.trend.SMAIndicator(close=close, window=cfg.moving_averages.sma_trend).sma_indicator()

            if len(sma50_series) >= 2 and len(sma200_series) >= 2:
                curr_50, prev_50 = float(sma50_series.iloc[-1]), float(sma50_series.iloc[-2])
                curr_200, prev_200 = float(sma200_series.iloc[-1]), float(sma200_series.iloc[-2])

                result["golden_cross"] = prev_50 <= prev_200 and curr_50 > curr_200
                result["death_cross"] = prev_50 >= prev_200 and curr_50 < curr_200
            else:
                result["golden_cross"] = False
                result["death_cross"] = False
        else:
            result["golden_cross"] = False
            result["death_cross"] = False
    except Exception:
        result["golden_cross"] = False
        result["death_cross"] = False

    # Price vs SMA
    try:
        current_price = float(close.iloc[-1])
        result["price_above_sma_50"] = current_price > result["sma_50"] if result.get("sma_50") else None
        result["price_above_sma_200"] = current_price > result["sma_200"] if result.get("sma_200") else None
    except Exception:
        result["price_above_sma_50"] = None
        result["price_above_sma_200"] = None

    # Current price and previous close for signal generation
    result["current_price"] = round(float(close.iloc[-1]), 2)
    result["prev_close"] = round(float(close.iloc[-2]), 2) if len(close) > 1 else result["current_price"]

    # Convert all numpy types to native Python types for JSON serialization
    result = _sanitize(result)

    logger.debug(f"Calculated indicators: RSI={result.get('rsi')}, MACD={result.get('macd_histogram')}")
    return result


def _sanitize(data: dict) -> dict:
    """Convert numpy types to native Python types."""
    cleaned = {}
    for key, value in data.items():
        if isinstance(value, (np.bool_,)):
            cleaned[key] = bool(value)
        elif isinstance(value, (np.integer,)):
            cleaned[key] = int(value)
        elif isinstance(value, (np.floating,)):
            cleaned[key] = None if np.isnan(value) else float(value)
        elif isinstance(value, dict):
            cleaned[key] = _sanitize(value)
        else:
            cleaned[key] = value
    return cleaned
