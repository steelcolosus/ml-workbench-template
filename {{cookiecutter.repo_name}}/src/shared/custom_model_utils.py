import mlflow.pyfunc
import pandas as pd
from mlflow.models import infer_signature

from libs.log.log_config import get_logger
from libs.store import Store

logger = get_logger("CUSTOM_MODEL_UTILS")


def register_model(run_id, model_name):
    """
    Register model in mlflow

    Args:
        run_id: str
        model_name: str

    Returns:
        None
    """

    mlflow.register_model(f"runs:/{run_id}/{model_name}", model_name)


def save_custom_model(
    model: mlflow.pyfunc.PythonModel,
    model_name,
    store: Store,
    sample: pd.DataFrame,
    code_paths=None,
    location="models",
    log_model=True,
    model_params=None,
    sync=True,
):
    """
    Save a custom pyfunc model to `<location>/<model_name>` through the store
    (uploaded to S3 when store.sync_s3 is on, unless sync=False) and, if
    `log_model`, log it to the active MLflow run.

    Returns the ModelInfo of the logged model, or None.
    """
    result = model.predict({}, sample)

    signature = infer_signature(sample, result, params=model_params)

    model_info = None
    if log_model:
        model_info = mlflow.pyfunc.log_model(
            name=model_name,
            python_model=model,
            signature=signature,
            code_paths=code_paths,
        )

    path = store.save_artifact(
        location,
        model_name,
        writer=lambda path: mlflow.pyfunc.save_model(
            path=path,
            python_model=model,
            signature=signature,
            code_paths=code_paths,
        ),
        sync=sync,
    )
    logger.info(f"Saved model {model_name} to {path}")

    return model_info
