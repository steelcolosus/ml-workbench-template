import os
from pathlib import Path

import yaml
from omegaconf import DictConfig, OmegaConf

PROJECT_CONFIG = "config.yaml"


def load_config(str_conf: str) -> dict:
    """
    Load a config object from a string
    """
    with open(str_conf) as fp:
        model_config = yaml.safe_load(fp)

    return model_config


def serialize_config(config: dict, output_path: str):
    """
    Serialize a config object (dict or OmegaConf node) to a YAML file, with its
    ${...} references resolved so the file can be loaded on its own
    """
    config_path = os.path.abspath(output_path)
    with open(config_path, "w+") as fp:
        fp.write(OmegaConf.to_yaml(config, resolve=True))

    return config_path


def find_project_config(start=None) -> Path:
    """
    The project's config.yaml: searched from `start` ($PROJECT_ROOT or the
    current directory by default) upwards, so it is found from a step's folder.
    """
    start = Path(start or os.environ.get("PROJECT_ROOT") or os.getcwd()).resolve()
    for folder in (start, *start.parents):
        candidate = folder / PROJECT_CONFIG
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"No {PROJECT_CONFIG} found in {start} or its parents. Run from the "
        "project or set $PROJECT_ROOT."
    )


def load_step_config(step: str, config_path: str = None) -> DictConfig:
    """
    A step's config: the file main.py serialized for it (`config_path`) or, when
    the step runs on its own, its section of the project's config.yaml with the
    ${...} references resolved. Empty when the step has no section.
    """
    if config_path:
        return OmegaConf.load(config_path)

    project = OmegaConf.load(find_project_config())
    section = project.get(step)
    if section is None:
        return OmegaConf.create({})
    return OmegaConf.create(OmegaConf.to_container(section, resolve=True))
