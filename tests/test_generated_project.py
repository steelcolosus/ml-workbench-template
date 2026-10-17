"""
Slow checks: generate a project and run its own make targets, as a user would.
Needs uv and Docker (make lint runs hadolint in Docker; the images need it too).
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from cookiecutter.main import cookiecutter

TEMPLATE = Path(__file__).resolve().parents[1]

pytestmark = pytest.mark.slow


def run(project, *args):
    env = {**os.environ, "MLFLOW_DISABLE_AGENT_HINT": "1"}
    # Variables of the surrounding shell must not leak into the project
    for var in ("VIRTUAL_ENV", "PROJECT_ROOT", "STORE_CONFIG", "MLFLOW_TRACKING_URI"):
        env.pop(var, None)
    result = subprocess.run(
        args, cwd=project, env=env, capture_output=True, text=True, timeout=1800
    )
    assert result.returncode == 0, f"{args} failed:\n{result.stdout}\n{result.stderr}"
    return result.stdout


@pytest.fixture(scope="module")
def project(tmp_path_factory):
    output = tmp_path_factory.mktemp("generated")
    project = cookiecutter(str(TEMPLATE), no_input=True, output_dir=output)
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    run(project, "make", "venv")
    return project


def test_lint_and_tests_pass(project):
    run(project, "make", "lint")
    assert " passed" in run(project, "make", "test")


def test_new_step_keeps_lint_and_tests_green(project):
    run(project, "make", "step", "ARGS=--no-input step_name=basic_cleaning")

    run(project, "make", "lint")
    output = run(project, "make", "test")
    assert "skipped" in output


@pytest.mark.skipif(shutil.which("docker") is None, reason="needs Docker")
def test_images_build(project):
    run(project, "make", "images")
