"""ASGI entry point for deployment."""
from app.main import create_app

app = create_app()
