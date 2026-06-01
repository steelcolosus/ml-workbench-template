import os
from contextlib import contextmanager

import dotenv
import mlflow

TRACKING_ENV_VARS = (
    "MLFLOW_TRACKING_URI",
    "MLFLOW_TRACKING_TOKEN",
    "MLFLOW_TRACKING_USERNAME",
    "MLFLOW_TRACKING_PASSWORD",
)


def configure_tracking(root_path: str, is_local: bool) -> str:
    if is_local:
        for var in TRACKING_ENV_VARS:
            os.environ.pop(var, None)

        local_db = os.path.join(root_path, "mlflow.db")
        mlflow.set_tracking_uri(f"sqlite:///{local_db}")
    else:
        dotenv.load_dotenv()

    return mlflow.get_tracking_uri()


@contextmanager
def managed_run(experiment_name: str, run_name: str | None = None):
    active_run = mlflow.active_run()
    if active_run is not None:
        yield active_run
        return

    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=run_name) as run:
        yield run
