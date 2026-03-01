"""Custom exception classes for StockPulse."""


class StockPulseError(Exception):
    """Base exception for StockPulse."""
    pass


class DataFetchError(StockPulseError):
    """Raised when stock data cannot be fetched from any source."""
    pass


class InvalidSymbolError(StockPulseError):
    """Raised when an invalid stock symbol is provided."""
    pass


class CacheError(StockPulseError):
    """Raised when cache operations fail."""
    pass


class NotificationError(StockPulseError):
    """Raised when notification delivery fails."""
    pass


class ConfigError(StockPulseError):
    """Raised when configuration is invalid."""
    pass
