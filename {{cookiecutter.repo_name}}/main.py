import tempfile
from pathlib import Path

import hydra
from omegaconf import DictConfig

from core.store import Store
from libs.pipeline import StepRunner
from libs.tracking import (
    configure_tracking,
    managed_run,
    prepare_step_environment,
)
from utils.log import get_logger

_steps = [
    # NOTE: Add steps here, in execution order. Each step is an MLflow project in
    # src/steps/<step> (create one with `make step`) with a section of the same
    # name in config.yaml, and runs in its block below.
    "get_data",
    "basic_cleaning",
    "data_check",
    "preprocessing",
]

# This automatically reads in the configuration
logger = get_logger("MAIN")


@hydra.main(config_name="config", config_path=".", version_base=None)
def go(config: DictConfig):

    # Steps to execute
    steps_par = config["main"]["steps"]
    active_steps = (
        _steps
        if steps_par == "all"
        else [step.strip() for step in steps_par.split(",")]
    )
    unknown_steps = [step for step in active_steps if step not in _steps]
    if unknown_steps:
        raise ValueError(f"Unknown steps {unknown_steps}. Available: {_steps}")

    root_path = Path(config["root"]).resolve()
    is_local = bool(config["launcher"]["local"])
    tracking_uri = configure_tracking(root_path=str(root_path), is_local=is_local)
    env_manager = "local" if is_local else config["launcher"]["env_manager"]
    store = Store.from_config(config["store"], base_dir=root_path)

    project_name = config["main"]["project_name"]
    experiment_name = f"{project_name}_{config['main']['experiment_name']}"
    run_name = config["launcher"].get("run_name") or f"{project_name}_pipeline"

    logger.info(f"Running the following steps: {active_steps}")
    logger.info(f"Experiment name: {experiment_name}")
    logger.info(f"Environment manager: {env_manager}")
    logger.info(f"Root path: {root_path}")
    logger.info(f"MLflow tracking URI: {tracking_uri}")
    logger.info(f"Store sync to S3: {store.sync_s3}")
    for name, location in store.locations.items():
        logger.info(f"Store location {name}: {location.path}")

    prepare_step_environment(str(root_path), env_manager)

    with (
        managed_run(experiment_name=experiment_name, run_name=run_name) as run,
        tempfile.TemporaryDirectory() as tmp_dir,
    ):
        logger.info(f"MLflow run ID: {run.info.run_id}")

        # Each step gets its config section (config_path), the parameters below,
        # the resolved store config and this run as its parent
        runner = StepRunner(
            steps_path=root_path / "src" / "steps",
            config=config,
            store=store,
            work_dir=tmp_dir,
            env_manager=env_manager,
            parent_run_id=run.info.run_id,
        )

        if "get_data" in active_steps:
            runner.run(
                "get_data",
                output_artifact=config["get_data"]["output_artifact"],
            )

        if "basic_cleaning" in active_steps:
            runner.run(
                "basic_cleaning",
                input_artifact=config["basic_cleaning"]["input_artifact"],
                output_artifact=config["basic_cleaning"]["output_artifact"],
            )

        if "data_check" in active_steps:
            runner.run(
                "data_check",
                input_artifact=config["data_check"]["input_artifact"],
            )

        if "preprocessing" in active_steps:
            runner.run(
                "preprocessing",
                input_artifact=config["preprocessing"]["input_artifact"],
                output_artifact=config["preprocessing"]["output_artifact"],
            )


if __name__ == "__main__":
    go()
