"""Tests for confidence scoring."""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.analysis.scoring import calculate_confidence, get_confidence_label


class TestConfidenceScoring:
    def test_hold_gets_low_score(self):
        score = calculate_confidence("HOLD", {}, [], [])
        assert score < 50

    def test_more_signals_higher_score(self):
        indicators = {"rsi": 20, "volume_ratio": 1.5}
        score_few = calculate_confidence("BUY", indicators, ["sig1"], [])
        score_many = calculate_confidence("BUY", indicators, ["sig1", "sig2", "sig3", "sig4"], [])
        assert score_many > score_few

    def test_strong_rsi_gives_bonus(self):
        indicators_weak = {"rsi": 28}
        indicators_strong = {"rsi": 10}
        buy_signals = ["RSI oversold", "MACD bullish", "Golden Cross"]

        score_weak = calculate_confidence("BUY", indicators_weak, buy_signals, [])
        score_strong = calculate_confidence("BUY", indicators_strong, buy_signals, [])
        assert score_strong > score_weak

    def test_volume_confirmation_bonus(self):
        indicators_no_vol = {"rsi": 25}
        indicators_vol = {"rsi": 25, "volume_ratio": 2.5}
        buy_signals = ["RSI oversold", "MACD bullish", "Golden Cross"]

        score_no = calculate_confidence("BUY", indicators_no_vol, buy_signals, [])
        score_vol = calculate_confidence("BUY", indicators_vol, buy_signals, [])
        assert score_vol > score_no

    def test_score_clamped_to_100(self):
        indicators = {"rsi": 5, "volume_ratio": 5.0, "price_above_sma_200": True, "price_above_sma_50": False, "golden_cross": True}
        many_signals = [f"sig{i}" for i in range(10)]
        score = calculate_confidence("BUY", indicators, many_signals, [])
        assert score <= 100


class TestConfidenceLabel:
    def test_strong_label(self):
        result = get_confidence_label(85)
        assert result["level"] == "Strong"
        assert result["color"] == "green"

    def test_moderate_label(self):
        result = get_confidence_label(70)
        assert result["level"] == "Moderate"

    def test_weak_label(self):
        result = get_confidence_label(55)
        assert result["level"] == "Weak"

    def test_none_label(self):
        result = get_confidence_label(30)
        assert result["level"] == "None"
