"""Entry point to start StockPulse."""

import sys
import os

# Add the project root to path so 'app' package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from app.config import get_settings


def main():
    import yfinance
    print(f"Python: {sys.executable}")
    print(f"yfinance: {yfinance.__version__}")

    settings = get_settings()

    banner = """
╔══════════════════════════════════════════╗
║         StockPulse v1.0.0               ║
║    Stock Market Technical Advisor        ║
║                                          ║
║    Dashboard: http://{host}:{port}      ║
║    API Docs:  http://{host}:{port}/docs ║
╚══════════════════════════════════════════╝
""".format(host=settings.app.host, port=settings.app.port)

    print(banner)

    uvicorn.run(
        "app.main:create_app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
        factory=True,
        log_level=settings.app.log_level.lower(),
    )


if __name__ == "__main__":
    main()
