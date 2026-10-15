"""Base class for custom MLflow pyfunc models."""

import mlflow.pyfunc
import pandas as pd
from mlflow.models import infer_signature
from mlflow.models.model import ModelInfo

from core.store import Store
from utils.log import get_logger

logger = get_logger("MODEL")


class CustomModel(mlflow.pyfunc.PythonModel):
    """
    Subclass it and implement predict():

        class PriceModel(CustomModel):
            def predict(self, context, model_input, params=None):
                ...

        model = PriceModel()
        model.save(store, "price_model", sample=X.head())    # in a step
        loaded = CustomModel.load(store, "price_model")       # in serving
    """

    def save(
        self,
        store: Store,
        name: str,
        sample: pd.DataFrame,
        location: str = "models",
        code_paths: list = None,
        log_model: bool = True,
        params: dict = None,
        sync: bool = True,
    ) -> ModelInfo | None:
        """
        Save the model to `<location>/<name>` through the store (uploaded when
        store.sync_s3 is on, unless sync=False) and, if `log_model`, log it to the
        active MLflow run. The signature is inferred by predicting on `sample`,
        which is also stored as the input example.

        Returns the ModelInfo of the logged model, or None.
        """
        signature = infer_signature(sample, self.predict({}, sample), params=params)

        model_info = None
        if log_model:
            model_info = mlflow.pyfunc.log_model(
                name=name,
                python_model=self,
                signature=signature,
                input_example=sample,
                code_paths=code_paths,
            )

        path = store.save_artifact(
            location,
            name,
            writer=lambda path: mlflow.pyfunc.save_model(
                path=path,
                python_model=self,
                signature=signature,
                input_example=sample,
                code_paths=code_paths,
            ),
            sync=sync,
        )
        logger.info(f"Saved model {name} to {path}")
        return model_info

    @staticmethod
    def load(store: Store, name: str, location: str = "models"):
        """Load a saved model (downloading it when missing and sync is on)."""
        return store.load_artifact(location, name, reader=mlflow.pyfunc.load_model)
