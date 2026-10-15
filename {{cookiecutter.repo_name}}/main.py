import os
import tempfile
from pathlib import Path

import hydra
import mlflow
from omegaconf import DictConfig, OmegaConf

from core.store import STORE_CONFIG_ENV, Store
from libs.tracking import (
    configure_tracking,
    managed_run,
    prepare_step_environment,
)
from utils.log import get_logger

_steps = [
    # NOTE: Add steps here, in execution order. Each step is an MLflow project in
    # src/steps/<step> (create one with `make step`) and receives the keys of the config
    # section with the same name as parameters.
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

    experiment_name = (
        f"{config['main']['project_name']}_{config['main']['experiment_name']}"
    )

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
        managed_run(experiment_name=experiment_name) as run,
        tempfile.TemporaryDirectory() as tmp_dir,
    ):
        logger.info(f"MLflow run ID: {run.info.run_id}")

        # Hand the resolved store config (CLI overrides included) to the steps
        os.environ[STORE_CONFIG_ENV] = store.dump(Path(tmp_dir) / "store.yaml")

        for step in active_steps:
            step_path = root_path / "src" / "steps" / step
            if not (step_path / "MLproject").exists():
                logger.warning(
                    f"Skipping step {step!r}: no MLflow project in {step_path} "
                    "(create it with `make step`)"
                )
                continue

            section = config.get(step)
            parameters = (
                OmegaConf.to_container(section, resolve=True)
                if section is not None
                else {}
            )
            logger.info(f"Running step {step!r} with parameters {parameters}")
            mlflow.run(
                str(step_path),
                "main",
                parameters=parameters,
                env_manager=env_manager,
                experiment_name=experiment_name,
            )


if __name__ == "__main__":
    go()
