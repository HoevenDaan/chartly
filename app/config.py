"""Pydantic settings and configuration loader for StockPulse."""

import os
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class AppConfig(BaseModel):
    name: str = "StockPulse"
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    log_level: str = "INFO"


class WatchlistStock(BaseModel):
    symbol: str
    name: str


class WatchlistConfig(BaseModel):
    default_stocks: list[WatchlistStock] = []


class DataConfig(BaseModel):
    primary_source: str = "yfinance"
    fallback_source: str = "alphavantage"
    history_period: str = "1y"
    intraday_interval: str = "1h"
    cache_ttl_minutes: int = 15
    market_hours_only: bool = False


class RSIConfig(BaseModel):
    period: int = 14
    oversold: int = 30
    overbought: int = 70


class MACDConfig(BaseModel):
    fast: int = 12
    slow: int = 26
    signal: int = 9


class MovingAveragesConfig(BaseModel):
    sma_short: int = 20
    sma_long: int = 50
    sma_trend: int = 200
    ema_short: int = 12
    ema_long: int = 26


class BollingerBandsConfig(BaseModel):
    period: int = 20
    std_dev: int = 2


class ATRConfig(BaseModel):
    period: int = 14


class StochasticConfig(BaseModel):
    k_period: int = 14
    d_period: int = 3


class VolumeConfig(BaseModel):
    avg_period: int = 20
    spike_multiplier: float = 2.0


class IndicatorsConfig(BaseModel):
    rsi: RSIConfig = RSIConfig()
    macd: MACDConfig = MACDConfig()
    moving_averages: MovingAveragesConfig = MovingAveragesConfig()
    bollinger_bands: BollingerBandsConfig = BollingerBandsConfig()
    atr: ATRConfig = ATRConfig()
    stochastic: StochasticConfig = StochasticConfig()
    volume: VolumeConfig = VolumeConfig()


class SignalsConfig(BaseModel):
    min_confidence: int = 65
    min_agreement: int = 3


class AnalysisConfig(BaseModel):
    indicators: IndicatorsConfig = IndicatorsConfig()
    signals: SignalsConfig = SignalsConfig()


class SchedulerConfig(BaseModel):
    data_refresh_minutes: int = 15
    signal_check_minutes: int = 30
    daily_summary_time: str = "18:00"


class WhatsAppConfig(BaseModel):
    enabled: bool = False
    daily_summary: bool = True
    signal_alerts: bool = True
    min_alert_confidence: int = 70
    scanner_summary: bool = True


class NotificationsConfig(BaseModel):
    whatsapp: WhatsAppConfig = WhatsAppConfig()


class Settings(BaseModel):
    app: AppConfig = AppConfig()
    watchlist: WatchlistConfig = WatchlistConfig()
    data: DataConfig = DataConfig()
    analysis: AnalysisConfig = AnalysisConfig()
    scheduler: SchedulerConfig = SchedulerConfig()
    notifications: NotificationsConfig = NotificationsConfig()

    # Environment variables (not from config.yaml)
    alpha_vantage_api_key: Optional[str] = None
    whatsapp_phone: Optional[str] = None
    callmebot_api_key: Optional[str] = None


def load_config(config_path: Optional[str] = None) -> Settings:
    """Load configuration from config.yaml and environment variables."""
    if config_path is None:
        config_path = str(BASE_DIR / "config.yaml")

    config_data = {}
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, "r") as f:
            config_data = yaml.safe_load(f) or {}

    settings = Settings(**config_data)

    settings.alpha_vantage_api_key = os.getenv("ALPHA_VANTAGE_API_KEY") or None
    settings.whatsapp_phone = os.getenv("WHATSAPP_PHONE") or None
    settings.callmebot_api_key = os.getenv("CALLMEBOT_API_KEY") or None

    return settings


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = load_config()
    return _settings


def reset_settings():
    """Reset global settings (useful for testing)."""
    global _settings
    _settings = None
