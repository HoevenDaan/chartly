"""FastAPI application factory for StockPulse."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.routes import router as api_router
from app.config import get_settings
from app.data.cache import init_db
from app.scheduler.jobs import start_scheduler, stop_scheduler
from app.utils.logger import get_logger, setup_logger

TEMPLATE_DIR = Path(__file__).parent / "dashboard" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    settings = get_settings()
    setup_logger(settings.app.log_level)
    logger = get_logger("main")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Initialize watchlist with defaults if empty
    from app.data.cache import get_watchlist, add_to_watchlist
    existing = await get_watchlist()
    if not existing:
        for stock in settings.watchlist.default_stocks:
            await add_to_watchlist(stock.symbol, stock.name)
        logger.info(f"Initialized watchlist with {len(settings.watchlist.default_stocks)} default stocks")

    # Start scheduler
    start_scheduler()

    yield

    # Shutdown
    stop_scheduler()
    logger.info("StockPulse shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app.name,
        description="Stock Market Technical Advisor",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Include API routes
    app.include_router(api_router)

    # Dashboard route
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        return templates.TemplateResponse("index.html", {"request": request})

    # Scanner page route
    @app.get("/scanner", response_class=HTMLResponse)
    async def scanner_page(request: Request):
        return templates.TemplateResponse("scanner.html", {"request": request})

    return app
