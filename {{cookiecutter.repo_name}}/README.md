# {{cookiecutter.project_name}}

{{cookiecutter.description}}

This is a Makefile-based project designed to set up a development environment for running MLflow server and Jupyter Notebook in parallel. It uses [uv](https://docs.astral.sh/uv/) to create the virtual environment from `pyproject.toml` and `uv.lock`, sets up a Docker Compose environment, and manages storage for artifacts and PostgreSQL.

## Requirements

-   [uv](https://docs.astral.sh/uv/getting-started/installation/) (it installs Python {{cookiecutter.python_version}} from `.python-version` if needed)
-   Docker
-   Docker Compose

## Getting Started

1. Clone the repository.
2. Install uv (`curl -LsSf https://astral.sh/uv/install.sh | sh`) and make sure Docker and Docker Compose are installed.
3. Run `make venv` to create `.venv` with the project and every dependency group. The first run creates `uv.lock`: commit it.
4. Run `make test` to check the setup.
5. Run `make` to start PostgreSQL and the MLflow server. The first run creates `.env` from `example.env`.

There is no need to activate `.venv` or set `PYTHONPATH`: the targets run through `uv run`, and the packages in `src/` are installed, so `from core.store import Store` works from the project root, a notebook or a step. To work in a shell, run `source .venv/bin/activate` or prefix commands with `uv run`.

## Project layout

All code lives in `src/`. The entry points (`main.py`, `run.py`, `MLProject`, `config.yaml`) stay at the root.

```
src/
  core/        Abstractions the rest of the code builds on (the store, ...)
  libs/        Building blocks a step chooses to use: MLflow tracking, data transforms, EDA
  utils/       Small generic helpers: config files, logging, file operations
  steps/       Pipeline steps, one MLflow project per folder (`make step`)
  serving/     Serving code (APIs, batch scoring)
templates/
  step/        Cookiecutter template used by `make step`
tests/         Mirrors src/: tests/core, tests/libs, ...
```

Each package may only import the ones below it: `serving` → `libs` → `core` → `utils`. Steps can import all of them, and nothing imports a step. `make lint` checks these rules with [import-linter](https://import-linter.readthedocs.io/).

## Targets

Run `make help` for the full list.

-   `venv`: Create `.venv` and install the project with the locked dependencies (`uv sync`).
-   `outdated`: List the direct dependencies that have a newer version.
-   `upgrade`: Upgrade every dependency in `uv.lock` to its latest allowed version and sync `.venv`.
-   `docker-compose`: Start PostgreSQL with Docker Compose and wait until it is healthy.
-   `mlflow-server`: Run the MLflow server with a PostgreSQL backend and artifact store.
-   `jupyter-notebook`: Run Jupyter Lab in the virtual environment.
-   `setup`: Set up the environment and storage for MLflow and PostgreSQL.
-   `run`: Run the MLflow server.
-   `run-all`: Run the MLflow server and Jupyter Lab in parallel.
-   `pipeline`: Run the pipeline steps (`STEPS=a,b` for a subset, `ARGS="key=value"` for config overrides).
-   `step`: Create a new MLflow step in `src/steps/` from the step template.
-   `test`: Run the tests.
-   `lint`: Check the code with ruff (lint and format) and the package layers with import-linter.
-   `format`: Fix lint issues and format the code with ruff.
-   `hooks`: Install the pre-commit hooks (ruff on every commit).
-   `clean`: Stop the project containers.
-   `clean-all`: Remove containers, stores and Python caches.
-   `down`: Stop and remove containers, networks, images, and volumes.
-   `prune`: Prune **all** unused Docker resources on this machine (not only this project).

## Usage

Run the default target to set up the environment and run the MLflow server:

```shell
make
```

Every target uses `ENV=dev` (`.env`) by default. Use `ENV=beta` or `ENV=prod` to load `.env.beta` or `.env.prod`:

```shell
make pipeline ENV=prod
```

Run the whole pipeline, a subset of steps, or override any config value:

```shell
make pipeline
make pipeline STEPS=basic_cleaning,data_check
make pipeline ARGS="store.sync_s3=true launcher.local=true"
```

## Dependencies

Dependencies live in `pyproject.toml`, split by where they are installed, and their exact versions in `uv.lock`:

| Set | Kind | What | Installed in | Add with |
|---|---|---|---|---|
| base | `[project] dependencies` | What `src/core`, `src/libs` and `src/utils` import | everywhere | `uv add scipy` |
| `pipeline` | extra | main.py, run.py and the steps (Hydra, dask, ...) | pipeline image, step environments | `uv add --optional pipeline lightgbm` |
| `serving` | extra | The API in `src/serving` (FastAPI, uvicorn) | serving image | `uv add --optional serving orjson` |
| `test` | group | pytest, moto, httpx | test image | `uv add --group test pytest-cov` |
| `dev` | group | ruff, pre-commit, import-linter, cookiecutter | your machine | `uv add --group dev mypy` |
| `notebook` | group | Jupyter Lab and widgets | your machine | `uv add --group notebook plotly` |
| `eda` | group | ydata-profiling, seaborn, matplotlib | your machine | `uv add --group eda sweetviz` |
| `tracking-server` | group | psycopg2 for `make mlflow-server` | your machine | |

Extras are part of the package: an image or a step environment asks for them (`uv sync --extra serving`, `pip install -e ".[pipeline]"`). Groups are only for working on the project and never reach an image, except the test image.

Your `.venv` gets everything: `make venv` runs `uv sync --all-extras`, and the targets run through `uv run --all-extras`. `uv add` updates `pyproject.toml`, `uv.lock` and `.venv` at once. Run `make outdated` to see what can be upgraded and `make upgrade` to do it.

A package goes in base when every image needs it, in an extra when only that part of the project imports it, and in a group when nothing at runtime imports it.

## Pipeline steps

Each step is an MLflow project in `src/steps/<step>`:

1. Create it with `make step`. It asks for the step's name and parameters (`input_artifact,output_artifact` by default) and prints what to add to `main.py` and `config.yaml`; `make step ARGS="--no-input step_name=basic_cleaning"` skips the prompts. See `templates/step/README.md`.
2. Add its name to `_steps` in `main.py`, in execution order, and run it in its own block (the step's hook prints this block):

```python
        if "basic_cleaning" in active_steps:
            runner.run(
                "basic_cleaning",
                input_artifact=config["basic_cleaning"]["input_artifact"],
                output_artifact=config["basic_cleaning"]["output_artifact"],
            )
```

3. Add its section to `config.yaml`:

```yaml
basic_cleaning:
    input_artifact: ${get_data.output_artifact}   # chained to the previous step
    output_artifact: clean.parquet
    min_price: 10
    max_price: 350

preprocessing:
    input_artifact: ${basic_cleaning.output_artifact}
    output_artifact: features.parquet
    aggregations:                                  # nested values work too
        - column: price
          name: avg_price
          aggfunc: mean
```

`runner.run(step, run_name=None, **parameters)` (`libs.pipeline.StepRunner`):

-   writes the step's whole section to a YAML file and passes its path as `config_path`; the step reads it as `self.config`;
-   passes the keyword arguments as MLflow parameters, so they show up in the MLflow UI;
-   names the MLflow run after the step (or `run_name`) and nests it under the pipeline run;
-   gives the step the resolved store config, `ARGS` overrides such as `store.sync_s3=true` included;
-   skips a step whose folder doesn't exist yet, with a warning.

Each block can do whatever that step needs: pass other parameters, a different `run_name`, or run only under some condition.

### Writing a step

A step's `run.py` subclasses `core.step.Step`:

```python
from core.step import Step


class BasicCleaning(Step):
    """Drop rows outside the price range"""

    @classmethod
    def add_arguments(cls, parser):
        # The same parameters as in the step's MLproject
        parser.add_argument("--input_artifact", type=str, required=True)
        parser.add_argument("--output_artifact", type=str, required=True)

    def run(self):
        df = self.store.load_data("raw", self.args.input_artifact)
        df = df[df["price"].between(self.config.min_price, self.config.max_price)]
        self.store.save_data("processed", self.args.output_artifact, df)
        self.logger.info(f"Kept {len(df)} rows")


if __name__ == "__main__":
    BasicCleaning.main()
```

`main()` gives `run()` everything it needs:

-   `self.args`: the parameters declared in `add_arguments`, plus `config_path`, which every step gets.
-   `self.config`: the step's config section, nested values included. It comes from the file main.py passes as `config_path` or, when the step runs on its own, from its section of `config.yaml` with `${...}` resolved.
-   `self.store` and `self.logger`.
-   `run()` runs inside the step's MLflow run, which records the config it ran with (`step_config.yaml`). An exception fails the run and the pipeline.

The step's name is its folder name, which is also its config section; set `name = "..."` on the class to change it.

### Step environments

`launcher.env_manager` (used when `launcher.local` is false) decides where the steps run:

-   `local` (default): in `.venv`, like `launcher.local=true`.
-   `uv`: MLflow creates an environment per step with uv, from the step's `requirements.txt`.
-   `virtualenv`: the same with pip, but it needs [pyenv](https://github.com/pyenv/pyenv) to install Python.

A step's `requirements.txt` installs the project with `-e ${PROJECT_ROOT}` (the packages in `src/` and the `[project]` dependencies); add packages only that step needs below it. `main.py` sets `PROJECT_ROOT`, keeps the step environments in `.mlflow-envs/<hash of uv.lock>` (they are rebuilt when `uv.lock` changes) and applies the versions in `uv.lock` as constraints, so the steps run with the same versions as `.venv`. `make clean-python` deletes them.

A step can also run on its own:

```shell
uv run mlflow run src/steps/basic_cleaning --env-manager local -P input_artifact=listings.csv -P output_artifact=clean.parquet
```

## Store

`core.store.Store` reads and saves files by **location** and **name**. Locations are folders configured once in `config.yaml`, so steps never build paths by hand. Files are always read and written locally. When `store.sync_s3` is true, a file that is missing locally is downloaded from S3 on load, and every save is uploaded afterwards.

### Configuration

```yaml
store:
    local_root: ${root}/data            # base folder for relative location paths
    sync_s3: false                      # the only switch for S3
    bucket: ${oc.env:AWS_BUCKET,null}   # default bucket
    prefix: ml/{{cookiecutter.repo_name}}  # default prefix
    locations:
        raw:
            path: raw                   # data/raw
        processed:
            path: processed             # data/processed
        models:
            path: ${root}/models        # absolute paths can live outside local_root
        analytics:
            path: analytics
            bucket: analytics-bucket    # optional: own bucket
            prefix: team-x/{{cookiecutter.repo_name}}  # optional: own prefix
```

Where an item is stored in S3:

| Call | Local | S3 |
|---|---|---|
| `("raw", "listings.csv")` | `data/raw/listings.csv` | `s3://<bucket>/ml/{{cookiecutter.repo_name}}/raw/listings.csv` |
| `("models", "price_model")` | `models/price_model/` | `s3://<bucket>/ml/{{cookiecutter.repo_name}}/models/price_model/` |
| `("analytics", "eda/report.html")` | `data/analytics/eda/report.html` | `s3://analytics-bucket/team-x/{{cookiecutter.repo_name}}/eda/report.html` |

A location uses its own `bucket` and `prefix` when set, otherwise `store.bucket` and `store.prefix/<location name>`.

With `sync_s3: false` nothing contacts S3: no bucket, credentials or network are needed.

### Methods

```python
from core.store import Store

store = Store.from_env()   # inside a step or notebook; main.py passes its resolved config

# Data: pandas (default) or dask, format from the extension (.csv, .parquet, .json, .jsonl)
df = store.load_data(
    "raw", args.input_artifact,
    columns=["id", "price", "last_review"],
    dtypes={"price": "float64"},
    parse_dates=["last_review"],
    sep=",",                       # anything else goes to the reader
)
events = store.load_data("raw", "events/*.parquet", engine="dask")
store.save_data("processed", args.output_artifact, df)          # engine detected from the object

# Artifacts: anything written or read by another tool
store.save_artifact("analytics", "eda/report.html",
                    writer=lambda path: ProfileReport(df).to_file(path))
store.save_artifact("models", "price_model",
                    writer=lambda path: mlflow.pyfunc.save_model(path, python_model=model))
model = store.load_artifact("models", "price_model", reader=mlflow.pyfunc.load_model)

# Just the local path, no download or upload
path = store.path("analytics", "plots/heatmap.png")
```

| Method | What it does |
|---|---|
| `load_data(location, name, engine, columns, dtypes, parse_dates, format, **read_options)` | Reads a DataFrame. Downloads it first if it is missing locally and sync is on. |
| `save_data(location, name, df, format, sync=True, **write_options)` | Writes a DataFrame, then uploads it if sync is on. |
| `load_artifact(location, name, reader=None)` | Makes sure the file or folder is local (downloading it if needed) and returns `reader(path)`, or the path. |
| `save_artifact(location, name, writer, sync=True)` | Calls `writer(path)` to create a file or folder, moves it into place, then uploads it if sync is on. |
| `path(location, name="")` | Returns the local path. Never downloads or uploads: use `save_artifact` when the result must reach S3. |
| `uri(location, name="")` | Returns the S3 URI (for logs and debugging). |

Details:

-   `sync=False` on a save keeps that one save local even when `store.sync_s3` is true.
-   Saves are atomic: the writer works on a temporary path that only replaces the existing file or folder once it is complete.
-   Folders (dask datasets, MLflow models) are mirrored to S3: remote files that no longer exist locally are deleted.
-   A local file always wins over S3; delete it to download it again.
-   Locations and buckets are checked when the store is created: an unknown location or a missing bucket with `sync_s3: true` fails right away.

### Extending the store

The store works through two interfaces in `src/core/store/`, with S3 and pandas/dask as the built-in implementations:

| Interface | Built in | To add one |
|---|---|---|
| `RemoteStorage` (`remote.py`) | `S3Storage` (also S3-compatible endpoints) | Implement `exists`, `list_keys`, `get_file`, `put_file` and `delete_keys`; folder downloads, mirroring and atomic writes come from the base class. Pass it as `Store(..., remote=GCSStorage())`. |
| `DataEngine` (`engines.py`) | `PandasEngine`, `DaskEngine` | Implement `owns`, `read` and `write`. Pass it as `Store(..., engines={"polars": PolarsEngine()})`, then `load_data(..., engine="polars")`. |

`Store.from_config` and `Store.from_env` accept the same `remote=` and `engines=` arguments.

### Local S3

To try `sync_s3` without AWS, start the in-memory S3 server and point the store at it:

```shell
docker compose --profile s3-local up -d
```

Then uncomment `AWS_ENDPOINT_URL`, `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` in `.env` and create the bucket once (see `example.env`).

## Custom models

Custom MLflow models subclass `core.model.CustomModel` (an `mlflow.pyfunc.PythonModel`) and implement `predict`:

```python
from core.model import CustomModel


class PriceModel(CustomModel):
    def predict(self, context, model_input, params=None):
        ...


model = PriceModel()
model.save(store, "price_model", sample=X.head())    # logs it to the run and saves it to the `models` location
loaded = CustomModel.load(store, "price_model")       # downloads it first when missing and sync is on
```

`save` infers the signature by predicting on `sample`. `log_model=False` skips logging to MLflow, `sync=False` keeps the saved copy local and `location=` picks another store location. To register a logged model, use `libs.tracking.register_model`.

## Environment Variables

The project includes a .env file containing environment variables for MLflow server, PostgreSQL, and storage directories. Modify the values as needed for your environment.

### Configuration

To configure the project, modify the values in the .env file according to your requirements. Here are the main environment variables used in the Makefile:

-   `POSTGRES_USER`: PostgreSQL user.
-   `POSTGRES_PASSWORD`: PostgreSQL password.
-   `POSTGRES_DB`: PostgreSQL database name.
-   `POSTGRES_PORT`: PostgreSQL port on the host.
-   `MLFLOW_BACKEND_STORE`: Hostname for the MLflow backend store (PostgreSQL).
-   `MLFLOW_ARTIFACT_STORE`: Directory for storing MLflow artifacts.
-   `MLFLOW_TRACKING_SERVER_HOST`: Host for the MLflow tracking server.
-   `MLFLOW_TRACKING_SERVER_PORT`: Port for the MLflow tracking server.
-   `POSTGRES_VOLUME`: Directory for storing PostgreSQL data.
-   `AWS_PROFILE`, `AWS_BUCKET`, `AWS_REGION`: AWS settings used by the store.
-   `AWS_ENDPOINT_URL`: Optional S3-compatible endpoint (e.g. the local S3 server).

### Customization

You can easily customize this project to suit your needs by adding or modifying targets in the Makefile. Here are some ideas for customization:

-   Add targets for specific data processing or training tasks.
-   Integrate additional tools, like TensorBoard or additional Jupyter Notebook extensions.
-   Add targets for deployment or packaging.

## Contributing

If you'd like to contribute to the project, feel free to submit a pull request or open an issue. We appreciate any help and feedback.
