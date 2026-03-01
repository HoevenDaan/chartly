"""Tests for signal generation logic."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.analysis.signals import generate_signals


class TestBuySignals:
    def test_rsi_oversold_triggers_buy(self):
        indicators = {"rsi": 25, "current_price": 100, "prev_close": 99}
        result = generate_signals(indicators)
        assert any("RSI" in s and "oversold" in s for s in result["buy_signals"])

    def test_macd_bullish_crossover(self):
        indicators = {"macd_histogram": 0.5, "macd_histogram_prev": -0.2, "current_price": 100, "prev_close": 99}
        result = generate_signals(indicators)
        assert any("MACD" in s and "bullish" in s for s in result["buy_signals"])

    def test_golden_cross(self):
        indicators = {"golden_cross": True, "current_price": 100, "prev_close": 99}
        result = generate_signals(indicators)
        assert any("Golden Cross" in s for s in result["buy_signals"])

    def test_volume_spike_up_day(self):
        indicators = {
            "volume_spike": True, "volume_ratio": 2.5,
            "current_price": 105, "prev_close": 100,
        }
        result = generate_signals(indicators)
        assert any("Volume spike" in s and "up day" in s for s in result["buy_signals"])

    def test_multiple_buy_signals_generate_buy(self):
        indicators = {
            "rsi": 22,
            "macd_histogram": 0.5, "macd_histogram_prev": -0.1,
            "golden_cross": True,
            "volume_spike": True, "volume_ratio": 2.0,
            "current_price": 100, "prev_close": 98,
        }
        result = generate_signals(indicators)
        assert result["signal"] == "BUY"
        assert len(result["buy_signals"]) >= 3


class TestSellSignals:
    def test_rsi_overbought_triggers_sell(self):
        indicators = {"rsi": 78, "current_price": 100, "prev_close": 101}
        result = generate_signals(indicators)
        assert any("RSI" in s and "overbought" in s for s in result["sell_signals"])

    def test_macd_bearish_crossover(self):
        indicators = {"macd_histogram": -0.5, "macd_histogram_prev": 0.2, "current_price": 100, "prev_close": 101}
        result = generate_signals(indicators)
        assert any("MACD" in s and "bearish" in s for s in result["sell_signals"])

    def test_death_cross(self):
        indicators = {"death_cross": True, "current_price": 100, "prev_close": 101}
        result = generate_signals(indicators)
        assert any("Death Cross" in s for s in result["sell_signals"])

    def test_multiple_sell_signals_generate_sell(self):
        indicators = {
            "rsi": 82,
            "macd_histogram": -0.5, "macd_histogram_prev": 0.1,
            "death_cross": True,
            "volume_spike": True, "volume_ratio": 3.0,
            "current_price": 95, "prev_close": 100,
        }
        result = generate_signals(indicators)
        assert result["signal"] == "SELL"
        assert len(result["sell_signals"]) >= 3


class TestHoldSignals:
    def test_no_indicators_generates_hold(self):
        result = generate_signals({})
        assert result["signal"] == "HOLD"

    def test_insufficient_signals_generates_hold(self):
        indicators = {"rsi": 50, "current_price": 100, "prev_close": 100}
        result = generate_signals(indicators)
        assert result["signal"] == "HOLD"

    def test_mixed_signals_generates_hold(self):
        indicators = {
            "rsi": 25,  # Buy signal
            "macd_histogram": -0.5, "macd_histogram_prev": 0.1,  # Sell signal
            "current_price": 100, "prev_close": 100,
        }
        result = generate_signals(indicators)
        # With only 1 buy and 1 sell, should be HOLD
        assert result["signal"] == "HOLD"

    def test_none_input_generates_hold(self):
        result = generate_signals(None)
        assert result["signal"] == "HOLD"
