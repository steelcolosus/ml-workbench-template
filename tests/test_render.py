"""Fast checks on the generated files: no project environment needed."""

import py_compile
import tomllib

import pytest
import yaml
from cookiecutter.exceptions import FailedHookException
from cookiecutter.main import cookiecutter

# Rendered with the generated project's own cookiecutter (`make step`), so they
# keep their Jinja markers
INNER_TEMPLATE = "templates/step"


def text_files(project):
    for path in sorted(project.rglob("*")):
        relative = path.relative_to(project).as_posix()
        if path.is_file() and not relative.startswith(INNER_TEMPLATE):
            yield relative, path.read_text()


def test_default_project_layout(render):
    project = render()

    for expected in [
        "Makefile",
        "makefiles/common.mk",
        "docker/docker-bake.hcl",
        "docker/base.Dockerfile",
        "docker/pipeline.Dockerfile",
        "docker/serving.Dockerfile",
        "docker/mlflow.Dockerfile",
        "src/core/store/store.py",
        "src/core/step.py",
        "src/serving/app.py",
        "templates/step/cookiecutter.json",
        "docs/ARCHITECTURE.md",
        "LICENSE",
        "config.yaml",
        ".python-version",
    ]:
        assert (project / expected).is_file(), expected


def test_no_template_markers_are_left(render):
    project = render(project_name="Price Model")

    leftovers = [
        name
        for name, text in text_files(project)
        if "{{" in text or "{%" in text
    ]
    assert leftovers == []
    assert project.name == "price_model"


def test_python_yaml_and_toml_files_parse(render):
    project = render()

    for name, text in text_files(project):
        path = project / name
        if name.endswith(".py"):
            py_compile.compile(str(path), doraise=True)
        elif name.endswith((".yaml", ".yml")):
            yaml.safe_load(text)
        elif name.endswith(".toml"):
            tomllib.loads(text)


@pytest.mark.parametrize(
    "license_, header",
    [("MIT", "MIT License"), ("BSD-3-Clause", "BSD 3-Clause License")],
)
def test_license_file_and_metadata(render, license_, header):
    project = render(open_source_license=license_, author_name="Ada Lovelace")

    text = (project / "LICENSE").read_text()
    assert text.startswith(header)
    assert "Ada Lovelace" in text
    pyproject = tomllib.loads((project / "pyproject.toml").read_text())
    assert pyproject["project"]["license"] == license_


def test_no_license(render):
    project = render(open_source_license="No license file")

    assert not (project / "LICENSE").exists()
    pyproject = tomllib.loads((project / "pyproject.toml").read_text())
    assert "license" not in pyproject["project"]


def test_python_version_reaches_every_place(render):
    project = render(python_version="3.12")

    assert (project / ".python-version").read_text().strip() == "3.12"
    pyproject = tomllib.loads((project / "pyproject.toml").read_text())
    assert pyproject["project"]["requires-python"] == ">=3.12"
    assert 'default = "3.12"' in (project / "docker/docker-bake.hcl").read_text()


def make_step(project, **context):
    return cookiecutter(
        str(project / INNER_TEMPLATE),
        no_input=True,
        extra_context=context,
        output_dir=project / "src" / "steps",
    )


def test_step_template(render):
    project = render()

    make_step(
        project,
        step_name="data_check",
        parameters="input_artifact, reference_artifact,config_path",
    )

    step = project / "src/steps/data_check"
    run_py = (step / "run.py").read_text()
    assert "class DataCheck(Step):" in run_py
    assert run_py.count('parser.add_argument("--') == 2  # config_path not repeated
    mlproject = yaml.safe_load((step / "MLproject").read_text())
    params = mlproject["entry_points"]["main"]["parameters"]
    assert list(params) == ["config_path", "input_artifact", "reference_artifact"]
    assert params["config_path"]["default"] == ""
    # The hook moves the step's test into the project's tests
    assert not (step / "_test_step.py").exists()
    test_file = project / "tests/steps/test_data_check.py"
    py_compile.compile(str(test_file), doraise=True)


def test_step_without_parameters(render):
    project = render()

    make_step(project, step_name="get_data", parameters="")

    run_py = (project / "src/steps/get_data/run.py").read_text()
    assert "add_arguments" not in run_py
    py_compile.compile(str(project / "src/steps/get_data/run.py"), doraise=True)


@pytest.mark.parametrize("name", ["data-check", "DataCheck", "1step"])
def test_invalid_step_names_are_rejected(render, name):
    project = render()

    with pytest.raises(FailedHookException):
        make_step(project, step_name=name)
    assert not (project / "src/steps" / name).exists()
