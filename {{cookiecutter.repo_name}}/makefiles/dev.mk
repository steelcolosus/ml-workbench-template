# Development tools: dependencies, notebooks and git hooks

.PHONY: outdated upgrade jupyter-notebook run-all hooks

outdated: ##@Development List direct dependencies with a newer version available
	$(UV) tree --outdated --depth 1

upgrade: ##@Development Upgrade every dependency to its latest version in uv.lock
	$(UV) lock --upgrade
	$(UV_SYNC)

#run jupyter notebook
jupyter-notebook: ##@Development Run jupyter notebook
	$(UV_RUN) jupyter-lab --ServerApp.iopub_msg_rate_limit=100000000

# run all
run-all: ##@Development Run mlflow-server and jupyter-notebook targets in parallel
	$(MAKE) -j 2 mlflow-server jupyter-notebook

hooks: ##@Development Install the pre-commit hooks (needs a git repository)
	$(UV_RUN) pre-commit install
