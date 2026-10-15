"""Runs the pipeline steps (MLflow projects in src/steps) from main.py."""

import os
from pathlib import Path

import mlflow
from omegaconf import DictConfig

from core.step import PIPELINE_RUN_ENV
from core.store import STORE_CONFIG_ENV, Store
from utils.config import serialize_config
from utils.log import get_logger

logger = get_logger("PIPELINE")


class StepRunner:
    """
    Runs the steps of one pipeline run. Every step gets:
    - its config section as a YAML file (the `config_path` parameter)
    - the parameters passed to run(), e.g. input_artifact / output_artifact
    - the resolved store config ($STORE_CONFIG), CLI overrides included
    - the pipeline run as its parent run in the MLflow UI
    """

    def __init__(
        self,
        steps_path,
        config: DictConfig,
        store: Store,
        work_dir,
        env_manager: str,
        parent_run_id: str = None,
    ):
        self.steps_path = Path(steps_path)
        self.config = config
        self.work_dir = Path(work_dir)
        self.env_manager = env_manager

        # Inherited by every step process
        os.environ[STORE_CONFIG_ENV] = store.dump(self.work_dir / "store.yaml")
        if parent_run_id:
            os.environ[PIPELINE_RUN_ENV] = parent_run_id

    def run(self, step: str, run_name: str = None, **parameters):
        """
        Run src/steps/<step> with its config section and `parameters`. The MLflow
        run is named `run_name` (default: the step's name). A step that doesn't
        exist yet is skipped with a warning.
        """
        step_path = self.steps_path / step
        if not (step_path / "MLproject").exists():
            logger.warning(
                f"Skipping step {step!r}: no MLflow project in {step_path} "
                "(create it with `make step`)"
            )
            return None

        config_path = serialize_config(
            self.config.get(step) or {}, self.work_dir / f"{step}.yaml"
        )
        logger.info(f"Running step {step!r} with parameters {parameters}")
        return mlflow.run(
            str(step_path),
            "main",
            parameters={"config_path": config_path, **parameters},
            env_manager=self.env_manager,
            run_name=run_name or step,
        )
