"""API endpoints. Add new routers here and include them in app.py."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from mlflow.exceptions import MlflowException

from serving.model import ModelService
from serving.schemas import (
    HealthResponse,
    ModelInfo,
    PredictRequest,
    PredictResponse,
    ReadyResponse,
)

NOT_LOADED = "No model loaded: set SERVING_MODEL_NAME"

router = APIRouter()


def get_model(request: Request) -> ModelService:
    return request.app.state.model


def get_loaded_model(
    model: Annotated[ModelService, Depends(get_model)],
) -> ModelService:
    if not model.ready:
        raise HTTPException(status_code=503, detail=NOT_LOADED)
    return model


Model = Annotated[ModelService, Depends(get_model)]
LoadedModel = Annotated[ModelService, Depends(get_loaded_model)]


@router.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    """Liveness: the API process is up."""
    return HealthResponse()


@router.get(
    "/ready",
    response_model=ReadyResponse,
    responses={503: {"model": ReadyResponse, "description": "No model loaded"}},
    tags=["health"],
)
def ready(model: Model):
    """Readiness: a model is loaded and the API can predict."""
    body = ReadyResponse(
        ready=model.ready,
        model_name=model.settings.model_name,
        detail=None if model.ready else NOT_LOADED,
    )
    if model.ready:
        return body
    return JSONResponse(status_code=503, content=body.model_dump())


@router.get(
    "/model",
    response_model=ModelInfo,
    responses={503: {"description": "No model loaded"}},
    tags=["model"],
)
def model_info(model: LoadedModel) -> ModelInfo:
    """The served model and its input and output schema."""
    return ModelInfo(**model.info())


@router.post(
    "/predict",
    response_model=PredictResponse,
    responses={
        422: {"description": "The records don't match the model's input schema"},
        503: {"description": "No model loaded"},
    },
    tags=["model"],
)
def predict(body: PredictRequest, model: LoadedModel) -> PredictResponse:
    """Predict one value per record with the served model."""
    try:
        predictions = model.predict(body.records)
    except MlflowException as err:
        # Raised by the model's signature check, e.g. a missing column
        raise HTTPException(status_code=422, detail=err.message) from err
    return PredictResponse(
        model_name=model.settings.model_name, predictions=predictions
    )
