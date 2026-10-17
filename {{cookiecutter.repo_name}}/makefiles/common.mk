# Shared by every makefile: the environment file, project variables and the
# commands the targets use. Included first by the root Makefile.

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

SHELL := /bin/bash
# Absolute project root, read by config.yaml (${oc.env:PROJECT_ROOT})
PROJECT_ROOT := $(CURDIR)
USER_NAME := $(shell whoami)
# Single source of the Python version: uv reads it too
PYTHON_VERSION := $(shell cat .python-version)
# The images build with the same uv that wrote uv.lock
UV_VERSION := $(shell uv --version 2>/dev/null | cut -d' ' -f2)
IMAGE_NAME := {{cookiecutter.repo_name}}
# Image labels (docker/docker-bake.hcl)
PROJECT_VERSION := $(shell sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml | head -1)
GIT_SHA := $(shell git rev-parse --short HEAD 2>/dev/null)
SOURCE_URL := $(shell git remote get-url origin 2>/dev/null)

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

# Commands: `uv run` keeps .venv in sync with uv.lock before running anything.
# Locally every extra is installed (pipeline, serving); images install only theirs.
UV := uv
UV_SYNC := $(UV) sync --all-extras
UV_RUN := $(UV) run --all-extras
PYTHON := $(UV_RUN) python
MLFLOW := $(UV_RUN) mlflow
PYTEST := $(UV_RUN) pytest
RUFF := $(UV_RUN) ruff
CC := $(UV_RUN) cookiecutter

# Create .env from example.env the first time
.env:
	cp example.env .env
