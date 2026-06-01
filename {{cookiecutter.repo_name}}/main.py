import os
import tempfile

import hydra
from libs.log.log_config import get_logger
from libs.mlflow_runtime import configure_tracking, managed_run
from omegaconf import DictConfig

_steps = [
    # NOTE: Add steps here
    'get_data',
    'basic_cleaning',
    'data_check',
    'preprocessing',
]

# This automatically reads in the configuration
logger = get_logger("MAIN")


@hydra.main(config_name='config',  config_path=".", version_base=None)
def go(config: DictConfig):

    # Steps to execute
    steps_par = config['main']['steps']
    active_steps = steps_par.split(",") if steps_par != "all" else _steps
    root_path = hydra.utils.get_original_cwd()
    config_path = os.path.join(
        root_path,
        "config.yaml"
    )
    model_path = os.path.join(
        root_path,
        'models'
    )
    data_path = os.path.join(
        root_path,
        "data"
    )
    raw_data = os.path.join(
        data_path,
        'raw'
    )
    processed_data = os.path.join(
        data_path,
        'processed'
    )

    is_local = bool(config.get("launcher", {}).get("local", False))
    tracking_uri = configure_tracking(root_path=root_path, is_local=is_local)

    # Move to a temporary directory
    experiment_name = (
        f"{config['main']['project_name']}_"
        f"{config['main']['experiment_name']}"
    )
    env_manager = "local" if is_local else "configured"

    logger.info(f"Running the following steps: {active_steps}")
    logger.info(f"Experiment name: {experiment_name}")
    logger.info(f"Environment manager: {env_manager}")
    logger.info(f"Root path: {root_path}")
    logger.info(f"Config path: {config_path}")
    logger.info(f"Model path: {model_path}")
    logger.info(f"Data path: {data_path}")
    logger.info(f"Raw data path: {raw_data}")
    logger.info(f"Processed data path: {processed_data}")
    logger.info(f"MLflow tracking URI: {tracking_uri}")

    with managed_run(experiment_name=experiment_name) as run:
        logger.info(f"MLflow run ID: {run.info.run_id}")

        with tempfile.TemporaryDirectory():

            if "get_data" in active_steps:
                # Download file and load
                logger.info("Getting data")

            if "basic_cleaning" in active_steps:
                ##################
                # Implement here #
                ##################
                logger.info("Basic cleaning")

            if "data_check" in active_steps:
                ##################
                # Implement here #
                ##################
                logger.info("Data check")

            if "preprocessing" in active_steps:
                ##################
                # Implement here #
                ##################
                logger.info("Preprocessing")


if __name__ == "__main__":
    go()
