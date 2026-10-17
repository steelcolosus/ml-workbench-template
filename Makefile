# Commands for working on the template itself

.PHONY: test test-all

test: ## Render the template in every configuration and check the output (fast)
	uv run pytest -m "not slow"

test-all: ## Also generate a project and run its own make venv, lint, test, step and images
	uv run pytest
