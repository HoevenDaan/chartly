"""Tests for the advisor engine."""

import sys
import os
import pytest
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.analysis.advisor import analyze_stock, analyze_all, DISCLAIMER


def _make_history(prices):
    """Create mock OHLCV history from a list of close prices."""
    return [{
        "date": f"2025-01-{i+1:02d}",
        "open": price * 0.99,
        "high": price * 1.02,
        "low": price * 0.97,
        "close": price,
        "volume": 1000000,
    } for i, price in enumerate(prices)]


def _make_stock_data(symbol="TEST", name="Test Corp", prices=None):
    """Create a complete mock stock data dict."""
    if prices is None:
        np.random.seed(42)
        base = 100
        prices = []
        for _ in range(250):
            base += np.random.normal(0.05, 0.8)
            prices.append(round(max(base, 10), 2))

    return {
        "info": {
            "symbol": symbol,
            "name": name,
            "sector": "Technology",
            "market_cap": 1e12,
            "pe_ratio": 25.5,
            "week_52_high": max(prices),
            "week_52_low": min(prices),
        },
        "price": {
            "symbol": symbol,
            "price": prices[-1],
            "change": prices[-1] - prices[-2] if len(prices) > 1 else 0,
            "change_percent": ((prices[-1] - prices[-2]) / prices[-2] * 100) if len(prices) > 1 else 0,
            "volume": 1000000,
            "market_open": True,
        },
        "history": _make_history(prices),
    }


class TestAdvisor:
    def test_analyze_stock_returns_complete_report(self):
        data = _make_stock_data()
        report = analyze_stock(data)

        assert report["symbol"] == "TEST"
        assert report["name"] == "Test Corp"
        assert report["price"] > 0
        assert report["signal"] in ("BUY", "SELL", "HOLD")
        assert 0 <= report["confidence"] <= 100
        assert "indicators" in report
        assert "key_levels" in report
        assert "summary" in report
        assert "disclaimer" in report

    def test_report_includes_disclaimer(self):
        data = _make_stock_data()
        report = analyze_stock(data)
        assert report["disclaimer"] == DISCLAIMER

    def test_report_has_confidence_label(self):
        data = _make_stock_data()
        report = analyze_stock(data)
        assert "confidence_label" in report
        assert "level" in report["confidence_label"]
        assert "color" in report["confidence_label"]

    def test_report_has_key_levels(self):
        data = _make_stock_data()
        report = analyze_stock(data)
        kl = report["key_levels"]
        assert "support" in kl
        assert "resistance" in kl
        assert "stop_loss" in kl

    def test_report_summary_contains_symbol(self):
        data = _make_stock_data(symbol="AAPL", name="Apple Inc.")
        report = analyze_stock(data)
        assert "AAPL" in report["summary"]

    def test_analyze_all_handles_errors(self):
        good = _make_stock_data(symbol="GOOD")
        bad = {"info": {"symbol": "BAD", "name": "Bad Corp"}, "price": {"symbol": "BAD", "price": 0, "volume": 0}, "history": []}

        reports = analyze_all([good, bad])
        assert len(reports) == 2
        symbols = [r["symbol"] for r in reports]
        assert "GOOD" in symbols
        assert "BAD" in symbols

    def test_analyze_all_returns_list(self):
        stocks = [_make_stock_data(symbol=s) for s in ["A", "B", "C"]]
        reports = analyze_all(stocks)
        assert len(reports) == 3
        assert all(isinstance(r, dict) for r in reports)
