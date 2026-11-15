from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from edt.api.errors import install_error_handlers
from edt.api.routes import health
from edt.config import Settings, load_settings

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Earth Digital Twin - Trend Detective API", version="0.2.0")
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type"],
    )
    install_error_handlers(app)
    app.include_router(health.router, prefix=API_PREFIX)
    return app


def __getattr__(name: str):
    # `uvicorn edt.api.app:app` builds the app lazily so importing this module needs no env vars.
    if name == "app":
        app = create_app()
        globals()["app"] = app
        return app
    raise AttributeError(name)
