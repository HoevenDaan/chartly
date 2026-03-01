"""Data models and schemas for StockPulse."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class StockInfo(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    week_52_high: Optional[float] = None
    week_52_low: Optional[float] = None


class StockPrice(BaseModel):
    symbol: str
    price: float
    change: float = 0.0
    change_percent: float = 0.0
    volume: int = 0
    timestamp: datetime = datetime.now()
    market_open: bool = True


class OHLCVData(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class IndicatorValues(BaseModel):
    rsi: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    atr: Optional[float] = None
    stoch_k: Optional[float] = None
    stoch_d: Optional[float] = None
    volume_avg: Optional[float] = None
    volume_ratio: Optional[float] = None
    volume_spike: bool = False
    week_52_position: Optional[float] = None
    golden_cross: bool = False
    death_cross: bool = False
    price_above_sma_50: Optional[bool] = None
    price_above_sma_200: Optional[bool] = None


class Signal(BaseModel):
    signal: str  # BUY, SELL, HOLD
    confidence: int = 0  # 0-100
    reasons: list[str] = []
    buy_signals: list[str] = []
    sell_signals: list[str] = []


class KeyLevels(BaseModel):
    support: Optional[float] = None
    support_label: str = ""
    resistance: Optional[float] = None
    resistance_label: str = ""
    stop_loss: Optional[float] = None


class AdvisorReport(BaseModel):
    symbol: str
    name: str
    price: float
    signal: Signal
    indicators: IndicatorValues
    key_levels: KeyLevels
    summary: str
    disclaimer: str
    timestamp: datetime = datetime.now()


class StockData(BaseModel):
    info: StockInfo
    price: StockPrice
    history: list[OHLCVData] = []
    indicators: Optional[IndicatorValues] = None
    signal: Optional[Signal] = None
    report: Optional[AdvisorReport] = None
