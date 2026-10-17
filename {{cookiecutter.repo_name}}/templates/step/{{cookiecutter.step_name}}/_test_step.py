"""
Tests for a pipeline step (STEP, in src/steps/<STEP>/).

run_step() runs the step like main.py does: its config section comes from a
file, the store has the project's locations in a temporary folder, and MLflow
tracks to a temporary SQLite file.
"""

import importlib.util
import sys
from pathlib import Path

import mlflow
import pytest
import yaml

from core.step import PIPELINE_RUN_ENV
from core.store import STORE_CONFIG_ENV, Store
from utils.config import load_project_config

STEP = "{{ cookiecutter.step_name }}"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
STEP_FILE = PROJECT_ROOT / "src" / "steps" / STEP / "{{ cookiecutter.script_name }}"


def load_step():
    name = f"steps_{STEP}"
    spec = importlib.util.spec_from_file_location(name, STEP_FILE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # Step.step_name() finds the step's folder through it
    spec.loader.exec_module(module)
    return module.{{ cookiecutter.__class_name }}


@pytest.fixture
def store(tmp_path, monkeypatch):
    """The project's store locations, all inside tmp_path; S3 sync off."""
    names = load_project_config(PROJECT_ROOT / "config.yaml").store.locations
    store = Store(
        local_root=tmp_path / "data",
        locations={name: dict(path=name) for name in names},
    )
    monkeypatch.setenv(STORE_CONFIG_ENV, store.dump(tmp_path / "store.yaml"))
    monkeypatch.delenv(PIPELINE_RUN_ENV, raising=False)
    previous = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path}/mlflow.db")
    yield store
    mlflow.set_tracking_uri(previous)


def run_step(tmp_path, config=None, **parameters):
    """Run the step with `config` as its section and `parameters` as arguments."""
    config_path = tmp_path / "step_config.yaml"
    config_path.write_text(yaml.safe_dump(config or {}))
    argv = ["--config_path", str(config_path)]
    for name, value in parameters.items():
        argv += [f"--{name}", str(value)]
    load_step().main(argv)


def test_{{ cookiecutter.step_name }}(tmp_path, store):
    pytest.skip("Implement run() in the step, then write this test")
    # For example:
    #
    # import pandas as pd
    #
    # store.save_data("raw", "in.csv", pd.DataFrame(dict(price=[5.0, 20.0])))
    # run_step(
    #     tmp_path,
    #     config=dict(min_price=10),
    #     input_artifact="in.csv",
    #     output_artifact="out.parquet",
    # )
    # out = store.load_data("processed", "out.parquet")
    # assert out["price"].tolist() == [20.0]
