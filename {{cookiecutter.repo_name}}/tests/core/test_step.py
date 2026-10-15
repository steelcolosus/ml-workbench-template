import mlflow
import pytest
from mlflow import MlflowClient

from core.step import PIPELINE_RUN_ENV, Step
from core.store import STORE_CONFIG_ENV

PROJECT_CONFIG = """
root: ${oc.env:PROJECT_ROOT,.}
store:
  local_root: ${root}/data
  locations:
    raw:
      path: raw
my_step:
  threshold: 0.5
  output_artifact: out.csv
  same_output: ${my_step.output_artifact}
  nested:
    - column: price
      aggfunc: mean
"""


class Recorder(Step):
    """Keeps the last instance that ran, to inspect it in the tests."""

    name = "my_step"
    last = None

    @classmethod
    def add_arguments(cls, parser):
        parser.add_argument("--output_artifact", type=str, required=True)

    def run(self):
        type(self).last = self
        self.run_id = mlflow.active_run().info.run_id


class Failing(Step):
    name = "my_step"

    def run(self):
        raise RuntimeError("boom")


class Unnamed(Step):
    def run(self):
        pass


@pytest.fixture
def project(tmp_path, monkeypatch):
    (tmp_path / "config.yaml").write_text(PROJECT_CONFIG)
    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
    for var in (STORE_CONFIG_ENV, PIPELINE_RUN_ENV, "MLFLOW_RUN_ID"):
        monkeypatch.delenv(var, raising=False)

    previous = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path}/mlflow.db")
    yield tmp_path
    mlflow.set_tracking_uri(previous)


def test_without_config_path_it_reads_its_project_section(project):
    Recorder.main(["--output_artifact", "x.csv"])

    step = Recorder.last
    assert step.name == "my_step"
    assert step.args.output_artifact == "x.csv"
    assert step.config.threshold == 0.5
    assert step.config.same_output == "out.csv"
    assert step.config.nested[0].aggfunc == "mean"
    assert step.store.path("raw") == (project / "data" / "raw").resolve()


def test_an_empty_config_path_also_reads_the_project_section(project):
    Recorder.main(["--config_path", "", "--output_artifact", "x.csv"])

    assert Recorder.last.config.threshold == 0.5


def test_config_path_wins_over_the_project_config(project):
    config_file = project / "step.yaml"
    config_file.write_text("threshold: 0.9\n")

    Recorder.main(["--config_path", str(config_file), "--output_artifact", "x.csv"])

    assert Recorder.last.config.threshold == 0.9


def test_runs_inside_an_mlflow_run_with_its_config_and_parent(project, monkeypatch):
    monkeypatch.setenv(PIPELINE_RUN_ENV, "parent-run-id")

    Recorder.main(["--output_artifact", "x.csv"])

    client = MlflowClient()
    run = client.get_run(Recorder.last.run_id)
    assert run.info.status == "FINISHED"
    assert run.data.tags["mlflow.parentRunId"] == "parent-run-id"
    artifacts = [a.path for a in client.list_artifacts(run.info.run_id)]
    assert "step_config.yaml" in artifacts


def test_a_failing_step_raises_and_fails_its_run(project):
    with pytest.raises(RuntimeError, match="boom"):
        Failing.main([])

    runs = mlflow.search_runs(search_all_experiments=True, output_format="list")
    assert [r.info.status for r in runs] == ["FAILED"]


def test_name_defaults_to_the_folder_of_the_step():
    assert Unnamed.step_name() == "core"
