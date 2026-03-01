"""Tests for data fetcher with mocked API calls."""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.data.fetcher import _fetch_yfinance, _fetch_alphavantage
from app.utils.exceptions import DataFetchError


class TestYfinanceFetcher:
    @patch("app.data.fetcher.yf.Ticker")
    def test_successful_fetch(self, mock_ticker_class):
        import pandas as pd
        import numpy as np

        dates = pd.date_range("2024-01-01", periods=50, freq="B")
        data = {
            "Open": np.random.uniform(90, 110, 50),
            "High": np.random.uniform(100, 120, 50),
            "Low": np.random.uniform(80, 100, 50),
            "Close": np.random.uniform(90, 115, 50),
            "Volume": np.random.randint(500000, 2000000, 50),
        }
        hist_df = pd.DataFrame(data, index=dates)

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = hist_df
        mock_ticker.info = {"longName": "Test Corp", "sector": "Tech", "marketCap": 1e12}
        mock_ticker_class.return_value = mock_ticker

        result = _fetch_yfinance("TEST")
        assert result["info"]["symbol"] == "TEST"
        assert result["info"]["name"] == "Test Corp"
        assert len(result["history"]) == 50
        assert result["price"]["price"] > 0

    @patch("app.data.fetcher.yf.Ticker")
    def test_empty_data_raises_error(self, mock_ticker_class):
        import pandas as pd

        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_ticker_class.return_value = mock_ticker

        with pytest.raises(DataFetchError):
            _fetch_yfinance("INVALID")


class TestAlphaVantageFetcher:
    @patch("app.data.fetcher.get_settings")
    def test_no_api_key_raises_error(self, mock_settings):
        settings = MagicMock()
        settings.alpha_vantage_api_key = None
        mock_settings.return_value = settings

        with pytest.raises(DataFetchError, match="API key not configured"):
            _fetch_alphavantage("TEST")

    @patch("app.data.fetcher.requests.get")
    @patch("app.data.fetcher.get_settings")
    def test_successful_alphavantage_fetch(self, mock_settings, mock_get):
        settings = MagicMock()
        settings.alpha_vantage_api_key = "test_key"
        mock_settings.return_value = settings

        # Mock daily data response
        daily_data = {"Time Series (Daily)": {}}
        for i in range(260):
            day = f"2024-{(i//30)+1:02d}-{(i%28)+1:02d}"
            daily_data["Time Series (Daily)"][day] = {
                "1. open": "100.00", "2. high": "105.00",
                "3. low": "95.00", "4. close": "102.00", "5. volume": "1000000"
            }

        # Mock overview response
        overview_data = {"Name": "Test", "Sector": "Tech", "MarketCapitalization": "1000000000", "TrailingPE": "25", "52WeekHigh": "120", "52WeekLow": "80"}

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = [daily_data, overview_data]
        mock_get.return_value = mock_resp

        result = _fetch_alphavantage("TEST")
        assert result["info"]["symbol"] == "TEST"
        assert len(result["history"]) > 0

    @patch("app.data.fetcher.requests.get")
    @patch("app.data.fetcher.get_settings")
    def test_alphavantage_api_error(self, mock_settings, mock_get):
        settings = MagicMock()
        settings.alpha_vantage_api_key = "test_key"
        mock_settings.return_value = settings

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"Error Message": "Invalid API call"}
        mock_get.return_value = mock_resp

        with pytest.raises(DataFetchError):
            _fetch_alphavantage("INVALID")
