# Main commands. Everything else lives in makefiles/, one file per area, and
# runs the same way (`make <target>`); `make help` lists every target.
#
#   makefiles/common.mk   environment (.env, ENV=dev|beta|prod) and shared variables
#   makefiles/dev.mk      dependencies, notebooks, git hooks
#   makefiles/mlflow.mk   the MLflow tracking server
#   makefiles/infra.mk    docker-compose services, AWS login
#   makefiles/docker.mk   the project's images
#   makefiles/clean.mk    cleanup

include makefiles/common.mk

.DEFAULT_GOAL := default

.PHONY: default help setup venv run pipeline step serve test lint format

default: setup run ##@Main Set up the project and start PostgreSQL and the MLflow server

help: ##@Main Show every target, grouped
	@awk 'BEGIN {FS = ":.*##@"} /^[a-zA-Z_-]+:.*##@/ {split($$2, parts, " "); group = parts[1]; sub(/^[^ ]+ */, "", $$2); if (group != last) {printf "\n%s\n", group; last = group}; printf "  %-18s %s\n", $$1, $$2}' $(filter-out $(ENV_FILE),$(MAKEFILE_LIST))

setup:${MLFLOW_ARTIFACT_STORE} ${POSTGRES_VOLUME} venv  ##@Main Create .venv and the MLflow stores

# Create .venv with the project (the packages in src/), every extra and every group
venv: ##@Main Create .venv and install the locked dependencies (uv sync)
	$(UV_SYNC)

run: docker-compose ##@Main Start PostgreSQL and the MLflow server in Docker
	@echo "MLflow UI: $(MLFLOW_TRACKING_URI)"

# make pipeline STEPS=basic_cleaning ARGS="store.sync_s3=true"
pipeline: ##@Main Run the pipeline (STEPS=a,b for a subset, ARGS for config overrides)
	$(PYTHON) main.py "main.steps='$(or $(STEPS),all)'" $(ARGS)

# make step ARGS="--no-input step_name=basic_cleaning" skips the prompts
step: ##@Main Create a new MLflow step in src/steps/ from the step template
	$(CC) ${STEP_PATH} -o ./src/steps python_version=$(PYTHON_VERSION) $(ARGS)

serve: ##@Main Run the API locally with auto-reload (docs at /docs)
	$(UV_RUN) uvicorn serving.app:app --reload --port $(or $(SERVING_PORT),8000)

test: ##@Main Run the tests
	$(PYTEST) tests

lint: ##@Main Lint the code with ruff and check the package layers
	$(RUFF) check .
	$(RUFF) format --check .
	$(UV_RUN) lint-imports

format: ##@Main Fix lint issues and format the code with ruff
	$(RUFF) check --fix .
	$(RUFF) format .

include makefiles/dev.mk makefiles/mlflow.mk makefiles/infra.mk makefiles/docker.mk makefiles/clean.mk
