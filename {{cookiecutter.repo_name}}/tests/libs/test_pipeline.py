import json
import os
import sys

import mlflow
import pytest
from mlflow import MlflowClient
from omegaconf import OmegaConf

from core.step import PIPELINE_RUN_ENV
from core.store import STORE_CONFIG_ENV, Store
from libs.pipeline import StepRunner

MLPROJECT = """
name: echo
entry_points:
  main:
    parameters:
      config_path:
        type: string
        default: ""
      input_artifact:
        type: string
    command: python run.py --config_path {config_path} --input_artifact {input_artifact}
"""

# A step that saves what it received, to check it from the test
RUN_PY = """
import json

from omegaconf import OmegaConf

from core.step import Step


class Echo(Step):
    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--input_artifact", type=str, required=True)

    def run(self):
        received = dict(
            config=OmegaConf.to_container(self.config),
            input_artifact=self.args.input_artifact,
        )
        self.store.save_artifact(
            "raw", "echo.json", writer=lambda p: p.write_text(json.dumps(received))
        )


if __name__ == "__main__":
    Echo.main()
"""


@pytest.fixture
def pipeline(tmp_path, monkeypatch):
    step = tmp_path / "steps" / "echo"
    step.mkdir(parents=True)
    (step / "MLproject").write_text(MLPROJECT)
    (step / "run.py").write_text(RUN_PY)
    (tmp_path / "work").mkdir()

    # `mlflow run` starts `python` from PATH: use this interpreter. The runner
    # sets STORE_CONFIG and PIPELINE_RUN_ID; monkeypatch restores them.
    monkeypatch.setenv("PATH", os.path.dirname(sys.executable), prepend=os.pathsep)
    monkeypatch.setenv(STORE_CONFIG_ENV, "")
    monkeypatch.setenv(PIPELINE_RUN_ENV, "")

    previous = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path}/mlflow.db")
    config = OmegaConf.create(
        dict(
            base_name="listings.csv",
            echo=dict(input_artifact="${base_name}", nested=[dict(column="price")]),
        )
    )
    store = Store(local_root=tmp_path / "data", locations=dict(raw=None))
    yield tmp_path, config, store
    mlflow.set_tracking_uri(previous)


def make_runner(tmp_path, config, store, parent_run_id=None):
    return StepRunner(
        steps_path=tmp_path / "steps",
        config=config,
        store=store,
        work_dir=tmp_path / "work",
        env_manager="local",
        parent_run_id=parent_run_id,
    )


def test_a_step_gets_its_config_section_and_parameters(pipeline):
    tmp_path, config, store = pipeline

    with mlflow.start_run() as parent:
        runner = make_runner(tmp_path, config, store, parent.info.run_id)
        submitted = runner.run("echo", input_artifact=config.echo.input_artifact)

    received = json.loads(store.path("raw", "echo.json").read_text())
    assert received["input_artifact"] == "listings.csv"
    assert received["config"] == dict(
        input_artifact="listings.csv", nested=[dict(column="price")]
    )

    run = MlflowClient().get_run(submitted.run_id)
    assert run.info.run_name == "echo"
    assert run.data.params["input_artifact"] == "listings.csv"
    assert run.data.tags["mlflow.parentRunId"] == parent.info.run_id


def test_run_name_can_be_set(pipeline):
    tmp_path, config, store = pipeline

    submitted = make_runner(tmp_path, config, store).run(
        "echo", run_name="echo_v2", input_artifact="x.csv"
    )

    assert MlflowClient().get_run(submitted.run_id).info.run_name == "echo_v2"


def test_a_step_that_does_not_exist_is_skipped(pipeline):
    tmp_path, config, store = pipeline

    assert make_runner(tmp_path, config, store).run("missing") is None
