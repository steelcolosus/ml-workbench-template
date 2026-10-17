import hashlib
import os
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path

import dotenv
import mlflow

# Environments MLflow creates for the steps (env_manager uv or virtualenv)
STEP_ENVS_DIR = ".mlflow-envs"

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


def prepare_step_environment(root_path: str, env_manager: str) -> None:
    """Set up the environment that `mlflow.run` starts the steps from.

    local: steps run `python` from PATH, so put this interpreter first (the venv
    does not need to be activated, e.g. under `make pipeline`).

    uv / virtualenv: MLflow creates one environment per step and installs its
    requirements.txt from a temporary folder, so the steps find the project
    (`-e ${PROJECT_ROOT}`) through the PROJECT_ROOT variable instead of a
    relative path. MLflow caches the environments by the text of the
    requirements, which does not change when the project's dependencies do, so
    they live in .mlflow-envs/<hash of uv.lock>: rebuilt when uv.lock changes and
    never shared with another project. The versions in uv.lock are passed to
    pip/uv as constraints, so the steps run with the same versions as .venv.
    """
    os.environ["PROJECT_ROOT"] = root_path

    if env_manager == "local":
        os.environ["PATH"] = os.pathsep.join(
            [os.path.dirname(sys.executable), os.environ.get("PATH", "")]
        )
        return
    if env_manager not in ("uv", "virtualenv"):
        return

    lock = Path(root_path) / "uv.lock"
    if not lock.exists():
        raise FileNotFoundError(f"{lock} not found: run `make venv` first")
    lock_hash = hashlib.sha256(lock.read_bytes()).hexdigest()[:12]
    env_root = Path(root_path) / STEP_ENVS_DIR / lock_hash
    env_root.mkdir(parents=True, exist_ok=True)

    constraints = env_root / "constraints.txt"
    if not constraints.exists():
        subprocess.run(
            [
                "uv",
                "export",
                "--frozen",
                "--no-emit-project",
                "--no-hashes",
                "--quiet",
                "--output-file",
                str(constraints),
            ],
            cwd=root_path,
            check=True,
        )

    os.environ.setdefault("MLFLOW_ENV_ROOT", str(env_root))
    os.environ["PIP_CONSTRAINT"] = str(constraints)
    os.environ["UV_CONSTRAINT"] = str(constraints)


@contextmanager
def managed_run(experiment_name: str, run_name: str | None = None):
    active_run = mlflow.active_run()
    if active_run is not None:
        yield active_run
        return

    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=run_name) as run:
        yield run


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
