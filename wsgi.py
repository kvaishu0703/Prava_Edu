"""Production WSGI entry point used by Gunicorn."""

from app import create_app

app = create_app("production")
