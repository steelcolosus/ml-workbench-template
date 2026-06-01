import logging
import os

import hydra
import mlflow
from hydra.core.hydra_config import HydraConfig
from libs.mlflow_runtime import configure_tracking, managed_run
from omegaconf import DictConfig

# This automatically reads in the configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)-15s %(message)s")
logger = logging.getLogger()
# Load environment variables
parent_dir = os.path.dirname(os.path.abspath(__file__))
# Add it to PYTHONPATH
os.environ['PYTHONPATH'] = parent_dir


@hydra.main(config_name="config", config_path=".", version_base=None)
def go(config: DictConfig):
    root_path = hydra.utils.get_original_cwd()

    tracking_uri = configure_tracking(
        root_path=root_path,
        is_local=bool(config["launcher"]["local"]),
    )

    project_name = config["main"]["project_name"]
    experiment_name = (
        f"{project_name}_{config['main']['experiment_name']}"
    )
    steps = config["main"]["steps"]
    hydra_options = " ".join(HydraConfig.get().overrides.task)
    env_manager = (
        "local"
        if config["launcher"]["local"]
        else config["launcher"]["env_manager"]
    )
    run_name = config["launcher"].get("run_name") or f"{project_name}_pipeline"
    logger.info(f"MLflow tracking URI: {tracking_uri}")

    with managed_run(
        experiment_name=experiment_name,
        run_name=run_name,
    ) as mlrun:
        _ = mlflow.run(
            root_path,
            "main",
            parameters={
                "steps": steps,
                "hydra_options": hydra_options,
            },
            env_manager=env_manager,
            run_id=mlrun.info.run_id,
        )


if __name__ == "__main__":
    go()
