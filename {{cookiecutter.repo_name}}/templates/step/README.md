# Cookiecutter template for pipeline steps

`make step` uses this template to create a step in `src/steps/<step_name>`: an MLflow project whose `run.py` subclasses `core.step.Step`.

## Prompts

| Prompt | Used for |
|---|---|
| `step_name` | Folder name, config section name and class name (`data_check` → `DataCheck`). Must be snake_case. |
| `script_name` | The step's script (default `run.py`). |
| `short_description` | The class docstring. |
| `long_description` | The module docstring. |
| `parameters` | Comma-separated parameter names, e.g. `input_artifact,reference_artifact`. They become MLproject parameters and `add_arguments` in `run.py`. Leave it empty for a step without parameters. |
| `python_version` | The step's `python_env.yaml` (the Makefile passes the project's version). |

`config_path` is added to every step automatically (with an empty default, so `mlflow run` works without it): main.py passes the step's config section in that file, and without it the step reads its section of `config.yaml`. Don't list it in `parameters`.

A hook stops the generation when `step_name` or a parameter isn't a valid snake_case name, and another one prints the block to add to `main.py` and the section to add to `config.yaml` after the step is created.

Skip the prompts with `make step ARGS="--no-input step_name=data_check parameters=input_artifact,reference_artifact"`.

## Generated files

-   `MLproject`: the parameters, all `type: string`. Set their types and descriptions.
-   `run.py`: the `Step` subclass. Set the argument types and help in `add_arguments` and implement `run()`.
-   `tests/steps/test_<step_name>.py` (moved there by the hook): a `run_step()` helper that runs the step like main.py does (its config section from a file, the project's store locations in a temporary folder, MLflow in a temporary SQLite file) and a test that is skipped until you write it. If the file already exists it's kept.
-   `python_env.yaml` and `requirements.txt`: used when the pipeline runs with `launcher.env_manager=uv` or `virtualenv`. The step's `requirements.txt` installs the project itself (the packages in `src/` and the dependencies in `pyproject.toml`). Packages that only this step needs go below it; packages the whole project uses go in `pyproject.toml` (`uv add <package>`).
