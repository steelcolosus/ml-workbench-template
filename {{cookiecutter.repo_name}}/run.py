import argparse
import logging
import tempfile

import dotenv
import mlflow
import yaml

# This automatically reads in the configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()
# Load environment variables
dotenv.load_dotenv()


def go(args):
    hydra_options = args.hydra_options
    steps = args.steps

    with open("config.yaml") as fp:
        model_config = yaml.safe_load(fp)

    experiment_name = f"{model_config['main']['project_name']}_{model_config['main']['experiment_name']}"

    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name="Main") as mlrun:
        with tempfile.TemporaryDirectory() as tmp_dir:
            _ = mlflow.run(
                ".",
                "main",
                parameters={
                    'steps': steps if steps else "all",
                    'hydra_options': hydra_options if hydra_options else '',
                },
                run_id=mlrun.info.run_id,

            )


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Run the pipeline")

    parser.add_argument(
        "--steps",
        type=str,  # INSERT TYPE HERE: str, float or int,
        help="coma separated steps",  # INSERT DESCRIPTION HERE,
        required=False
    )

    parser.add_argument(
        "--hydra_options",
        type=str,  # INSERT TYPE HERE: str, float or int,
        help="Hydra options",  # INSERT DESCRIPTION HERE,
        required=False
    )

    args = parser.parse_args()

    go(args)
