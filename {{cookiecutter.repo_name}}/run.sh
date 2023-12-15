#!/bin/bash
export $(grep -v '^#' .env | xargs)
mlflow run . --experiment-name {{cookiecutter.experiment_name}}