from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.services.inference_service import load_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.models = load_models(settings.model_dir)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    # Browsers reject allow_credentials=True when allow_origins=["*"].
    # Use allow_origin_regex instead so credentials still work with explicit origins.
    origins = settings.cors_origins
    if origins == ["*"]:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/health", tags=["health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok", "environment": settings.app_env}

    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
