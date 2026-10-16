# Removing containers, stores, caches and Docker resources

.PHONY: purge clean clean-all clean-stores clean-python prune

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

# Removes unused docker resources of the whole machine, not only this project
prune: ##@Cleanup Prune ALL unused docker resources on this machine
	docker system prune -f
