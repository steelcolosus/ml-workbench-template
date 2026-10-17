from pathlib import Path

import hydra
import mlflow
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig

from libs.tracking import (
    configure_tracking,
    managed_run,
    prepare_step_environment,
)
from utils.config import with_absolute_root
from utils.log import get_logger

logger = get_logger("RUN")


@hydra.main(config_name="config", config_path=".", version_base=None)
def go(config: DictConfig):
    # A relative root ($PROJECT_ROOT unset) is resolved from this folder
    with_absolute_root(config, Path(__file__).parent)
    root_path = str(config["root"])

    tracking_uri = configure_tracking(
        root_path=root_path,
        is_local=bool(config["launcher"]["local"]),
    )

    project_name = config["main"]["project_name"]
    experiment_name = f"{project_name}_{config['main']['experiment_name']}"
    steps = config["main"]["steps"]
    hydra_options = " ".join(HydraConfig.get().overrides.task)
    env_manager = (
        "local" if config["launcher"]["local"] else config["launcher"]["env_manager"]
    )
    run_name = config["launcher"].get("run_name") or f"{project_name}_pipeline"
    logger.info(f"MLflow tracking URI: {tracking_uri}")

    prepare_step_environment(root_path, env_manager)

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
