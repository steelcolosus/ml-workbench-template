# Cookiecutter template for ML Workbench

Generates an ML project with:

-   an MLflow tracking server on PostgreSQL (Docker Compose), or local tracking in SQLite;
-   a Hydra-configured pipeline whose steps are MLflow projects, each a subclass of `core.step.Step`;
-   a local-first data store with optional S3 sync (`core.store.Store`);
-   a FastAPI app that serves the project's models (`src/serving`);
-   pipeline and serving Docker images, one Dockerfile each, built with `docker buildx bake`, each with only its dependencies;
-   [uv](https://docs.astral.sh/uv/) for dependencies, ruff, pre-commit, import-linter and pytest.

## Usage

```shell
uvx cookiecutter [path or URL of this repo] -o [destination directory]
```

| Prompt | Used for |
|---|---|
| `project_name` | The README title. |
| `repo_name` | Project folder, package and MLflow project name, experiment prefix (`<repo_name>_<experiment_name>`) and default S3 prefix (`ml/<repo_name>`). Derived from `project_name`. |
| `author_name` | `pyproject.toml` and the copyright line in `LICENSE`. |
| `experiment_name` | The MLflow experiment, with `repo_name` as prefix. |
| `description` | The README and `pyproject.toml`. |
| `open_source_license` | The `LICENSE` file (with the current year and `author_name`) and `license` in `pyproject.toml`. `No license file` creates neither. |
| `s3_bucket`, `aws_profile`, `aws_region` | `example.env` (`AWS_BUCKET`, `AWS_PROFILE`, `AWS_REGION`), read by the store when S3 sync is on. |
| `python_version` | `.python-version`, `requires-python` in `pyproject.toml` and the MLflow `python_env.yaml`. |

Then, inside the generated project:

```shell
make venv       # create .venv with uv
make test       # check the setup
make step       # create a pipeline step in src/steps/ (asks for its name and parameters)
make pipeline   # run the steps listed in main.py
make serve      # run the API (SERVING_MODEL_NAME=<model>)
make help       # every target
```

## Generated project

```
src/
  core/        Abstractions the rest builds on: Store, Step, CustomModel
  libs/        Building blocks a step chooses to use: MLflow tracking, StepRunner, EDA
  utils/       Generic helpers: config files, logging, file operations
  steps/       Pipeline steps, one MLflow project per folder
  serving/     Serving code (APIs, batch scoring)
templates/
  step/        Cookiecutter template used by `make step`
tests/
docs/ARCHITECTURE.md
makefiles/     Targets by area; the Makefile keeps the main commands
docker/        One Dockerfile per image (pipeline, serving), a shared base and docker-bake.hcl
main.py  run.py  MLProject  config.yaml  pyproject.toml  Makefile  docker-compose.yml
```

The generated project's `docs/ARCHITECTURE.md` explains the architecture: how a pipeline run flows through the code, every package and helper, the libraries, and recipes for common tasks. Its README covers the commands. `templates/step/README.md` covers the step template: its prompts, the generated `Step` subclass and the hooks that validate the input and print what to add to `main.py` and `config.yaml`.

Projects generated before a template change keep their own copy of `templates/step`; copy the folder over to update it.
