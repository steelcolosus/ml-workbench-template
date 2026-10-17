"""Loads the served model through the store and predicts with it."""

import json
from typing import Any

import numpy as np
import pandas as pd
from mlflow.types import DataType

from core.model import CustomModel
from core.store import Store
from serving.settings import Settings
from utils.log import get_logger

logger = get_logger("SERVING")


class ModelNotLoadedError(RuntimeError):
    pass


class ModelService:
    def __init__(self, settings: Settings, store: Store):
        self.settings = settings
        self.store = store
        self.model = None

    @property
    def ready(self) -> bool:
        return self.model is not None

    def load(self) -> None:
        """
        Load <model_location>/<model_name> from the store (downloaded first when
        it's missing locally and store.sync_s3 is on).
        """
        name, location = self.settings.model_name, self.settings.model_location
        logger.info(f"Loading model {name!r} from location {location!r}")
        self.model = CustomModel.load(self.store, name, location=location)

    def info(self) -> dict[str, Any]:
        signature = self._loaded().metadata.signature
        return {
            "name": self.settings.model_name,
            "location": self.settings.model_location,
            "inputs": signature.inputs.to_dict() if signature else None,
            "outputs": signature.outputs.to_dict() if signature else None,
        }

    def predict(self, records: list[dict[str, Any]]) -> list[Any]:
        model = self._loaded()
        data = _match_float_columns(
            pd.DataFrame.from_records(records), model.metadata.signature
        )
        return _to_json(model.predict(data))

    def _loaded(self):
        if self.model is None:
            raise ModelNotLoadedError(
                "No model loaded: set SERVING_MODEL_NAME to the name of a saved model"
            )
        return self.model


def _match_float_columns(data: pd.DataFrame, signature) -> pd.DataFrame:
    """
    JSON numbers like 3 arrive as integers, and MLflow refuses to convert them to
    the float columns of a model's signature: cast those columns first.
    """
    if signature is None or signature.inputs.is_tensor_spec():
        return data
    floats = {DataType.double: "float64", DataType.float: "float32"}
    for column in signature.inputs.inputs:
        if (
            column.name in data
            and column.type in floats
            and pd.api.types.is_integer_dtype(data[column.name])
        ):
            data[column.name] = data[column.name].astype(floats[column.type])
    return data


def _to_json(result) -> list[Any]:
    """Model output as JSON-compatible values (no numpy or pandas types)."""
    if isinstance(result, pd.DataFrame):
        return json.loads(result.to_json(orient="records"))
    if isinstance(result, pd.Series):
        return json.loads(result.to_json(orient="values"))
    if isinstance(result, np.ndarray):
        return result.tolist()
    return list(result)
