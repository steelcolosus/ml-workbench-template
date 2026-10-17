"""Request and response models: they validate the API and document it in /docs."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    ready: bool = Field(description="True when a model is loaded")
    model_name: str | None = Field(description="The model being served")
    detail: str | None = Field(default=None, description="Why it isn't ready")


class ModelInfo(BaseModel):
    name: str
    location: str = Field(description="Store location the model was loaded from")
    inputs: list[dict[str, Any]] | None = Field(
        description="Input columns and types from the model's signature"
    )
    outputs: list[dict[str, Any]] | None = Field(
        description="Output columns and types from the model's signature"
    )


class PredictRequest(BaseModel):
    records: list[dict[str, Any]] = Field(
        min_length=1,
        description="Rows to predict: one object per row, column name to value",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"records": [{"feature_a": 1.5, "feature_b": "x"}]}]
        }
    )


class PredictResponse(BaseModel):
    model_name: str
    predictions: list[Any] = Field(description="One prediction per input row")
