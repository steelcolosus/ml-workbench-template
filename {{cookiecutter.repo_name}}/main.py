import json
import logging
import os
import tempfile
from pdb import run

import dotenv
import hydra
import mlflow
from omegaconf import DictConfig

_steps = [
    # NOTE: Add steps here
    'get_data',
    'basic_cleaning',
    'data_check',
    'preprocessing',
]

# This automatically reads in the configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()
# Load environment variables
dotenv.load_dotenv()
# This automatically reads in the configuration


@hydra.main(config_name='config',  config_path=".", version_base="1.1")
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
    # Move to a temporary directory
    experiment_name = f"{config['main']['project_name']}_{config['main']['experiment_name']}"

    mlflow.set_experiment(experiment_name)
    env_manager = "local"
    with mlflow.start_run():

        with tempfile.TemporaryDirectory() as tmp_dir:

            if "get_data" in active_steps:
                # Download file and load in W&B
                pass

            if "basic_cleaning" in active_steps:
                ##################
                # Implement here #
                ##################
                pass

            if "data_check" in active_steps:
                ##################
                # Implement here #
                ##################
                pass

            if "preprocessing" in active_steps:
                ##################
                # Implement here #
                ##################
                pass


if __name__ == "__main__":
    go()
