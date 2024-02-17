import os
from datetime import date, datetime

import mlflow
import pandas as pd
import yaml
from omegaconf import OmegaConf


def load_config(str_conf: str) -> dict:
    """
    Load a config object from a string
    """
    with open(str_conf) as fp:
        model_config = yaml.safe_load(fp)

    return model_config


def serialize_config(config: dict, output_path: str):
    """
    Serialize a config object to a file
    """
    config_path = os.path.abspath(output_path)
    with open(config_path, 'w+') as fp:
        fp.write(OmegaConf.to_yaml(config))

    return config_path
