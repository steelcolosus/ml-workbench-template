"""
FastAPI app that serves a model saved through the store.

Run it with `make serve` (or the serving Docker image) and open /docs for the
interactive documentation (Swagger UI) or /redoc.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.store import Store
from serving.model import ModelService
from serving.routes import router
from serving.settings import Settings

DESCRIPTION = """
Predictions from the model set in `SERVING_MODEL_NAME`, loaded from the store
location `SERVING_MODEL_LOCATION` (default `models`).

- `GET /health`: the API is up
- `GET /ready`: a model is loaded
- `GET /model`: the model's name and input/output schema
- `POST /predict`: one prediction per record
"""

TAGS = [
    {"name": "health", "description": "Liveness and readiness checks"},
    {"name": "model", "description": "The served model and its predictions"},
]


def create_app(settings: Settings = None, store: Store = None) -> FastAPI:
    """
    Build the app. Without arguments, settings come from the environment and the
    store from config.yaml (or $STORE_CONFIG); tests pass their own.
    """
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        model = ModelService(settings, store or Store.from_env())
        if settings.model_name:
            # Fails startup when the configured model can't be loaded
            model.load()
        app.state.model = model
        yield

    app = FastAPI(
        title=settings.title,
        version=settings.version,
        description=DESCRIPTION,
        openapi_tags=TAGS,
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()
