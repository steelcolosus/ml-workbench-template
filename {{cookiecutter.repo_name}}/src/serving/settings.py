"""Serving settings, read from environment variables."""

import os
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version

PROJECT = {{ cookiecutter.repo_name | tojson }}


def _project_version() -> str:
    try:
        return version(PROJECT)
    except PackageNotFoundError:
        return "0.0.0"


@dataclass(frozen=True)
class Settings:
    # Model to serve: <model_location>/<model_name> in the store (empty: none)
    model_name: str | None = None
    model_location: str = "models"
    title: str = {{ (cookiecutter.project_name ~ " API") | tojson }}
    version: str = "0.0.0"

    @classmethod
    def from_env(cls) -> "Settings":
        """
        SERVING_MODEL_NAME: name of the model saved with CustomModel.save (or
            through store.save_artifact with an MLflow pyfunc writer)
        SERVING_MODEL_LOCATION: store location of the model (default: models)
        """
        return cls(
            model_name=os.environ.get("SERVING_MODEL_NAME") or None,
            model_location=os.environ.get("SERVING_MODEL_LOCATION") or "models",
            version=_project_version(),
        )
