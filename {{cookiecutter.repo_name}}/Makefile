include .env

export


PYTHONPATH= .
SHELL := /bin/bash
USER_NAME := $(shell whoami)
PYTHON_VERSION=$(shell {{cookiecutter.python_interpreter}} -c 'import sys; print("{0}.{1}".format(sys.version_info[0], sys.version_info[1]))')
PYTHON_PATH=$(shell which {{cookiecutter.python_interpreter}})

CURRENT_DIRECTORY:=$(shell pwd)
INSTALL_DIRECTORY:=$(CURRENT_DIRECTORY)/.venv
EXEC_PATH:=$(INSTALL_DIRECTORY)/bin/

variables := PYTHONPATH USER_NAME PYTHON_VERSION PYTHON_PATH CURRENT_DIRECTORY INSTALL_DIRECTORY EXEC_PATH

STEP_REPO:=git@github.com:steelcolosus/mlflow-step-template.git

# Colors
RESET := $(shell tput sgr0)
RED := $(shell tput setaf 1)
GREEN := $(shell tput setaf 2)
WHITE  := $(shell tput -Txterm setaf 7)
YELLOW := $(shell tput -Txterm setaf 3)

# Commands
PIP := $(EXEC_PATH)pip
PYTHON := $(EXEC_PATH)python3
MLFLOW := $(EXEC_PATH)mlflow
PYTEST := $(PYTHON) -m pytest
VENV:= python3 -m venv

PRUNE_OPTS = -f
DOWN_OPTS = --remove-orphans


default: clean setup docker-compose run##@Development Run all



setup:${MLFLOW_ARTIFACT_STORE} ${POSTGRES_VOLUME} venv  ##@Development setup environment and stores

# run mlflow-server
run: ##@Development Run mlflow-server
	$(MAKE) mlflow-server
# run all
run-all: ##@Development Run mlflow-server and jupyter-notebook targets in parallel
	$(MAKE) -j 2 mlflow-server jupyter-notebook

# Create virtual environment
venv: ##@Development Create virtual environment
	$(VENV) $(INSTALL_DIRECTORY)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

# run docker compose
docker-compose: ##@Development Run docker compose
	docker compose up -d

# run mlflow server
mlflow-server: ##@Development Run mlflow server
	source $(EXEC_PATH)activate && \
	PYTHONPATH=. $(MLFLOW) server \
		--backend-store-uri postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${MLFLOW_BACKEND_STORE}:${POSTGRES_PORT}/${POSTGRES_DATABASE} \
		--default-artifact-root ${MLFLOW_ARTIFACT_STORE} \
		--host ${MLFLOW_TRACKING_SERVER_HOST} \
		--port ${MLFLOW_TRACKING_SERVER_PORT}

mlflow-kill: ##@Development Kill mlflow server
	kill -9 $(shell lsof -t -i:${MLFLOW_TRACKING_SERVER_PORT})

#run jupyter notebook
jupyter-notebook: ##@Development Run jupyter notebook
	$(EXEC_PATH)jupyter-lab --NotebookApp.iopub_msg_rate_limit=100000000


purge: clean-all
clean: down prune
clean-all:  down prune clean-stores clean-python mlflow-kill
clean-stores:
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
	find . -name '.eggs' -type d -exec rm -rf {} +
	find . -name '*.egg-info' -exec rm -rf {} +
	find . -name '*.egg' -exec rm -f {} +
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

down: ##@Development Stop and remove containers, networks, images, and volumes
	docker compose down ${DOWN_OPTS}
prune:
	docker system prune ${PRUNE_OPTS}


${MLFLOW_ARTIFACT_STORE}:
	mkdir -p ${MLFLOW_ARTIFACT_STORE}

${POSTGRES_VOLUME}:
	mkdir -p ${POSTGRES_VOLUME}


step:
	$(CC) ${STEP_REPO} -o ./src