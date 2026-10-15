# Environment: dev (default) loads .env, beta loads .env.beta, prod loads .env.prod
ENV ?= dev

# Based on the env value, set the appropriate .env file
ifeq ($(ENV),prod)
ENV_FILE := .env.prod
else ifeq ($(ENV),beta)
ENV_FILE := .env.beta
else ifeq ($(ENV),dev)
ENV_FILE := .env
else
$(error Unknown env value $(ENV). Please set env to dev, beta, or prod.)
endif

# Output the env value and which environment file is being used
$(info Using environment: $(ENV))
$(info Loading configuration from file: $(ENV_FILE))

# Include the environment file if it exists (.env is created from example.env)
-include $(ENV_FILE)

export

.DEFAULT_GOAL := default

SHELL := /bin/bash
# Absolute project root, read by config.yaml (${oc.env:PROJECT_ROOT})
PROJECT_ROOT := $(CURDIR)
USER_NAME := $(shell whoami)
# Single source of the Python version: uv reads it too
PYTHON_VERSION := $(shell cat .python-version)

CURRENT_DIRECTORY:=$(CURDIR)
INSTALL_DIRECTORY:=$(CURRENT_DIRECTORY)/.venv

variables := PROJECT_ROOT USER_NAME PYTHON_VERSION CURRENT_DIRECTORY INSTALL_DIRECTORY

#STEP_REPO:=git@github.com:steelcolosus/mlflow-step-template.git
STEP_PATH:=$(CURRENT_DIRECTORY)/templates/step

# Colors
RESET := $(shell tput sgr0 2>/dev/null)
RED := $(shell tput setaf 1 2>/dev/null)
GREEN := $(shell tput setaf 2 2>/dev/null)
WHITE  := $(shell tput -Txterm setaf 7 2>/dev/null)
YELLOW := $(shell tput -Txterm setaf 3 2>/dev/null)

# Commands: `uv run` keeps .venv in sync with uv.lock before running anything
UV := uv
UV_RUN := $(UV) run
PYTHON := $(UV_RUN) python
MLFLOW := $(UV_RUN) mlflow
PYTEST := $(UV_RUN) pytest
RUFF := $(UV_RUN) ruff
CC := $(UV_RUN) cookiecutter

DOWN_OPTS = --remove-orphans

.PHONY: default help setup run run-all venv docker-compose mlflow-server mlflow-kill \
	jupyter-notebook pipeline test lint format outdated upgrade hooks step login \
	purge clean clean-all clean-stores clean-python down prune

default: setup docker-compose run ##@Development Setup and run the mlflow server

help: ##@Other Show this help
	@awk 'BEGIN {FS = ":.*##@"} /^[a-zA-Z_-]+:.*##@/ {split($$2, parts, " "); group = parts[1]; sub(/^[^ ]+ */, "", $$2); printf "  %-18s %-13s %s\n", $$1, "[" group "]", $$2}' Makefile

# Create .env from example.env the first time
.env:
	cp example.env .env

setup:${MLFLOW_ARTIFACT_STORE} ${POSTGRES_VOLUME} venv  ##@Development setup environment and stores

# run mlflow-server
run: ##@Development Run mlflow-server
	$(MAKE) mlflow-server
# run all
run-all: ##@Development Run mlflow-server and jupyter-notebook targets in parallel
	$(MAKE) -j 2 mlflow-server jupyter-notebook

# Create .venv with the project (the packages in src/) and every dependency group
venv: ##@Development Create .venv and install the locked dependencies (uv sync)
	$(UV) sync

outdated: ##@Development List direct dependencies with a newer version available
	$(UV) tree --outdated --depth 1

upgrade: ##@Development Upgrade every dependency to its latest version in uv.lock
	$(UV) lock --upgrade
	$(UV) sync

# run docker compose
docker-compose: ##@Development Run docker compose
	docker compose up -d --wait

# run mlflow server
mlflow-server: ##@Development Run mlflow server
	$(MLFLOW) server \
		--backend-store-uri postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${MLFLOW_BACKEND_STORE}:${POSTGRES_PORT}/${POSTGRES_DB} \
		--artifacts-destination ${MLFLOW_ARTIFACT_STORE} \
		--host ${MLFLOW_TRACKING_SERVER_HOST} \
		--port ${MLFLOW_TRACKING_SERVER_PORT}

mlflow-kill: ##@Development Kill mlflow server
	-@lsof -t -i:${MLFLOW_TRACKING_SERVER_PORT} | xargs kill -9 2>/dev/null || true

#run jupyter notebook
jupyter-notebook: ##@Development Run jupyter notebook
	$(UV_RUN) jupyter-lab --ServerApp.iopub_msg_rate_limit=100000000

# make pipeline STEPS=basic_cleaning ARGS="store.sync_s3=true"
pipeline: ##@Pipeline Run the pipeline (STEPS=a,b for a subset, ARGS for config overrides)
	$(PYTHON) main.py "main.steps='$(or $(STEPS),all)'" $(ARGS)

test: ##@Development Run the tests
	$(PYTEST) tests

lint: ##@Development Lint the code with ruff and check the package layers
	$(RUFF) check .
	$(RUFF) format --check .
	$(UV_RUN) lint-imports

format: ##@Development Fix lint issues and format the code with ruff
	$(RUFF) check --fix .
	$(RUFF) format .

hooks: ##@Development Install the pre-commit hooks (needs a git repository)
	$(UV_RUN) pre-commit install


purge: clean-all
clean: down ##@Cleanup Stop the project containers
clean-all: down clean-stores clean-python mlflow-kill ##@Cleanup Remove containers, stores and python caches
clean-stores:
	@test -n "${MLFLOW_ARTIFACT_STORE}" -a -n "${POSTGRES_VOLUME}" || \
		(echo "MLFLOW_ARTIFACT_STORE and POSTGRES_VOLUME must be set" && exit 1)
	sudo rm -rf ./${MLFLOW_ARTIFACT_STORE} ./${POSTGRES_VOLUME}
clean-python:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	find . -name '.ipynb_checkpoints' -exec rm -fr {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .eggs/
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf .mlflow-envs
	find . -name '.eggs' -type d -exec rm -rf {} +
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.egg' -exec rm -f {} +
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

down: ##@Development Stop and remove containers, networks, images, and volumes
	docker compose down ${DOWN_OPTS}
# Removes unused docker resources of the whole machine, not only this project
prune: ##@Cleanup Prune ALL unused docker resources on this machine
	docker system prune -f


${MLFLOW_ARTIFACT_STORE}:
	mkdir -p ${MLFLOW_ARTIFACT_STORE}

${POSTGRES_VOLUME}:
	mkdir -p ${POSTGRES_VOLUME}


# make step ARGS="--no-input step_name=basic_cleaning" skips the prompts
step: ##@Development Create a new MLflow step in src/steps/ from the step template
	$(CC) ${STEP_PATH} -o ./src/steps python_version=$(PYTHON_VERSION) $(ARGS)

login: ##@Development Login to AWS SSO
	aws sso login --profile ${AWS_PROFILE}
