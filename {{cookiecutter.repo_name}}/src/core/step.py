"""Base class for pipeline steps."""

import argparse
import inspect
import os
from abc import ABC, abstractmethod
from pathlib import Path

import mlflow
from omegaconf import DictConfig, OmegaConf

from core.store import Store
from utils.config import load_step_config
from utils.log import get_logger

# Run ID of the pipeline run (set by the runner in main.py). Steps tag their own
# run with it so the MLflow UI shows them nested under the pipeline run.
PIPELINE_RUN_ENV = "PIPELINE_RUN_ID"


class Step(ABC):
    """
    A step is an MLflow project in src/steps/<name>/ whose run.py subclasses
    Step, implements run() and calls main():

        class BasicCleaning(Step):
            @classmethod
            def add_arguments(cls, parser):
                parser.add_argument("--input_artifact", type=str, required=True)

            def run(self):
                df = self.store.load_data("raw", self.args.input_artifact)
                ...

        if __name__ == "__main__":
            BasicCleaning.main()

    Inside run(): `self.args` has the step's parameters, `self.config` its config
    section, plus `self.store` and `self.logger`.
    """

    # Defaults to the step's folder name, which matches its config section
    name: str = None

    def __init__(
        self,
        name: str,
        args: argparse.Namespace,
        config: DictConfig,
        store: Store,
    ):
        self.name = name
        self.args = args
        self.config = config
        self.store = store
        self.logger = get_logger(name)

    @abstractmethod
    def run(self):
        """The step's work."""

    @classmethod  # noqa: B027 - empty on purpose: steps without parameters skip it
    def add_arguments(cls, parser: argparse.ArgumentParser):
        """
        Declare the step's parameters: the same ones as in its MLproject.
        `--config_path` is always added by main().
        """

    @classmethod
    def step_name(cls) -> str:
        return cls.name or Path(inspect.getfile(cls)).resolve().parent.name

    @classmethod
    def main(cls, argv: list = None):
        """
        Entry point of run.py: parse the parameters, load the step's config and
        the store, and call run() inside the step's MLflow run.
        """
        name = cls.step_name()

        parser = argparse.ArgumentParser(description=cls.__doc__)
        parser.add_argument(
            "--config_path",
            type=str,
            default=None,
            help="YAML with this step's config section (written by main.py). "
            "Empty: the step's section of config.yaml",
        )
        cls.add_arguments(parser)
        args = parser.parse_args(argv)

        config = load_step_config(name, args.config_path or None)
        step = cls(name=name, args=args, config=config, store=Store.from_env())

        # Continues the run `mlflow run` created for the step (MLFLOW_RUN_ID), or
        # starts one when run.py is executed directly
        with mlflow.start_run():
            parent_run_id = os.environ.get(PIPELINE_RUN_ENV)
            if parent_run_id:
                mlflow.set_tag("mlflow.parentRunId", parent_run_id)
            mlflow.log_dict(OmegaConf.to_container(config), "step_config.yaml")
            step.logger.info(f"Running {name} with {vars(args)}")
            step.run()
