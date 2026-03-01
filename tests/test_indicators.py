"""Tests for technical indicator calculations."""

import sys
import os
import pytest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.analysis.indicators import calculate_indicators


def _make_history(prices, volumes=None):
    """Create mock OHLCV history from a list of close prices."""
    history = []
    for i, price in enumerate(prices):
        history.append({
            "date": f"2025-01-{i+1:02d}",
            "open": price * 0.99,
            "high": price * 1.02,
            "low": price * 0.97,
            "close": price,
            "volume": (volumes[i] if volumes else 1000000),
        })
    return history


@pytest.fixture
def trending_up_history():
    """Generate an uptrending price series (250 bars)."""
    np.random.seed(42)
    base = 100
    prices = []
    for i in range(250):
        base += np.random.normal(0.15, 1.0)
        prices.append(round(max(base, 10), 2))
    return _make_history(prices)


@pytest.fixture
def trending_down_history():
    """Generate a downtrending price series (250 bars)."""
    np.random.seed(42)
    base = 200
    prices = []
    for i in range(250):
        base -= np.random.normal(0.15, 1.0)
        prices.append(round(max(base, 10), 2))
    return _make_history(prices)


class TestIndicators:
    def test_rsi_calculated(self, trending_up_history):
        result = calculate_indicators(trending_up_history)
        assert "rsi" in result
        assert result["rsi"] is not None
        assert 0 <= result["rsi"] <= 100

    def test_macd_calculated(self, trending_up_history):
        result = calculate_indicators(trending_up_history)
        assert result["macd_line"] is not None
        assert result["macd_signal"] is not None
        assert result["macd_histogram"] is not None

    def test_sma_values(self, trending_up_history):
        result = calculate_indicators(trending_up_history)
        assert result["sma_20"] is not None
        assert result["sma_50"] is not None
        assert result["sma_200"] is not None
        # In an uptrend, SMA20 > SMA50 > SMA200
        assert result["sma_20"] > result["sma_200"]

    def test_ema_values(self, trending_up_history):
        result = calculate_indicators(trending_up_history)
        assert result["ema_12"] is not None
        assert result["ema_26"] is not None

    def test_bollinger_bands(self, trending_up_history):
        result = calculate_indicators(trending_up_history)
        assert result["bb_upper"] is not None
        assert result["bb_middle"] is not None
        assert result["bb_lower"] is not None
        assert result["bb_upper"] > result["bb_middle"] > result["bb_lower"]

    def test_atr_calculated(self, trending_up_history):
        result = calculate_indicators(trending_up_history)
        assert result["atr"] is not None
        assert result["atr"] > 0

    def test_stochastic_oscillator(self, trending_up_history):
        result = calculate_indicators(trending_up_history)
        assert result["stoch_k"] is not None
        assert result["stoch_d"] is not None
        assert 0 <= result["stoch_k"] <= 100
        assert 0 <= result["stoch_d"] <= 100

    def test_volume_analysis(self, trending_up_history):
        result = calculate_indicators(trending_up_history)
        assert result["volume_avg"] is not None
        assert result["volume_ratio"] is not None

    def test_52_week_position(self, trending_up_history):
        result = calculate_indicators(trending_up_history)
        assert result["week_52_position"] is not None
        assert 0 <= result["week_52_position"] <= 100

    def test_crossover_detection(self, trending_up_history):
        result = calculate_indicators(trending_up_history)
        assert "golden_cross" in result
        assert "death_cross" in result
        assert isinstance(result["golden_cross"], bool)
        assert isinstance(result["death_cross"], bool)

    def test_insufficient_data(self):
        short = _make_history([100, 101, 102])
        result = calculate_indicators(short)
        assert result == {}

    def test_empty_data(self):
        result = calculate_indicators([])
        assert result == {}

    def test_downtrend_indicators(self, trending_down_history):
        result = calculate_indicators(trending_down_history)
        assert result["rsi"] is not None
        # In a downtrend, SMA20 < SMA200
        assert result["sma_20"] < result["sma_200"]
