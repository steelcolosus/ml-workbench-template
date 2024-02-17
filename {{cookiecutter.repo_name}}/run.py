import argparse
import logging
import os
import tempfile

import dotenv
import mlflow
import yaml

# This automatically reads in the configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()
# Load environment variables
parent_dir = os.path.dirname(os.path.abspath(__file__))
# Add it to PYTHONPATH
os.environ['PYTHONPATH'] = parent_dir


def go(args):
    hydra_options = args.hydra_options
    steps = args.steps

    with open("config.yaml") as fp:
        model_config = yaml.safe_load(fp)

    project_name = model_config['main']['project_name']
    experiment_name = f"{project_name}_{model_config['main']['experiment_name']}"
    env_manager = "local" if args.local else "virtualenv"
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=f"{project_name}_pipeline") as mlrun:
        with tempfile.TemporaryDirectory() as tmp_dir:
            _ = mlflow.run(
                ".",
                "main",
                parameters={
                    'steps': steps,
                    'hydra_options': hydra_options,
                },
                env_manager=env_manager,
                run_id=mlrun.info.run_id,

            )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run the pipeline")

    parser.add_argument(
        "--steps",
        type=str,  # INSERT TYPE HERE: str, float or int,
        help="coma separated steps",  # INSERT DESCRIPTION HERE,
        default="all",
        required=False
    )

    parser.add_argument(
        "--hydra_options",
        type=str,  # INSERT TYPE HERE: str, float or int,
        help="Hydra options",  # INSERT DESCRIPTION HERE,
        default="",
        required=False
    )

    parser.add_argument(
        "--local",
        type=bool,  # INSERT TYPE HERE: str, float or int,
        help="Run experiment locally without tracking server",
        default=False,
        required=False
    )

    args = parser.parse_args()
    is_local = args.local
    if not is_local:
        dotenv.load_dotenv()

    args = parser.parse_args()

    go(args)
